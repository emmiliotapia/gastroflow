"""
Administrador de Conexiones WebSocket para Pantallas KDS y Staff (`kds_manager.py`)
========================================================================
Este módulo gestiona el ciclo de vida de los WebSockets conectados desde el
Kitchen Display System (KDS), PWA de Meseros y Terminales de Caja, enrutando
eventos de comandas nuevas o cambios de estado a las estaciones respectivas
(Cocina, Barra, Meseros/Runners o supervisión general).
"""

import asyncio
import json
import logging
from typing import Dict, Optional, Set
from fastapi import WebSocket

logger = logging.getLogger("kds_manager")


class KDSConnectionManager:
    """
    Gestor central de WebSockets para KDS, Cocina, Barra y Meseros.
    Soporta emisión asíncrona directa y emisión síncrona segura entre hilos.
    """

    def __init__(self):
        # Mapea un tipo de estación a un conjunto de conexiones activas
        self.active_connections: Dict[str, Set[WebSocket]] = {
            "KITCHEN": set(),
            "BAR": set(),
            "WAITERS": set(),
            "RUNNERS": set(),
            "ALL": set()
        }
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        """Registra el event loop principal de asyncio en el arranque de FastAPI."""
        self._loop = loop

    def get_loop(self) -> Optional[asyncio.AbstractEventLoop]:
        """Obtiene el loop principal o intenta resolver el loop en ejecución."""
        if self._loop and not self._loop.is_closed():
            return self._loop
        try:
            loop = asyncio.get_running_loop()
            if loop and not loop.is_closed():
                self._loop = loop
                return loop
        except RuntimeError:
            pass
        return None

    async def connect(self, websocket: WebSocket, station: str):
        """
        Acepta la conexión WebSocket y la registra en el pool de la estación correspondiente.
        """
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            pass
        await websocket.accept()
        station_key = station.upper()
        if station_key not in self.active_connections:
            self.active_connections[station_key] = set()
        self.active_connections[station_key].add(websocket)
        logger.info(f"[WS] Conexión abierta en estación '{station_key}'. Total activos: {len(self.active_connections[station_key])}")

    def disconnect(self, websocket: WebSocket, station: str):
        """
        Remueve una conexión desconectada del pool de la estación.
        """
        station_key = station.upper() if station.upper() in self.active_connections else "ALL"
        if station_key in self.active_connections and websocket in self.active_connections[station_key]:
            self.active_connections[station_key].remove(websocket)
            logger.info(f"[WS] Conexión cerrada en estación '{station_key}'.")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """
        Envía un mensaje JSON a una conexión en específico.
        """
        await websocket.send_text(json.dumps(message))

    async def broadcast_to_station(self, station: str, message: dict):
        """
        Transmite un evento JSON a todos los WebSockets suscritos a una estación,
        así como a los suscritos al canal general 'ALL'.
        """
        station_key = station.upper()
        if station_key not in self.active_connections:
            self.active_connections[station_key] = set()
        
        # Unimos las conexiones específicas de la estación y las de supervisión general ('ALL')
        targets = set(self.active_connections[station_key]).union(self.active_connections["ALL"])
        if not targets:
            return

        message_str = json.dumps(message)
        dead_connections = set()
        
        for connection in targets:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.warning(f"[WS] Falla al enviar a conexión activa: {str(e)}")
                dead_connections.add(connection)
                
        # Remover conexiones caídas del gestor
        for dead_conn in dead_connections:
            for key in self.active_connections:
                if dead_conn in self.active_connections[key]:
                    self.active_connections[key].remove(dead_conn)

    def broadcast_sync(self, station: str, message: dict):
        """
        Método seguro para emitir broadcasts hacia WebSockets desde endpoints síncronos
        o hilos del threadpool de FastAPI sin fallar por 'no current event loop'.
        """
        station_key = station.upper()
        active_cnt = len(self.active_connections.get(station_key, set())) + len(self.active_connections.get("ALL", set()))
        if active_cnt == 0:
            return

        loop = self.get_loop()
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self.broadcast_to_station(station=station, message=message),
                loop
            )
        else:
            try:
                loop = asyncio.get_event_loop()
                if loop and loop.is_running():
                    self._loop = loop
                    asyncio.run_coroutine_threadsafe(
                        self.broadcast_to_station(station=station, message=message),
                        loop
                    )
                    return
            except Exception:
                pass
            logger.warning(f"[WS] No se pudo encontrar loop de asyncio activo para emitir evento '{message.get('event')}' a estación '{station}'.")



# Instancia singleton global del administrador de WebSockets KDS
kds_manager = KDSConnectionManager()
