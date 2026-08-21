"""
Módulo de Seguridad, Hashing y Manejo de Tokens JWT
===================================================
Este módulo implementa las funciones criptográficas del sistema:
- Hashing y verificación de contraseñas principales (Bcrypt).
- Hashing y verificación del PIN/NIP numérico de Jefes de Sala (Poka-Yoke).
- Generación y decodificación de tokens de acceso JWT.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.core.config import settings

# Contexto de cifrado Passlib utilizando el algoritmo Bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica si una contraseña en texto plano coincide con su hash almacenado.

    :param plain_password: Contraseña ingresada por el usuario.
    :param hashed_password: Hash almacenado en la base de datos.
    :return: True si coincide, False en caso contrario.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Genera el hash de una contraseña utilizando el algoritmo Bcrypt.

    :param password: Contraseña en texto plano.
    :return: Hash de la contraseña.
    """
    return pwd_context.hash(password)


def verify_pin(plain_pin: str, hashed_pin: Optional[str]) -> bool:
    """
    Verifica el PIN/NIP numérico (4 a 6 dígitos) utilizado por Jefes de Sala para Poka-Yoke.

    :param plain_pin: PIN en texto plano ingresado para autorizar la acción.
    :param hashed_pin: Hash del PIN almacenado en el perfil del usuario.
    :return: True si la verificación es exitosa y el hash existe, False en caso contrario.
    """
    if not hashed_pin:
        return False
    return pwd_context.verify(plain_pin, hashed_pin)


def get_pin_hash(pin: str) -> str:
    """
    Genera el hash seguro de un PIN/NIP numérico.

    :param pin: Cadena numérica del PIN (ej. '1234').
    :return: Hash del PIN.
    """
    return pwd_context.hash(pin)


def create_access_token(
    subject: Union[str, Any],
    role: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Crea un token de acceso JWT firmando la información del usuario y su rol.

    :param subject: Identificador único del usuario (UUID o username en campo 'sub').
    :param role: Nombre del rol asignado (ej. 'ADMIN', 'JEFE_DE_SALA').
    :param expires_delta: Tiempo opcional de expiración del token.
    :return: Cadena de texto con el token JWT firmado.
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode: Dict[str, Any] = {
        "sub": str(subject),
        "role": str(role),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp())
    }

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decodifica y valida la firma y vigencia de un token JWT.

    :param token: Token JWT recibido en las cabeceras HTTP.
    :return: Diccionario de claims contenidos en el payload.
    :raises JWTError: Si el token es inválido, expiró o su firma no coincide.
    """
    payload = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM]
    )
    return payload
