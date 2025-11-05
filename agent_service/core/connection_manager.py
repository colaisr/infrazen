"""
WebSocket connection manager for tracking active connections.
"""

import logging
from typing import Dict, Optional
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections."""
    
    def __init__(self):
        # Dict[session_id, WebSocket]
        self.active_connections: Dict[str, WebSocket] = {}
        
    async def connect(self, session_id: str, websocket: WebSocket):
        """
        Accept and store a new WebSocket connection.
        
        Args:
            session_id: Chat session ID
            websocket: FastAPI WebSocket instance
        """
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket connected: session={session_id}")
        
    def disconnect(self, session_id: str):
        """
        Remove a WebSocket connection.
        
        Args:
            session_id: Chat session ID
        """
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"WebSocket disconnected: session={session_id}")
            
    async def send_message(self, session_id: str, message: dict):
        """
        Send a JSON message to a specific connection.
        
        Args:
            session_id: Chat session ID
            message: Message dict to send as JSON
        """
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to session {session_id}: {e}")
                self.disconnect(session_id)
                
    async def broadcast(self, message: dict):
        """
        Broadcast a message to all active connections.
        
        Args:
            message: Message dict to send as JSON
        """
        dead_connections = []
        
        for session_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to session {session_id}: {e}")
                dead_connections.append(session_id)
                
        # Clean up dead connections
        for session_id in dead_connections:
            self.disconnect(session_id)
            
    def get_connection_count(self) -> int:
        """Get count of active connections."""
        return len(self.active_connections)
    
    def is_connected(self, session_id: str) -> bool:
        """Check if a session has an active connection."""
        return session_id in self.active_connections


# Global singleton instance
manager = ConnectionManager()

