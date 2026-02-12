import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import create_access_token
from app.core.security import verify_password
from app.database import get_db
from app.models.schemas import LoginRequest, LoginResponse

router = APIRouter()


@router.post("/auth/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    conn: asyncpg.Connection = Depends(get_db),
):
    user = await conn.fetchrow(
        "SELECT id, org_id, password_hash FROM users WHERE email = $1",
        payload.email,
    )
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(
        {"sub": str(user["id"]), "org_id": str(user["org_id"])}
    )
    return LoginResponse(access_token=token)
