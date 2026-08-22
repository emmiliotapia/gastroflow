"""
Módulo de Dependencias e Inyección de FastAPI (`deps.py`)
=========================================================
Este módulo contiene las dependencias reutilizables para routers REST:
- Inyección de sesión de base de datos (`get_db`).
- Extracción y validación de usuario autenticado mediante JWT (`get_current_user`).
- Fábrica de autorización de roles para RBAC (`require_role`).
- Verificación del NIP/PIN Poka-Yoke para supervisores (`verify_supervisor_pin`).
"""

from typing import Callable, Generator, List, Sequence, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from backend.core.database import get_db_session
from backend.core.security import decode_access_token, verify_pin
from backend.models.enums import UserRole
from backend.models.user import User

# Esquema de autenticación Bearer para Swagger UI y cabeceras HTTP
security_bearer = HTTPBearer(auto_error=True)
security_bearer_optional = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    """
    Inyecta una sesión de base de datos activa para la petición actual.
    """
    yield from get_db_session()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_bearer),
    db: Session = Depends(get_db)
) -> User:
    """
    Valida el token JWT recibido en el encabezado 'Authorization: Bearer <token>'
    y retorna la entidad `User` correspondiente desde la base de datos.

    :raises HTTPException 401: Si el token es inválido, expiró o el usuario no existe/está inactivo.
    """
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales o el token ha expirado.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Consultar usuario precargando su entidad de Rol
    stmt = (
        select(User)
        .options(joinedload(User.role))
        .where(User.username == username)
    )
    user = db.execute(stmt).scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta de usuario se encuentra desactivada."
        )

    return user


def require_role(allowed_roles: Sequence[UserRole]) -> Callable:
    """
    Fábrica de dependencias (Dependency Factory) para RBAC.
    Verifica que el usuario autenticado posea uno de los roles permitidos.

    :param allowed_roles: Lista o secuencia de `UserRole` autorizados.
    :return: Función de dependencia ejecutable por FastAPI.
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        user_role_name = current_user.role.name if current_user.role else None

        if user_role_name not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acceso denegado. Se requiere uno de los siguientes roles: {[r.value for r in allowed_roles]}"
            )
        return current_user

    return role_checker


def verify_supervisor_pin(
    pin: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Validación de seguridad Poka-Yoke.
    Verifica el NIP/PIN numérico introducido por un Jefe de Sala o Administrador
    para autorizar operaciones delicadas (cortesías excedidas, cierre de tickets).

    :param pin: PIN numérico ingresado en la solicitud.
    :param db: Sesión de base de datos.
    :param current_user: Usuario actual en sesión.
    :return: El usuario supervisor autorizado.
    :raises HTTPException 403: Si el usuario no tiene rol de supervisor o el PIN es incorrecto.
    """
    # Verificar si el usuario actual es Jefe de Sala o Admin
    if current_user.role.name not in [UserRole.JEFE_DE_SALA, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un Jefe de Sala o Administrador puede autorizar esta acción con PIN."
        )

    if not current_user.hashed_pin or not verify_pin(pin, current_user.hashed_pin):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El PIN/NIP de autorización ingresado es incorrecto o no ha sido configurado."
        )

    return current_user


def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer_optional),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Intenta extraer y validar el usuario desde JWT.
    Si no se envía cabecera de autenticación, retorna None de forma segura.
    """
    if not credentials:
        return None

    try:
        payload = decode_access_token(credentials.credentials)
        username: str = payload.get("sub")
        if username is None:
            return None
    except JWTError:
        return None

    stmt = (
        select(User)
        .options(joinedload(User.role))
        .where(User.username == username)
    )
    user = db.execute(stmt).scalar_one_or_none()

    if user is None or not user.is_active:
        return None

    return user

