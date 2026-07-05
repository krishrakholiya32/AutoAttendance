from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.professor import Professor

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


async def get_current_professor(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Professor:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        professor_id = decode_access_token(token)
    except Exception:
        raise credentials_exception

    professor = await db.get(Professor, professor_id)
    if professor is None:
        raise credentials_exception
    return professor
