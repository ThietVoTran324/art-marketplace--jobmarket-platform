from datetime import datetime, timezone
from pathlib import Path
import uuid

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import delete, func, select

from app.api.rest.dependencies import db, require_roles, user_id
from app.api.rest.ownership import (
    assert_credential_owner,
    assert_cv_owner,
    assert_work_exp_owner,
)
from app.api.rest.utils import delete_file, save_file_bytes
from app.config import settings
from app.postgresql.models import (
    CompaniesOrm,
    ProfileCredentialsOrm,
    UserCvsOrm,
    UsersOrm,
    WorkExperiencesOrm,
)

from .constants import (
    CV_ALLOWED_CONTENT_TYPES,
    CV_ALLOWED_EXTENSIONS,
    CV_MAX_BYTES,
    CV_MAX_COUNT,
)
from .helpers import is_organization_user
from .notify import notify_company_work_exp_pending
from app.api.rest.role_gates import assert_can_manage_cv
from .schemas import (
    CredentialCreate,
    CredentialOut,
    CredentialUpdate,
    UserCvOut,
    WorkExperienceCreate,
    WorkExperienceOut,
    WorkExperienceUpdate,
)
from .sprint2_routes import router as sprint2_router
from .sprint3_routes import router as sprint3_router
from .sprint4_routes import router as sprint4_router
from .sprint5_routes import router as sprint5_router
from .sprint6_routes import router as sprint6_router

router = APIRouter(prefix="/job-market", tags=["job-market"])
router.include_router(sprint2_router)
router.include_router(sprint3_router)
router.include_router(sprint4_router)
router.include_router(sprint5_router)
router.include_router(sprint6_router)

_MATERIAL_FIELDS = frozenset(
    {
        "company_id",
        "company_name",
        "title",
        "description",
        "location",
        "start_date",
        "end_date",
        "employment_type",
    }
)


async def _resolve_active_company(db, company_id: int) -> CompaniesOrm:
    company = await db.scalar(
        select(CompaniesOrm).where(CompaniesOrm.id == company_id)
    )
    if company is None or company.status != "active":
        raise HTTPException(status_code=422, detail="company not found or not active")
    return company


async def _notify_owner_pending(db, *, work_exp: WorkExperiencesOrm, artist_id: int):
    if work_exp.company_id is None:
        return
    company = await db.scalar(
        select(CompaniesOrm).where(CompaniesOrm.id == work_exp.company_id)
    )
    if company is None or company.owner_user_id is None:
        return
    owner = await db.scalar(
        select(UsersOrm).where(UsersOrm.id == company.owner_user_id)
    )
    artist = await db.scalar(select(UsersOrm).where(UsersOrm.id == artist_id))
    if owner is None or artist is None:
        return
    await notify_company_work_exp_pending(
        db,
        owner=owner,
        artist=artist,
        work_exp_id=work_exp.id,
        company_name=work_exp.company_name,
    )

AdminUserId = Annotated[int, Depends(require_roles("admin"))]


# ---- Work experiences ----


@router.get(
    "/users/{target_user_id}/work-experiences",
    response_model=list[WorkExperienceOut],
)
async def list_work_experiences(target_user_id: int, db: db, user_id: user_id):
    if await is_organization_user(db, target_user_id):
        return []
    rows = (
        await db.scalars(
            select(WorkExperiencesOrm)
            .where(WorkExperiencesOrm.user_id == target_user_id)
            .order_by(WorkExperiencesOrm.start_date.asc(), WorkExperiencesOrm.id.asc())
        )
    ).all()
    return rows


@router.post(
    "/me/work-experiences",
    response_model=WorkExperienceOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_work_experience(body: WorkExperienceCreate, db: db, user_id: user_id):
    if await is_organization_user(db, user_id):
        raise HTTPException(status_code=403, detail="org cannot have work experiences")

    company_id = body.company_id
    company_name = body.company_name.strip() if body.company_name else None
    if company_id is not None:
        company = await _resolve_active_company(db, company_id)
        company_name = company.display_name

    row = WorkExperiencesOrm(
        user_id=user_id,
        company_id=company_id,
        company_name=company_name,
        employment_type=body.employment_type,
        title=body.title,
        description=(body.description.strip() if body.description else None) or None,
        location=body.location,
        start_date=body.start_date,
        end_date=body.end_date,
        status="pending",
    )
    db.add(row)
    await db.flush()
    if company_id is not None:
        await _notify_owner_pending(db, work_exp=row, artist_id=user_id)
    await db.commit()
    await db.refresh(row)
    return row


@router.patch("/me/work-experiences/{work_exp_id}", response_model=WorkExperienceOut)
async def update_work_experience(
    work_exp_id: int, body: WorkExperienceUpdate, db: db, user_id: user_id
):
    row = await assert_work_exp_owner(db, work_exp_id, user_id)
    prev_status = row.status
    prev_company_id = row.company_id
    data = body.model_dump(exclude_none=True)
    clear_company = bool(data.pop("clear_company_id", False) or body.clear_company_id)

    if clear_company and "company_id" in data:
        raise HTTPException(
            status_code=422, detail="cannot set company_id with clear_company_id"
        )

    material_changed = False
    company_link_changed = False

    if clear_company:
        if row.company_id is not None:
            material_changed = True
            company_link_changed = True
        row.company_id = None
    elif "company_id" in data:
        new_cid = data.pop("company_id")
        if new_cid != row.company_id:
            company = await _resolve_active_company(db, new_cid)
            row.company_id = company.id
            row.company_name = company.display_name
            data.pop("company_name", None)
            material_changed = True
            company_link_changed = True

    if "company_name" in data and row.company_id is None:
        new_name = str(data.pop("company_name")).strip()
        if new_name != row.company_name:
            row.company_name = new_name
            material_changed = True
    else:
        data.pop("company_name", None)

    start = data.get("start_date", row.start_date)
    end = data["end_date"] if "end_date" in data else row.end_date
    if end is not None and start is not None and end < start:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_date must be >= start_date",
        )

    if "description" in data:
        raw_desc = data["description"]
        data["description"] = (
            raw_desc.strip() if isinstance(raw_desc, str) and raw_desc.strip() else None
        )

    for key, value in data.items():
        if key in _MATERIAL_FIELDS and getattr(row, key) != value:
            material_changed = True
        setattr(row, key, value)

    any_change = material_changed or bool(data) or clear_company or company_link_changed
    if prev_status == "rejected" and any_change:
        row.status = "pending"
    elif prev_status == "approved" and material_changed:
        row.status = "pending"

    row.updated_at = datetime.now(timezone.utc)
    await db.flush()

    notify = False
    if row.company_id is not None:
        if company_link_changed and row.company_id != prev_company_id:
            notify = True
        elif row.status == "pending" and (
            (prev_status == "approved" and material_changed)
            or (prev_status == "rejected" and any_change)
            or (
                prev_status == "pending"
                and company_link_changed
                and prev_company_id is None
            )
        ):
            notify = True

    if notify:
        await _notify_owner_pending(db, work_exp=row, artist_id=user_id)

    await db.commit()
    await db.refresh(row)
    return row


@router.delete("/me/work-experiences/{work_exp_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_work_experience(work_exp_id: int, db: db, user_id: user_id):
    await assert_work_exp_owner(db, work_exp_id, user_id)
    await db.execute(delete(WorkExperiencesOrm).where(WorkExperiencesOrm.id == work_exp_id))
    await db.commit()


# ---- Credentials (public read / owner CRUD / admin override) ----


@router.get(
    "/users/{target_user_id}/credentials",
    response_model=list[CredentialOut],
)
async def list_credentials(
    target_user_id: int,
    db: db,
    user_id: user_id,
    kind: str | None = Query(default=None),
):
    if await is_organization_user(db, target_user_id):
        return []
    stmt = select(ProfileCredentialsOrm).where(
        ProfileCredentialsOrm.user_id == target_user_id
    )
    if kind is not None:
        if kind not in ("education", "licensing", "award"):
            raise HTTPException(status_code=422, detail="invalid kind")
        stmt = stmt.where(ProfileCredentialsOrm.kind == kind)
    stmt = stmt.order_by(ProfileCredentialsOrm.id.asc())
    return (await db.scalars(stmt)).all()


@router.post(
    "/me/credentials",
    response_model=CredentialOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_my_credential(body: CredentialCreate, db: db, user_id: user_id):
    row = ProfileCredentialsOrm(
        user_id=user_id,
        kind=body.kind,
        title=body.title,
        organization=body.organization,
        occurred_on=body.occurred_on,
        description=body.description,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


@router.patch("/me/credentials/{credential_id}", response_model=CredentialOut)
async def update_my_credential(
    credential_id: int, body: CredentialUpdate, db: db, user_id: user_id
):
    row = await assert_credential_owner(db, credential_id, user_id)
    for key, value in body.model_dump(exclude_none=True).items():
        setattr(row, key, value)
    row.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(row)
    return row


@router.delete("/me/credentials/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_credential(credential_id: int, db: db, user_id: user_id):
    await assert_credential_owner(db, credential_id, user_id)
    await db.execute(
        delete(ProfileCredentialsOrm).where(ProfileCredentialsOrm.id == credential_id)
    )
    await db.commit()


@router.post(
    "/admin/users/{target_user_id}/credentials",
    response_model=CredentialOut,
    status_code=status.HTTP_201_CREATED,
)
async def admin_create_credential(
    target_user_id: int,
    body: CredentialCreate,
    db: db,
    admin_user_id: AdminUserId,
):
    user = await db.scalar(select(UsersOrm).where(UsersOrm.id == target_user_id))
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    row = ProfileCredentialsOrm(
        user_id=target_user_id,
        kind=body.kind,
        title=body.title,
        organization=body.organization,
        occurred_on=body.occurred_on,
        description=body.description,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


@router.patch(
    "/admin/users/{target_user_id}/credentials/{credential_id}",
    response_model=CredentialOut,
)
async def admin_update_credential(
    target_user_id: int,
    credential_id: int,
    body: CredentialUpdate,
    db: db,
    admin_user_id: AdminUserId,
):
    row = await db.scalar(
        select(ProfileCredentialsOrm).where(
            ProfileCredentialsOrm.id == credential_id,
            ProfileCredentialsOrm.user_id == target_user_id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="credential not found")
    for key, value in body.model_dump(exclude_none=True).items():
        setattr(row, key, value)
    row.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(row)
    return row


@router.delete(
    "/admin/users/{target_user_id}/credentials/{credential_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def admin_delete_credential(
    target_user_id: int,
    credential_id: int,
    db: db,
    admin_user_id: AdminUserId,
):
    row = await db.scalar(
        select(ProfileCredentialsOrm).where(
            ProfileCredentialsOrm.id == credential_id,
            ProfileCredentialsOrm.user_id == target_user_id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="credential not found")
    await db.execute(
        delete(ProfileCredentialsOrm).where(ProfileCredentialsOrm.id == credential_id)
    )
    await db.commit()


# ---- CVs (owner only) ----


def _require_user_email(user: UsersOrm) -> None:
    if user.email is None or not str(user.email).strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="email_required",
        )


@router.get("/me/cvs", response_model=list[UserCvOut])
async def list_my_cvs(db: db, user_id: user_id):
    rows = (
        await db.scalars(
            select(UserCvsOrm)
            .where(UserCvsOrm.user_id == user_id)
            .order_by(UserCvsOrm.id.asc())
        )
    ).all()
    return rows


@router.post("/me/cvs", response_model=UserCvOut, status_code=status.HTTP_201_CREATED)
async def upload_my_cv(
    db: db,
    user_id: user_id,
    file: UploadFile = File(...),
):
    await assert_can_manage_cv(db, user_id)
    user = await db.scalar(select(UsersOrm).where(UsersOrm.id == user_id))
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    _require_user_email(user)

    count = await db.scalar(
        select(func.count()).select_from(UserCvsOrm).where(UserCvsOrm.user_id == user_id)
    )
    if count is not None and count >= CV_MAX_COUNT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cv_quota_exceeded",
        )

    content_type = file.content_type or ""
    if content_type not in CV_ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Invalid file type. Allowed: pdf, doc, docx",
        )

    original = file.filename or "cv"
    ext = Path(original).suffix.lower()
    if ext not in CV_ALLOWED_EXTENSIONS:
        ext = CV_ALLOWED_CONTENT_TYPES[content_type]

    raw = await file.read()
    if len(raw) > CV_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cv_too_large",
        )
    if not raw:
        raise HTTPException(status_code=400, detail="empty file")

    filename = f"{uuid.uuid4()}{ext}"
    media_root = Path(settings.MEDIA_PATH)
    cvs_dir = media_root / "cvs" / str(user_id)
    cvs_dir.mkdir(parents=True, exist_ok=True)
    full_path = cvs_dir / filename
    await save_file_bytes(raw, str(full_path))

    stored_name = f"cvs/{user_id}/{filename}"
    row = UserCvsOrm(
        user_id=user_id,
        original_filename=Path(original).name[:255],
        stored_name=stored_name,
        content_type=content_type,
        size_bytes=len(raw),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


@router.delete("/me/cvs/{cv_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_cv(cv_id: int, db: db, user_id: user_id):
    await assert_can_manage_cv(db, user_id)
    row = await assert_cv_owner(db, cv_id, user_id)
    media_root = Path(settings.MEDIA_PATH)
    await delete_file(str(media_root / row.stored_name))
    await db.execute(delete(UserCvsOrm).where(UserCvsOrm.id == cv_id))
    await db.commit()


@router.get("/me/cvs/{cv_id}/file")
async def download_my_cv(cv_id: int, db: db, user_id: user_id):
    row = await assert_cv_owner(db, cv_id, user_id)
    path = Path(settings.MEDIA_PATH) / row.stored_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(
        path,
        media_type=row.content_type,
        filename=row.original_filename,
    )
