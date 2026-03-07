from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.auth import decode_access_token
from app.db.session import get_db

DbSession = Annotated[Session, Depends(get_db)]

_bearer = HTTPBearer()


def require_auth(
    credentials: HTTPAuthorizationCredentials = Security(_bearer),
) -> str:
    try:
        return decode_access_token(credentials.credentials)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
