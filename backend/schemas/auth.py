"""
Esquemas Pydantic para Autenticación y Usuarios (`auth.py`)
==========================================================
Este módulo contiene los modelos de validación de datos para:
- Solicitudes de Login.
- Respuestas de Tokens de acceso JWT.
- Perfil de lectura de Usuario.
- Verificación de NIP/PIN Poka-Yoke.
"""

import uuid
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    """
    Esquema para la solicitud de inicio de sesión de usuarios.
    """
    username: str = Field(..., example="jefe_sala_01", description="Nombre de usuario registrado")
    password: str = Field(..., example="PasswordSegura2026!", description="Contraseña en texto plano")


class UserRead(BaseModel):
    """
    Esquema de respuesta pública para información de perfil de usuario.
    """
    id: uuid.UUID
    username: str
    email: EmailStr
    full_name: str
    role: str = Field(..., description="Nombre del rol asignado al usuario")
    is_active: bool
    has_pin: bool = Field(..., description="Indica si el usuario tiene un NIP/PIN Poka-Yoke configurado")

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """
    Esquema de respuesta tras un inicio de sesión exitoso.
    """
    access_token: str = Field(..., description="Token JWT firmado de acceso")
    token_type: str = Field(default="bearer", description="Tipo de token HTTP Bearer")
    user: UserRead = Field(..., description="Datos resumidos del usuario autenticado")


class VerifyPinRequest(BaseModel):
    """
    Esquema para la verificación de PIN/NIP de autorización de Jefes de Sala (Poka-Yoke).
    """
    pin: str = Field(..., min_length=4, max_length=6, example="1234", description="NIP numérico de 4 a 6 dígitos")
