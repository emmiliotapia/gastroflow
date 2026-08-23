"""
Esquemas Pydantic para Gestión de Tickets de Sistemas (`ticket.py`)
===================================================================
Este módulo define las estructuras de datos DTO para la validación de entrada
y formateo de salida de los tickets de soporte del casino.
"""

import uuid
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field
from backend.models.enums import TicketStatus


class TicketCreate(BaseModel):
    machine_id: Optional[uuid.UUID] = Field(None, description="ID de la máquina/slot vinculada al ticket")
    description: str = Field(..., min_length=5, description="Detalle del problema reportado")


class TicketAssign(BaseModel):
    assigned_to_id: uuid.UUID = Field(..., description="ID del técnico de sistemas asignado")


class TicketResolve(BaseModel):
    resolution_notes: str = Field(..., min_length=5, description="Notas de la solución técnica aplicada")
    status: Optional[TicketStatus] = Field(TicketStatus.HOLD, description="Puede ser HOLD o se deja para que Jefe de Sala cierre")


class TicketClose(BaseModel):
    supervisor_pin: str = Field(..., min_length=4, max_length=6, description="PIN/NIP del Jefe de sala para cierre")
    resolution_notes: Optional[str] = Field(None, description="Notas opcionales de resolución final")


class TicketUserRead(BaseModel):
    id: uuid.UUID
    username: str
    full_name: str

    model_config = ConfigDict(from_attributes=True)


class TicketMachineRead(BaseModel):
    id: uuid.UUID
    asset_code: str
    zone: str
    model: str

    model_config = ConfigDict(from_attributes=True)


class TicketRead(BaseModel):
    id: uuid.UUID
    folio: str
    machine_id: Optional[uuid.UUID] = None
    machine: Optional[TicketMachineRead] = None
    description: str
    status: TicketStatus
    created_by_id: Optional[uuid.UUID] = None
    created_by: Optional[TicketUserRead] = None


    assigned_to_id: Optional[uuid.UUID] = None
    assigned_to: Optional[TicketUserRead] = None
    closed_by_id: Optional[uuid.UUID] = None
    closed_by: Optional[TicketUserRead] = None
    resolution_notes: Optional[str] = None
    closed_at: Optional[datetime] = None
    created_at: Any
    updated_at: Any

    model_config = ConfigDict(from_attributes=True)
