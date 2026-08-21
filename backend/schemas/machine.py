"""
Esquemas Pydantic para Gestión de Máquinas / Slots (`machine.py`)
================================================================
Este módulo define las estructuras de datos DTO para la validación de entrada
y formateo de salida de las máquinas tragamonedas del casino.
"""

import uuid
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from backend.models.enums import MachineStatus


class MachineBase(BaseModel):
    serial_number: str = Field(..., max_length=100, description="Número de serie físico único asignado por el fabricante")
    asset_code: str = Field(..., max_length=50, description="Código de activo en sala (ej. SLOT-102)")
    model: str = Field(..., max_length=100, description="Modelo y marca de la máquina")
    zone: str = Field(..., max_length=100, description="Zona física de ubicación en la sala")
    status: MachineStatus = Field(default=MachineStatus.OPERATIONAL, description="Estado operativo de la máquina")


class MachineCreate(MachineBase):
    qr_code_token: Optional[str] = Field(None, max_length=100, description="Token del código QR. Si no se suministra, se genera automáticamente")


class MachineUpdate(BaseModel):
    serial_number: Optional[str] = Field(None, max_length=100)
    asset_code: Optional[str] = Field(None, max_length=50)
    model: Optional[str] = Field(None, max_length=100)
    zone: Optional[str] = Field(None, max_length=100)
    status: Optional[MachineStatus] = None
    is_active: Optional[bool] = None


class MachineRead(MachineBase):
    id: uuid.UUID
    qr_code_token: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
