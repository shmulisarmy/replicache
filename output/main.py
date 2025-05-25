"""Main FastAPI application with WebSocket endpoints."""

import asyncio
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from models.user import User
from core.database import Database
from core.websocket_manager import WebSocketManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Real-time Sync API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database with sample data
initial_users = [
    User("John", 20, "john@example.com"),
    User("Jane", 21, "jane@example.com"),
    User("Alice", 22, "alice@example.com"),
    User("Bob", 23, "bob@example.com"),
]

database = Database(initial_users, key_extractor=lambda user: user.name)
websocket_manager = WebSocketManager(database)


@app.get("/")
async def root():
    """Root endpoint returning API information."""
    return {
        "message": "Real-time Sync API",
        "version": "1.0.0",
        "endpoints": {
            "websocket": "/ws/{client_id}",
            "database": "/db"
        }
    }


@app.get("/db")
async def get_database():
    """Get current database state."""
    return {
        "data": database.get_all_data(),
        "version": database.get_data_version(),
        "connected_clients": len(websocket_manager.clients)
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "database_version": database.get_data_version(),
        "connected_clients": len(websocket_manager.clients)
    }


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    WebSocket endpoint for real-time communication with clients.
    
    Args:
        websocket: WebSocket connection
        client_id: Unique identifier for the client
    """
    try:
        await websocket_manager.connect(websocket, client_id)
        
        while True:
            message = await websocket.receive_text()
            await asyncio.sleep(0.5)
            await websocket_manager.handle_message(client_id, message)
            
    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {str(e)}")
    finally:
        websocket_manager.disconnect(client_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

