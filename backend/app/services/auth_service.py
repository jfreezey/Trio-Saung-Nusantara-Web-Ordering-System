from fastapi import HTTPException, status


def authenticate_admin(email: str, password: str):
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Database authentication is not configured yet."
    )
