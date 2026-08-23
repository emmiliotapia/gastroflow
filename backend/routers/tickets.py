"""
Router REST de Tickets de Soporte Técnico y Mantenimiento (`/api/v1/tickets`)
=============================================================================
Este router proporciona endpoints para abrir, asignar, solucionar
y cerrar tickets con validación de seguridad (PIN de supervisor).
"""

import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from backend.core.deps import get_current_user, get_db, require_role, verify_supervisor_pin, get_optional_current_user
from backend.core.security import verify_pin
from backend.models.enums import UserRole, TicketStatus
from backend.models.ticket import Ticket
from backend.models.user import User
from backend.models.machine import Machine
from backend.schemas.ticket import TicketCreate, TicketAssign, TicketResolve, TicketClose, TicketRead
from backend.utils.n8n import trigger_ticket_webhook, trigger_runner_alert_webhook

router = APIRouter(prefix="/api/v1/tickets", tags=["Tickets de Mantenimiento / Sistemas"])


@router.get(
    "/",
    response_model=List[TicketRead],
    summary="Listar todos los tickets",
    description="Retorna el listado de tickets activos con filtros de estado y asignación."
)
def list_tickets(
    status_filter: Optional[TicketStatus] = Query(None, alias="status", description="Filtrar por estado del ticket"),
    machine_id: Optional[uuid.UUID] = Query(None, description="Filtrar por máquina específica"),
    assigned_to_id: Optional[uuid.UUID] = Query(None, description="Filtrar por técnico asignado"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[TicketRead]:
    stmt = (
        select(Ticket)
        .options(
            joinedload(Ticket.machine),
            joinedload(Ticket.created_by),
            joinedload(Ticket.assigned_to),
            joinedload(Ticket.closed_by)
        )
    )

    if status_filter:
        stmt = stmt.where(Ticket.status == status_filter)
    if machine_id:
        stmt = stmt.where(Ticket.machine_id == machine_id)
    if assigned_to_id:
        stmt = stmt.where(Ticket.assigned_to_id == assigned_to_id)

    # Ordenar cronológicamente descendente (nuevos primero)
    stmt = stmt.order_by(Ticket.created_at.desc())
    tickets = db.execute(stmt).unique().scalars().all()
    return [TicketRead.model_validate(t) for t in tickets]


@router.post(
    "/",
    response_model=TicketRead,
    status_code=status.HTTP_201_CREATED,
    summary="Abrir un nuevo ticket de soporte",
    description="Crea una solicitud de soporte para una máquina. Dispara alerta a n8n."
)
def create_ticket(
    payload: TicketCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> TicketRead:
    # Validar máquina si se provee
    machine = None
    if payload.machine_id:
        machine = db.get(Machine, payload.machine_id)
        if not machine:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Máquina con ID '{payload.machine_id}' no encontrada."
            )

    # Generar folio incremental TKT-XXXXX
    count_stmt = select(func.count(Ticket.id))
    ticket_count = db.execute(count_stmt).scalar() or 0
    folio = f"TKT-{ticket_count + 1:05d}"

    ticket = Ticket(
        folio=folio,
        machine_id=payload.machine_id,
        description=payload.description,
        status=TicketStatus.PENDIENTE,
        created_by_id=current_user.id if current_user else None
    )

    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    # Volver a cargar con relaciones
    stmt = (
        select(Ticket)
        .options(
            joinedload(Ticket.machine),
            joinedload(Ticket.created_by),
            joinedload(Ticket.assigned_to),
            joinedload(Ticket.closed_by)
        )
        .where(Ticket.id == ticket.id)
    )
    final_ticket = db.execute(stmt).unique().scalar_one()
    dto = TicketRead.model_validate(final_ticket)

    # Notificar webhook n8n estándar
    trigger_ticket_webhook(dto.model_dump(mode="json"))

    # Extraer código de máquina si viene en el título o descripción
    desc = payload.description or ""
    machine_code = machine.asset_code if machine else None
    if not machine_code:
        import re
        match = re.search(r"Máquina\s+([A-Za-z0-9\-_]+)", desc, re.IGNORECASE)
        machine_code = match.group(1) if match else "SALA"

    # Despachar al canal especializado
    if "[SOLICITUD DE RECARGA]" in desc:
        trigger_runner_alert_webhook(machine_id=machine_code, action="recarga")
    elif "[LLAMAR MESERO]" in desc:
        trigger_runner_alert_webhook(machine_id=machine_code, action="mesero")
    else:
        trigger_runner_alert_webhook(machine_id=machine_code, action="falla")

    return dto



@router.patch(
    "/{ticket_id}/assign",
    response_model=TicketRead,
    summary="Asignar técnico al ticket",
    description="Asigna un colaborador técnico y cambia el estado a EN_PROCESO."
)
def assign_ticket(
    ticket_id: uuid.UUID,
    payload: TicketAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.JEFE_DE_SALA, UserRole.TECHNICIAN]))
) -> TicketRead:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket no encontrado."
        )

    # Validar que el técnico asignado exista en la base de datos
    tech = db.get(User, payload.assigned_to_id)
    if not tech:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El técnico de sistemas asignado no existe."
        )

    ticket.assigned_to_id = payload.assigned_to_id
    ticket.status = TicketStatus.EN_PROCESO

    db.commit()
    db.refresh(ticket)

    # Recargar con relaciones
    stmt = (
        select(Ticket)
        .options(
            joinedload(Ticket.machine),
            joinedload(Ticket.created_by),
            joinedload(Ticket.assigned_to),
            joinedload(Ticket.closed_by)
        )
        .where(Ticket.id == ticket.id)
    )
    final_ticket = db.execute(stmt).unique().scalar_one()
    dto = TicketRead.model_validate(final_ticket)

    # Notificar webhook
    trigger_ticket_webhook(dto.model_dump(mode="json"))

    return dto


@router.patch(
    "/{ticket_id}/resolve",
    response_model=TicketRead,
    summary="Registrar notas técnicas de resolución",
    description="Permite al técnico registrar comentarios de la solución y mover estado (ej. a HOLD)."
)
def resolve_ticket(
    ticket_id: uuid.UUID,
    payload: TicketResolve,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.JEFE_DE_SALA, UserRole.TECHNICIAN]))
) -> TicketRead:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket no encontrado."
        )

    ticket.resolution_notes = payload.resolution_notes
    if payload.status:
        if payload.status == TicketStatus.FINALIZADO:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Para finalizar y cerrar formalmente el ticket, use el endpoint /close con PIN de supervisor."
            )
        ticket.status = payload.status

    db.commit()
    db.refresh(ticket)

    # Recargar con relaciones
    stmt = (
        select(Ticket)
        .options(
            joinedload(Ticket.machine),
            joinedload(Ticket.created_by),
            joinedload(Ticket.assigned_to),
            joinedload(Ticket.closed_by)
        )
        .where(Ticket.id == ticket.id)
    )
    final_ticket = db.execute(stmt).unique().scalar_one()
    dto = TicketRead.model_validate(final_ticket)

    # Notificar
    trigger_ticket_webhook(dto.model_dump(mode="json"))

    return dto


@router.post(
    "/{ticket_id}/close",
    response_model=TicketRead,
    summary="Cierre formal con validación PIN de Supervisor (Poka-Yoke)",
    description="Finaliza y cierra el ticket requiriendo la firma digital/PIN de un supervisor."
)
def close_ticket(
    ticket_id: uuid.UUID,
    payload: TicketClose,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> TicketRead:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket no encontrado."
        )

    # Buscar supervisor que valide por PIN
    # Validamos que el PIN ingresado pertenezca a un supervisor/administrador activo
    stmt_sup = (
        select(User)
        .options(joinedload(User.role))
        .where(User.is_active == True)
    )
    users = db.execute(stmt_sup).unique().scalars().all()
    supervisor = None
    for u in users:
        if u.role.name in [UserRole.JEFE_DE_SALA, UserRole.ADMIN]:
            if u.hashed_pin and verify_pin(payload.supervisor_pin, u.hashed_pin):
                supervisor = u
                break

    if not supervisor:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El PIN de supervisor ingresado no es válido."
        )

    ticket.status = TicketStatus.FINALIZADO
    ticket.closed_by_id = supervisor.id
    ticket.closed_at = datetime.utcnow()
    if payload.resolution_notes:
        ticket.resolution_notes = payload.resolution_notes

    db.commit()
    db.refresh(ticket)

    # Recargar con relaciones
    stmt = (
        select(Ticket)
        .options(
            joinedload(Ticket.machine),
            joinedload(Ticket.created_by),
            joinedload(Ticket.assigned_to),
            joinedload(Ticket.closed_by)
        )
        .where(Ticket.id == ticket.id)
    )
    final_ticket = db.execute(stmt).unique().scalar_one()
    dto = TicketRead.model_validate(final_ticket)

    # Notificar
    trigger_ticket_webhook(dto.model_dump(mode="json"))

    return dto
