"""
Router REST de Gestión de Máquinas / Slots (`/api/v1/machines`)
=============================================================
Este router proporciona endpoints CRUD para dar de alta, consultar,
editar y desactivar tragamonedas (slots), así como resolver códigos QR.
"""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.deps import get_current_user, get_db, require_role
from backend.models.enums import UserRole, MachineStatus
from backend.models.machine import Machine
from backend.models.user import User
from backend.schemas.machine import MachineCreate, MachineRead, MachineUpdate

router = APIRouter(prefix="/api/v1/machines", tags=["Gestión de Máquinas / Slots"])


@router.get(
    "/",
    response_model=List[MachineRead],
    summary="Listar máquinas activas",
    description="Retorna el catálogo completo de tragamonedas. Requiere estar autenticado."
)
def list_machines(
    zone: Optional[str] = Query(None, description="Filtrar por zona de la sala"),
    status_filter: Optional[MachineStatus] = Query(None, alias="status", description="Filtrar por estado operativo"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[MachineRead]:
    stmt = select(Machine).where(Machine.is_active == True)
    if zone:
        stmt = stmt.where(Machine.zone == zone)
    if status_filter:
        stmt = stmt.where(Machine.status == status_filter)
        
    machines = db.execute(stmt).scalars().all()
    return [MachineRead.model_validate(m) for m in machines]


@router.get(
    "/by-token/{token}",
    response_model=MachineRead,
    summary="Obtener máquina por token QR",
    description="Resuelve y retorna los detalles de una máquina a partir de su token QR."
)
def get_machine_by_token(
    token: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> MachineRead:
    stmt = select(Machine).where(Machine.qr_code_token == token, Machine.is_active == True)
    machine = db.execute(stmt).scalar_one_or_none()
    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Máquina con token QR '{token}' no encontrada o inactiva."
        )
    return MachineRead.model_validate(machine)


@router.get(
    "/{machine_id}",
    response_model=MachineRead,
    summary="Obtener detalles de una máquina",
    description="Retorna el detalle de un tragamonedas por su UUID."
)
def get_machine(
    machine_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> MachineRead:
    machine = db.get(Machine, machine_id)
    if not machine or not machine.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Máquina con ID '{machine_id}' no encontrada o inactiva."
        )
    return MachineRead.model_validate(machine)


@router.post(
    "/",
    response_model=MachineRead,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar una nueva máquina",
    description="Registra un slot y genera un token QR único. Requiere rol ADMIN o JEFE_DE_SALA."
)
def create_machine(
    payload: MachineCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.JEFE_DE_SALA]))
) -> MachineRead:
    # Validar número de serie único
    check_stmt = select(Machine).where(Machine.serial_number == payload.serial_number)
    if db.execute(check_stmt).scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe una máquina registrada con ese número de serie."
        )

    # Validar asset_code único
    check_asset_stmt = select(Machine).where(Machine.asset_code == payload.asset_code)
    if db.execute(check_asset_stmt).scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe una máquina registrada con ese código de activo."
        )

    token = payload.qr_code_token or str(uuid.uuid4())[:8].upper()

    machine = Machine(
        serial_number=payload.serial_number,
        asset_code=payload.asset_code,
        model=payload.model,
        zone=payload.zone,
        qr_code_token=token,
        status=payload.status,
        is_active=True
    )
    db.add(machine)
    db.commit()
    db.refresh(machine)
    return MachineRead.model_validate(machine)


@router.patch(
    "/{machine_id}",
    response_model=MachineRead,
    summary="Actualizar datos de una máquina",
    description="Edita parámetros de un slot. Requiere rol ADMIN, JEFE_DE_SALA o TECHNICIAN."
)
def update_machine(
    machine_id: uuid.UUID,
    payload: MachineUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.JEFE_DE_SALA, UserRole.TECHNICIAN]))
) -> MachineRead:
    machine = db.get(Machine, machine_id)
    if not machine or not machine.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Máquina no encontrada o inactiva."
        )

    # Actualizar campos suministrados
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(machine, key, value)

    db.commit()
    db.refresh(machine)
    return MachineRead.model_validate(machine)


@router.delete(
    "/{machine_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Dar de baja una máquina (Desactivación)",
    description="Marca como inactiva una máquina del catálogo general. Requiere rol ADMIN."
)
def delete_machine(
    machine_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    machine = db.get(Machine, machine_id)
    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Máquina no encontrada."
        )
    machine.is_active = False
    db.commit()
    return None


@router.get(
    "/{machine_id}/qr",
    summary="Obtener URL y datos del QR de la máquina",
    description="Retorna la URL que debe embeberse en el código QR físico para la PWA de comandas."
)
def get_machine_qr(
    machine_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    machine = db.get(Machine, machine_id)
    if not machine or not machine.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Máquina no encontrada."
        )

    # URL base del comandero
    pos_url = f"https://pos.smartopsia.com?machine_id={machine.id}"
    return {
        "machine_id": str(machine.id),
        "asset_code": machine.asset_code,
        "qr_code_token": machine.qr_code_token,
        "pos_url": pos_url
    }
