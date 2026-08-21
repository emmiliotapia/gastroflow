"""
Administrador de Conexiones WebSocket para Pantallas KDS (`kds_manager.py`)
========================================================================
Este módulo gestiona el ciclo de vida de los WebSockets conectados desde el
Kitchen Display System (KDS), enrutando eventos de comandas nuevas o cambios
de estado a las estaciones respectivas (Cocina, Barra, o todas).
"""

import json
from typing import Dict, Set
from fastapi import WebSocket


class KDSConnectionManager:
    """
    Gestor central de WebSockets para KDS.
    """

    def __init__(self):
        # Mapea un tipo de estación ("KITCHEN", "BAR", "ALL") a un conjunto de conexiones activas
        self.active_connections: Dict[str, Set[WebSocket]] = {
            "KITCHEN": set(),
            "BAR": set(),
            "ALL": set()
        }

    async def connect(self, websocket: WebSocket, station: str):
        """
        Acepta la conexión WebSocket y la registra en el pool de la estación correspondiente.
        """
        await websocket.accept()
        station_key = station.upper() if station.upper() in self.active_connections else "ALL"
        self.active_connections[station_key].add(websocket)

    def disconnect(self, websocket: WebSocket, station: str):
        """
        Remueve una conexión desconectada del pool de la estación.
        """
        station_key = station.upper() if station.upper() in self.active_connections else "ALL"
        if websocket in self.active_connections[station_key]:
            self.active_connections[station_key].remove(websocket)

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
        station_key = station.upper() if station.upper() in self.active_connections else "ALL"
        
        # Unimos las conexiones específicas de la estación y las de supervisión general ('ALL')
        targets = self.active_connections[station_key].union(self.active_connections["ALL"])
        
        message_str = json.dumps(message)
        
        # Limpieza de conexiones muertas durante el envío
        dead_connections = set()
        for connection in targets:
            try:
                await connection.send_text(message_str)
            except Exception:
                dead_connections.add(connection)
                
        # Remover conexiones caídas del gestor
        for dead_conn in dead_connections:
            for key in self.active_connections:
                if dead_conn in self.active_connections[key]:
                    self.active_connections[key].remove(dead_conn)


# Instancia singleton global del administrador de WebSockets KDS
kds_manager = KDSConnectionManager()
