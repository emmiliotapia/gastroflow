"""
Módulo de Configuración Central y Variables de Entorno
=====================================================
Este módulo gestiona la carga de variables de entorno utilizando Pydantic Settings.
Garantiza que la URL de la base de datos, claves secretas JWT y parámetros del servidor
estén estrictamente tipados.
"""

import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuración global del sistema cargada desde variables de entorno o archivo .env.
    """
    PROJECT_NAME: str = "GastroFlow"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Base de Datos PostgreSQL
    POSTGRES_USER: str = "casino_admin"
    POSTGRES_PASSWORD: str = "casino_secure_pass_2026"
    POSTGRES_DB: str = "casino_erp_db"
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = "postgresql://casino_admin:casino_secure_pass_2026@localhost:5433/casino_erp_db"

    # Seguridad JWT
    SECRET_KEY: str = "super_secret_jwt_key_casino_hub_2026_change_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 horas de turno

    # CORS: lista de orígenes separados por coma y/o regex de orígenes permitidos.
    # Por defecto solo se aceptan subdominios HTTPS de smartopsia.com y localhost.
    CORS_ORIGINS: str = "http://localhost:8000,http://localhost:8002,http://127.0.0.1:8000"
    CORS_ORIGIN_REGEX: str = r"^https://([a-z0-9-]+\.)*smartopsia\.com$"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
