"""
Router REST de Autenticación y Autorización (`/api/v1/auth`)
============================================================
Este módulo implementa los endpoints HTTP para:
- Inicio de sesión y generación de JWT (`POST /login`).
- Consulta del perfil en sesión (`GET /me`).
- Validación de PIN/NIP Poka-Yoke de Jefes de Sala (`POST /verify-pin`).
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from backend.core.deps import get_current_user, get_db
from backend.core.security import create_access_token, verify_password, verify_pin
from backend.models.enums import UserRole
from backend.models.user import User
from backend.schemas.auth import LoginRequest, TokenResponse, UserRead, VerifyPinRequest

router = APIRouter(prefix="/api/v1/auth", tags=["Autenticación"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Iniciar sesión y obtener Token JWT",
    description="Autentica al usuario mediante nombre de usuario y contraseña, de forma compatible con JSON, urlencoded y multipart form."
)
async def login(
    request: Request,
    db: Session = Depends(get_db)
) -> TokenResponse:
    """
    Endpoint de inicio de sesión. Soporta JSON, form-urlencoded y multipart-form-data.
    """
    content_type = request.headers.get("content-type", "")
    username = None
    password = None

    if "application/json" in content_type:
        try:
            body = await request.json()
            username = body.get("username")
            password = body.get("password")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON body")
    else:
        # Form-urlencoded o multipart form data
        try:
            form = await request.form()
            username = form.get("username")
            password = form.get("password")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid form data")

    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nombre de usuario y contraseña son obligatorios."
        )

    stmt = (
        select(User)
        .options(joinedload(User.role))
        .where(User.username == username)
    )
    user = db.execute(stmt).scalar_one_or_none()

    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nombre de usuario o contraseña incorrectos.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta de usuario se encuentra inactiva."
        )

    # Actualizar la marca de tiempo de último acceso
    user.last_login = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)

    # Nombre del rol asignado
    role_name = user.role.name.value if user.role else "CUSTOMER"

    # Generar Token JWT
    access_token = create_access_token(
        subject=user.username,
        role=role_name
    )

    user_read = UserRead(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=role_name,
        is_active=user.is_active,
        has_pin=bool(user.hashed_pin)
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user_read
    )


@router.get(
    "/me",
    response_model=UserRead,
    summary="Obtener perfil del usuario autenticado",
    description="Retorna la información del usuario correspondiente al token JWT provisto en las cabeceras."
)
def get_me(
    current_user: User = Depends(get_current_user)
) -> UserRead:
    """
    Retorna el perfil del usuario autenticado en sesión.
    """
    role_name = current_user.role.name.value if current_user.role else "CUSTOMER"

    return UserRead(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        role=role_name,
        is_active=current_user.is_active,
        has_pin=bool(current_user.hashed_pin)
    )


@router.post(
    "/verify-pin",
    summary="Validar PIN NIP de Jefe de Sala (Poka-Yoke)",
    description="Valida el PIN numérico de un Jefe de Sala o Administrador para autorizar acciones delicadas en sala."
)
def verify_supervisor_pin_endpoint(
    payload: VerifyPinRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Endpoint para validación en tiempo real del NIP/PIN Poka-Yoke.
    """
    if current_user.role.name not in [UserRole.JEFE_DE_SALA, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un Jefe de Sala o Administrador posee un PIN de autorización."
        )

    if not current_user.hashed_pin or not verify_pin(payload.pin, current_user.hashed_pin):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El PIN/NIP de autorización ingresado es incorrecto."
        )

    return {
        "status": "authorized",
        "message": "PIN de Jefe de Sala validado exitosamente.",
        "authorized_by": current_user.full_name
    }
