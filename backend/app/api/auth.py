from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_professor
from app.core.logging import get_logger
from app.core.security import create_access_token, hash_password, verify_password
from app.models.professor import Professor
from app.schemas.auth import LoginRequest, ProfessorOut, SignupRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])
logger = get_logger(__name__)


@router.post("/signup", response_model=TokenResponse)
async def signup(payload: SignupRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.scalar(select(Professor).where(Professor.email == payload.email))
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    professor = Professor(
        email=payload.email,
        password_hash=hash_password(payload.password),
        name=payload.name,
    )
    db.add(professor)
    await db.commit()
    await db.refresh(professor)
    logger.info("professor_signup", professor_id=professor.id)

    token = create_access_token(professor.id)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    professor = await db.scalar(select(Professor).where(Professor.email == payload.email))
    if not professor or not verify_password(payload.password, professor.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = create_access_token(professor.id)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=ProfessorOut)
async def me(professor: Professor = Depends(get_current_professor)):
    return professor
