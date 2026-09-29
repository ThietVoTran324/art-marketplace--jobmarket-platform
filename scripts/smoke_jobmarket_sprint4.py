"""JobMarket Sprint4 smoke — apply, view-CV, status, gates."""
import asyncio
import io
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from sqlalchemy import text

from app.api.rest.utils import create_url_safe_token
from app.postgresql.database import async_session_maker

BASE = "http://127.0.0.1:8000"
PASSWORD = "TestPass123!"


def future_expires_at(days: int = 30) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def csrf_headers(cookies: httpx.Cookies) -> dict[str, str]:
    token = cookies.get("csrf_token")
    assert token, "missing csrf_token cookie"
    return {"X-CSRF-Token": token}


async def promote_admin(user_id: int) -> None:
    async with async_session_maker() as session:
        await session.execute(
            text(
                "INSERT INTO user_roles (user_id, role) VALUES (:uid, 'admin') "
                "ON CONFLICT DO NOTHING"
            ),
            {"uid": user_id},
        )
        await session.commit()


async def set_email(user_id: int, email: str, verified: bool = True) -> None:
    async with async_session_maker() as session:
        await session.execute(
            text(
                "UPDATE users SET email = :email, verified = :verified WHERE id = :uid"
            ),
            {"email": email, "verified": verified, "uid": user_id},
        )
        await session.commit()


async def register_and_login(client, username: str):
    r = await client.post(
        "/users/register", json={"username": username, "password": PASSWORD}
    )
    assert r.status_code == 201, r.text
    uid = r.json()["id"]
    r = await client.post(
        "/users/login", json={"username": username, "password": PASSWORD}
    )
    assert r.status_code == 200, r.text
    return uid, r.cookies


def minimal_pdf() -> bytes:
    return b"%PDF-1.1\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


async def become_org(client, *, owner_id, cookies, headers, email, reg, admin_c, admin_h):
    body = {
        "display_name": f"Co {reg}",
        "registration_country": "VN",
        "registration_type": "LLC",
        "registration_number_raw": reg,
        "signer_full_name": "Owner",
        "primary_document_language": "en",
        "company_email": email,
        "address_line": "1 Main",
        "city": "HN",
        "branch_country": "VN",
    }
    r = await client.post(
        "/job-market/me/hiring-rights-requests",
        cookies=cookies,
        headers=headers,
        json=body,
    )
    assert r.status_code == 201, r.text
    req = r.json()
    token = create_url_safe_token(
        {"request_id": req["id"], "user_id": owner_id}, expiration=86400
    )
    await client.get(f"/job-market/kyc/confirm-email/{token}", follow_redirects=False)
    files = {"file": ("biz.pdf", io.BytesIO(minimal_pdf()), "application/pdf")}
    up = await client.post(
        f"/job-market/me/hiring-rights-requests/{req['id']}/documents",
        cookies=cookies,
        headers=headers,
        data={"doc_type": "business_registration_document"},
        files=files,
    )
    assert up.status_code == 201, up.text
    appr = await client.post(
        f"/job-market/admin/hiring-rights-requests/{req['id']}/approve",
        cookies=admin_c,
        headers=admin_h,
    )
    assert appr.status_code == 200, appr.text
    return req["company_id"]


async def main() -> None:
    suffix = uuid.uuid4().hex[:8]
    results = []

    async with httpx.AsyncClient(base_url=BASE, timeout=60.0) as client:
        admin_id, admin_c = await register_and_login(client, f"jm4ad_{suffix}")
        await promote_admin(admin_id)
        login = await client.post(
            "/users/login",
            json={"username": f"jm4ad_{suffix}", "password": PASSWORD},
        )
        admin_c = login.cookies
        ah = csrf_headers(admin_c)

        owner_id, owner_c = await register_and_login(client, f"jm4o_{suffix}")
        owner_email = f"jm4o_{suffix}@example.com"
        await set_email(owner_id, owner_email)
        oh = csrf_headers(owner_c)
        company_id = await become_org(
            client,
            owner_id=owner_id,
            cookies=owner_c,
            headers=oh,
            email=owner_email,
            reg=f"44{suffix.upper()}",
            admin_c=admin_c,
            admin_h=ah,
        )
        results.append("org_ok")

        # Org cannot apply
        branches = await client.get(
            f"/job-market/companies/{company_id}/branches", cookies=owner_c
        )
        branch_id = branches.json()[0]["id"]
        job = await client.post(
            "/job-market/me/job-posts",
            cookies=owner_c,
            headers=oh,
            json={
                "title": f"Role {suffix}",
                "years_experience": 1,
                "salary_mode": "love_it",
                "currency": "VND",
                "branch_ids": [branch_id],
                "expires_at": future_expires_at(),
            },
        )
        assert job.status_code == 201, job.text
        job_id = job.json()["id"]

        org_apply = await client.post(
            f"/job-market/jobs/{job_id}/apply",
            cookies=owner_c,
            headers=oh,
            data={"cover_note": "x"},
            files={"cv": ("cv.pdf", io.BytesIO(minimal_pdf()), "application/pdf")},
        )
        assert org_apply.status_code == 403
        results.append("org_cannot_apply_ok")

        # Applicant
        app_id, app_c = await register_and_login(client, f"jm4a_{suffix}")
        await set_email(app_id, f"jm4a_{suffix}@example.com", verified=False)
        aph = csrf_headers(app_c)
        no_email = await client.post(
            f"/job-market/jobs/{job_id}/apply",
            cookies=app_c,
            headers=aph,
            files={"cv": ("cv.pdf", io.BytesIO(minimal_pdf()), "application/pdf")},
        )
        assert no_email.status_code == 400
        results.append("email_gate_ok")

        await set_email(app_id, f"jm4a_{suffix}@example.com", verified=True)

        apply = await client.post(
            f"/job-market/jobs/{job_id}/apply",
            cookies=app_c,
            headers=aph,
            data={"cover_note": "Hello"},
            files={"cv": ("cv.pdf", io.BytesIO(minimal_pdf()), "application/pdf")},
        )
        assert apply.status_code == 201, apply.text
        application_id = apply.json()["id"]
        assert apply.json()["status"] == "submitted"
        results.append("apply_oneshot_ok")

        # quota not bumped — no /me/cvs from oneshot
        cvs = await client.get("/job-market/me/cvs", cookies=app_c)
        assert cvs.status_code == 200 and cvs.json() == []
        results.append("oneshot_no_quota_ok")

        dup = await client.post(
            f"/job-market/jobs/{job_id}/apply",
            cookies=app_c,
            headers=aph,
            files={"cv": ("cv.pdf", io.BytesIO(minimal_pdf()), "application/pdf")},
        )
        assert dup.status_code == 409
        results.append("duplicate_ok")

        detail = await client.get(f"/job-market/jobs/{job_id}", cookies=app_c)
        assert detail.json()["my_application"]["id"] == application_id
        results.append("my_application_ok")

        # non-owner cannot view cv
        steal = await client.get(
            f"/job-market/applications/{application_id}/cv-view", cookies=app_c
        )
        assert steal.status_code == 403
        results.append("applicant_cv_acl_ok")

        # owner view → viewed
        view = await client.get(
            f"/job-market/applications/{application_id}/cv-view", cookies=owner_c
        )
        assert view.status_code == 200, view.text
        assert view.json()["status"] == "viewed"
        results.append("viewed_on_cv_view_ok")

        # reject
        rej = await client.post(
            f"/job-market/me/job-posts/{job_id}/applications/{application_id}/reject",
            cookies=owner_c,
            headers=oh,
        )
        assert rej.status_code == 200 and rej.json()["status"] == "rejected"
        results.append("reject_ok")

        term = await client.post(
            f"/job-market/me/job-posts/{job_id}/applications/{application_id}/pass",
            cookies=owner_c,
            headers=oh,
        )
        assert term.status_code == 409
        results.append("terminal_lock_ok")

        # re-apply after reject — blocked until close+reopen
        again = await client.post(
            f"/job-market/jobs/{job_id}/apply",
            cookies=app_c,
            headers=aph,
            files={"cv": ("cv2.pdf", io.BytesIO(minimal_pdf()), "application/pdf")},
        )
        assert again.status_code == 409, again.text
        results.append("no_reapply_after_reject_ok")

        # close + reopen resets cycle → apply allowed again
        await client.post(
            f"/job-market/me/job-posts/{job_id}/close", cookies=owner_c, headers=oh
        )
        ext = await client.patch(
            f"/job-market/me/job-posts/{job_id}",
            cookies=owner_c,
            headers=oh,
            json={"expires_at": future_expires_at(20)},
        )
        assert ext.status_code == 200, ext.text
        reo = await client.post(
            f"/job-market/me/job-posts/{job_id}/reopen", cookies=owner_c, headers=oh
        )
        assert reo.status_code == 200, reo.text
        again2 = await client.post(
            f"/job-market/jobs/{job_id}/apply",
            cookies=app_c,
            headers=aph,
            files={"cv": ("cv2b.pdf", io.BytesIO(minimal_pdf()), "application/pdf")},
        )
        assert again2.status_code == 201, again2.text
        app2 = again2.json()["id"]
        results.append("reapply_after_reopen_ok")

        # pass second
        passed = await client.post(
            f"/job-market/me/job-posts/{job_id}/applications/{app2}/pass",
            cookies=owner_c,
            headers=oh,
        )
        assert passed.status_code == 200 and passed.json()["status"] == "passed"

        block = await client.post(
            f"/job-market/jobs/{job_id}/apply",
            cookies=app_c,
            headers=aph,
            files={"cv": ("cv3.pdf", io.BytesIO(minimal_pdf()), "application/pdf")},
        )
        assert block.status_code == 409
        results.append("no_reapply_after_passed_ok")

        # closed job block apply (new applicant)
        await client.post(
            f"/job-market/me/job-posts/{job_id}/close", cookies=owner_c, headers=oh
        )
        other_id, other_c = await register_and_login(client, f"jm4x_{suffix}")
        await set_email(other_id, f"jm4x_{suffix}@example.com")
        oxh = csrf_headers(other_c)
        closed = await client.post(
            f"/job-market/jobs/{job_id}/apply",
            cookies=other_c,
            headers=oxh,
            files={"cv": ("cv.pdf", io.BytesIO(minimal_pdf()), "application/pdf")},
        )
        assert closed.status_code == 400
        results.append("closed_blocks_apply_ok")

        # owner still lists apps
        lst = await client.get(
            f"/job-market/me/job-posts/{job_id}/applications", cookies=owner_c
        )
        assert lst.status_code == 200 and len(lst.json()) >= 2
        results.append("owner_list_when_closed_ok")

        # HY-02 mark-read ownership
        upd = await client.get("/updates/", cookies=owner_c)
        assert upd.status_code == 200
        if upd.json():
            uid = upd.json()[0]["id"]
            bad = await client.put(
                f"/updates/read/{uid}", cookies=other_c, headers=oxh
            )
            assert bad.status_code == 404, bad.text
            results.append("hy02_mark_read_ok")

    for item in results:
        print("PASS:", item)
    print("ALL_SMOKE_PASS")


if __name__ == "__main__":
    asyncio.run(main())
