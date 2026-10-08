from typing import Annotated

from fastapi import Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.rest.pins.schemas import FilterParams, FilterWithValue
from app.api.rest.roles import get_user_roles
from app.postgresql.database import get_db
from app.redis.redis_revoke_tokens import is_token_revoked

from .utils import encode_token, jwt_decode_soft


async def get_token(request: Request):
    token = request.cookies.get("access_token", None)
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return token


async def get_current_user_id(token: Annotated[str, Depends(get_token)]):
    if await is_token_revoked(token):
        raise HTTPException(status_code=401, detail="Token is revoked")

    data = encode_token(token)
    if data.get("sub") != "access":
        raise HTTPException(status_code=401, detail="Invalid token")

    return data["user_id"]


async def get_optional_user_id(request: Request) -> int | None:
    """Return user_id from access cookie, or None if missing/invalid (no 401)."""
    token = request.cookies.get("access_token", None)
    if not token:
        return None
    try:
        if await is_token_revoked(token):
            return None
        data = jwt_decode_soft(token)
        if not data or data.get("sub") != "access":
            return None
        return data.get("user_id")
    except Exception:
        return None


def require_roles(*required: str):
    required_set = set(required)

    async def _checker(
        current_user_id: Annotated[int, Depends(get_current_user_id)],
        db: Annotated[AsyncSession, Depends(get_db)],
    ) -> int:
        roles = await get_user_roles(db, current_user_id)
        if not required_set.issubset(roles):
            raise HTTPException(status_code=403, detail="HTTP_403_FORBIDDEN")
        return current_user_id

    return _checker


db = Annotated[AsyncSession, Depends(get_db)]
user_id = Annotated[int, Depends(get_current_user_id)]
optional_user_id = Annotated[int | None, Depends(get_optional_user_id)]


def _filter_params(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
) -> FilterParams:
    """Flatten offset/limit — avoid `Annotated[Model, Query()]` which some
    FastAPI builds treat as a single required `filter` object (HTTP 422)."""
    return FilterParams(offset=offset, limit=limit)


def _filter_with_value(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    value: str = Query(""),
) -> FilterWithValue:
    return FilterWithValue(offset=offset, limit=limit, value=value)


filter = Annotated[FilterParams, Depends(_filter_params)]
filter_with_value = Annotated[FilterWithValue, Depends(_filter_with_value)]
