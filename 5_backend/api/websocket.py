"""
WebSocket API Routes
Real-time communication for workflow updates and notifications.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, List, Set
import json
import asyncio
from datetime import datetime

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        # Active connections by type
        self.active_connections: Dict[str, List[WebSocket]] = {
            "workflow": [],
            "notifications": [],
            "analyst": [],
        }
        # Connections by application ID
        self.application_connections: Dict[str, List[WebSocket]] = {}

    async def connect(
        self,
        websocket: WebSocket,
        connection_type: str = "workflow",
        application_id: str = None
    ):
        """Accept a new WebSocket connection."""
        await websocket.accept()

        if connection_type in self.active_connections:
            self.active_connections[connection_type].append(websocket)

        if application_id:
            if application_id not in self.application_connections:
                self.application_connections[application_id] = []
            self.application_connections[application_id].append(websocket)

    def disconnect(
        self,
        websocket: WebSocket,
        connection_type: str = "workflow",
        application_id: str = None
    ):
        """Remove a WebSocket connection."""
        if connection_type in self.active_connections:
            if websocket in self.active_connections[connection_type]:
                self.active_connections[connection_type].remove(websocket)

        if application_id and application_id in self.application_connections:
            if websocket in self.application_connections[application_id]:
                self.application_connections[application_id].remove(websocket)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific connection."""
        try:
            await websocket.send_json(message)
        except Exception:
            pass

    async def broadcast(self, message: dict, connection_type: str = "workflow"):
        """Broadcast a message to all connections of a type."""
        if connection_type in self.active_connections:
            for connection in self.active_connections[connection_type]:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass

    async def broadcast_to_application(self, message: dict, application_id: str):
        """Broadcast a message to all connections watching an application."""
        if application_id in self.application_connections:
            for connection in self.application_connections[application_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws/workflow/{application_id}")
async def workflow_websocket(websocket: WebSocket, application_id: str):
    """WebSocket endpoint for workflow updates."""
    await manager.connect(
        websocket,
        connection_type="workflow",
        application_id=application_id
    )

    try:
        # Send initial connection confirmation
        await manager.send_personal_message({
            "type": "connection",
            "status": "connected",
            "application_id": application_id,
            "timestamp": datetime.now().isoformat(),
        }, websocket)

        while True:
            # Receive messages from client
            data = await websocket.receive_text()
            message = json.loads(data)

            # Handle different message types
            if message.get("type") == "ping":
                await manager.send_personal_message({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat(),
                }, websocket)

            elif message.get("type") == "subscribe":
                # Subscribe to additional application IDs
                app_id = message.get("application_id")
                if app_id:
                    if app_id not in manager.application_connections:
                        manager.application_connections[app_id] = []
                    manager.application_connections[app_id].append(websocket)

    except WebSocketDisconnect:
        manager.disconnect(
            websocket,
            connection_type="workflow",
            application_id=application_id
        )


@router.websocket("/ws/notifications")
async def notifications_websocket(websocket: WebSocket):
    """WebSocket endpoint for system notifications."""
    await manager.connect(websocket, connection_type="notifications")

    try:
        await manager.send_personal_message({
            "type": "connection",
            "status": "connected",
            "channel": "notifications",
            "timestamp": datetime.now().isoformat(),
        }, websocket)

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "ping":
                await manager.send_personal_message({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat(),
                }, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket, connection_type="notifications")


@router.websocket("/ws/analyst/{application_id}")
async def analyst_websocket(websocket: WebSocket, application_id: str):
    """WebSocket endpoint for AI analyst chat."""
    await manager.connect(
        websocket,
        connection_type="analyst",
        application_id=application_id
    )

    try:
        await manager.send_personal_message({
            "type": "connection",
            "status": "connected",
            "application_id": application_id,
            "channel": "analyst",
            "timestamp": datetime.now().isoformat(),
        }, websocket)

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "ping":
                await manager.send_personal_message({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat(),
                }, websocket)

            elif message.get("type") == "chat":
                # Handle chat message - in production, would process with RAG
                await manager.send_personal_message({
                    "type": "chat_response",
                    "status": "processing",
                    "message_id": message.get("message_id"),
                    "timestamp": datetime.now().isoformat(),
                }, websocket)

    except WebSocketDisconnect:
        manager.disconnect(
            websocket,
            connection_type="analyst",
            application_id=application_id
        )


# Utility functions for sending updates from other parts of the application

async def send_workflow_update(
    application_id: str,
    step_name: str,
    step_status: str,
    data: dict = None
):
    """Send a workflow step update."""
    message = {
        "type": "workflow_update",
        "application_id": application_id,
        "step_name": step_name,
        "step_status": step_status,
        "data": data or {},
        "timestamp": datetime.now().isoformat(),
    }
    await manager.broadcast_to_application(message, application_id)


async def send_decision_notification(
    application_id: str,
    decision: str,
    decision_type: str,
    reason: str = None
):
    """Send a decision notification."""
    message = {
        "type": "decision",
        "application_id": application_id,
        "decision": decision,
        "decision_type": decision_type,
        "reason": reason,
        "timestamp": datetime.now().isoformat(),
    }
    await manager.broadcast_to_application(message, application_id)
    await manager.broadcast(message, connection_type="notifications")


async def send_risk_alert(
    application_id: str,
    alert_type: str,
    message_text: str,
    severity: str = "warning"
):
    """Send a risk alert."""
    message = {
        "type": "risk_alert",
        "application_id": application_id,
        "alert_type": alert_type,
        "message": message_text,
        "severity": severity,
        "timestamp": datetime.now().isoformat(),
    }
    await manager.broadcast_to_application(message, application_id)
    await manager.broadcast(message, connection_type="notifications")


async def send_system_notification(
    title: str,
    message_text: str,
    severity: str = "info"
):
    """Send a system-wide notification."""
    message = {
        "type": "system_notification",
        "title": title,
        "message": message_text,
        "severity": severity,
        "timestamp": datetime.now().isoformat(),
    }
    await manager.broadcast(message, connection_type="notifications")
