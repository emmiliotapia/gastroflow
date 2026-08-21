"""
Script para la Creación de Usuarios de Prueba
=============================================
Este script permite dar de alta rápidamente usuarios de prueba en la base de datos
(Técnicos, Supervisores, Clientes) para validar los flujos de las PWAs y APIs.
"""

import sys
from sqlalchemy import select
from sqlalchemy.orm import Session

# Resolver ruta raíz
sys.path.insert(0, ".")

from backend.core.database import SessionLocal, engine
from backend.core.security import get_password_hash, get_pin_hash
from backend.models.enums import UserRole, MembershipTier
from backend.models.user import Role, User


def create_user(
    username: str, 
    email: str, 
    full_name: str, 
    password: str, 
    role_name: UserRole, 
    pin: str = None, 
    tier: MembershipTier = None
):
    db: Session = SessionLocal()
    try:
        # 1. Obtener Rol
        stmt_role = select(Role).where(Role.name == role_name)
        role = db.execute(stmt_role).scalar_one_or_none()
        
        if not role:
            # Crear rol dinámicamente si no existe
            role = Role(
                name=role_name,
                description=f"Rol de sistema para {role_name.value}",
                permissions={"all": True} if role_name == UserRole.ADMIN else {"read": True}
            )
            db.add(role)
            db.flush()
            print(f"[INFO] Rol {role_name.value} creado en base de datos.")

        # 2. Verificar si el usuario ya existe
        stmt_user = select(User).where(User.username == username)
        existing_user = db.execute(stmt_user).scalar_one_or_none()
        
        if existing_user:
            print(f"[WARN] El usuario '{username}' ya existe. Actualizando credenciales...")
            existing_user.hashed_password = get_password_hash(password)
            if pin:
                existing_user.hashed_pin = get_pin_hash(pin)
            if tier:
                existing_user.membership_tier = tier
            db.commit()
            print(f"[SUCCESS] Usuario '{username}' actualizado correctamente.")
            return

        # 3. Crear nuevo usuario
        new_user = User(
            username=username,
            email=email,
            full_name=full_name,
            hashed_password=get_password_hash(password),
            hashed_pin=get_pin_hash(pin) if pin else None,
            role_id=role.id,
            membership_tier=tier if tier else MembershipTier.CLASSIC,
            is_active=True
        )
        db.add(new_user)
        db.commit()
        print(f"[SUCCESS] Usuario creado exitosamente:")
        print(f"  - Usuario: {username}")
        print(f"  - Contraseña: {password}")
        print(f"  - Rol: {role_name.value}")
        if pin:
            print(f"  - PIN/NIP: {pin}")
        if tier:
            print(f"  - Membresía: {tier.value}")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] No se pudo crear el usuario: {str(e)}")
    finally:
        db.close()


if __name__ == "__main__":
    print("\n--- CREANDO USUARIOS DE PRUEBA ---")
    
    # 1. Crear Técnico de Prueba para la PWA Staff
    create_user(
        username="tecnico_test",
        email="soporte@casino.com",
        full_name="Tomás Alva (Sistemas)",
        password="TechPass2026!",
        role_name=UserRole.TECHNICIAN
    )

    # 2. Crear Supervisor / Jefe de Sala para validaciones Poka-Yoke
    create_user(
        username="supervisor_test",
        email="supervisor_test@casino.com",
        full_name="Sofía Castro (Jefa de Sala)",
        password="JefePass2026!",
        role_name=UserRole.JEFE_DE_SALA,
        pin="9999"
    )

    # 3. Crear Cliente Classic para pruebas de cortesías insuficientes
    create_user(
        username="cliente_classic",
        email="classic_test@casino.com",
        full_name="Pedro Infante (Client)",
        password="ClientPass2026!",
        role_name=UserRole.CUSTOMER,
        tier=MembershipTier.CLASSIC
    )

    # 4. Crear Cliente VIP con cortesía automática
    create_user(
        username="cliente_vip",
        email="vip_test@casino.com",
        full_name="María Félix (VIP Client)",
        password="VipPass2026!",
        role_name=UserRole.CUSTOMER,
        tier=MembershipTier.VIP
    )
