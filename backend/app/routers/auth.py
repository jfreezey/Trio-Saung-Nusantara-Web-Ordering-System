from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

from app.schemas.auth import LoginRequest, LoginResponse, UserResponse
from app.services.auth_service import authenticate_admin
from app.core.security import decode_access_token


router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"]
)

security = HTTPBearer()


# Login Admin & cashier role
@router.post("/login", response_model=LoginResponse)
def login_admin(login_data: LoginRequest):
    token = authenticate_admin(
        email=login_data.email,
        password=login_data.password
    )

    return {
        "access_token": token,
        "token_type": "bearer"
    }


# Checking identity from JWT (belum integrate dengan database)
@router.get("/me")
def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    try:
        payload = decode_access_token(credentials.credentials)

        if payload.get("role") != "Admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required."
            )

        return {
            "user_id": payload["sub"],
            "role": payload["role"]
        }

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token."
        )
