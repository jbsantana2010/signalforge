from datetime import datetime, timedelta, timezone

import asyncpg
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.database import get_db

bearer_scheme = HTTPBearer()


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    from jose import jwt
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    from jose import JWTError, jwt
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        user_id: str | None = payload.get("sub")
        org_id: str | None = payload.get("org_id")
        if user_id is None or org_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )
        agency_id: str | None = payload.get("agency_id")
        result = {"user_id": user_id, "org_id": org_id}
        if agency_id:
            result["agency_id"] = agency_id
        return result
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )


async def resolve_active_org_id(
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
    x_org_id: str | None = Header(None),
) -> str:
    """Return the effective org_id for admin queries.

    If X-ORG-ID header is sent and the user belongs to an agency,
    validate the target org belongs to the same agency and return it.
    Otherwise fall back to the user's home org_id from the JWT.
    """
    home_org_id = current_user["org_id"]

    if not x_org_id:
        return home_org_id

    agency_id = current_user.get("agency_id")
    if not agency_id:
        # Non-agency user cannot switch orgs
        return home_org_id

    # Validate target org belongs to the same agency
    target = await conn.fetchval(
        "SELECT id FROM orgs WHERE id = $1 AND agency_id = $2",
        x_org_id,
        agency_id,
    )
    if not target:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Org not accessible",
        )
    return x_org_id
