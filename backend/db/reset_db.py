"""
Script para Reiniciar la Base de Datos
=====================================
Este script elimina todas las tablas de la base de datos y las vuelve
a crear desde cero. Útil para entornos de desarrollo y pruebas.
"""

import sys
sys.path.insert(0, ".")

from backend.core.database import engine
from backend.models.base import Base
# Importar todos los modelos para asegurar que SQLAlchemy los registre
import backend.models 

def reset_database():
    print("[INFO] Eliminando todas las tablas existentes en la base de datos...")
    Base.metadata.drop_all(bind=engine)
    print("[INFO] Creando todas las tablas nuevamente...")
    Base.metadata.create_all(bind=engine)
    print("[SUCCESS] Base de datos reiniciada con éxito.")

if __name__ == "__main__":
    reset_database()
