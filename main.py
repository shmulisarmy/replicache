from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from user import User
from action import AppendAction, DeleteAction, EditAction
from db import Db
from client import Client
import json
import uvicorn
import asyncio
from mutations_mutex import mutations_mutex_locked
from sse_starlette.sse import EventSourceResponse




app = FastAPI()


queue = []


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ideally restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = Db([
    User("John", 20, "john@example.com"),
    User("Jane", 21, "jane@example.com"),
    User("Alice", 22, "alice@example.com"),
    User("Bob", 23, "bob@example.com"),
])



clients: dict[str, WebSocket] = {}
client_data: dict[str, Client] = {}



actions = []


@app.get("/db")
def get_db():
    return db.data


# @app.on_event("startup")
# def 


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    global mutations_mutex_locked, actions
    await websocket.accept()
    clients[client_id] = websocket
    client_data[client_id] = Client(client_id, db.data_version)

    try:
        while True:
            data = await websocket.receive_text()
            action = json.loads(data)
            client = client_data[client_id]

            print(f"action: {action}")
            match action["type"]:
                case "add":
                    while mutations_mutex_locked:
                        await asyncio.sleep(0.3)
                        continue
                    actions.append(AppendAction(action["data"], action["key"], version=db.data_version, client_id=client.id, time=action['time']))
                case "edit":
                    while mutations_mutex_locked:
                        await asyncio.sleep(0.1)
                        continue
                    actions.append(EditAction(action["value"], action["key"], action["field"], version=db.data_version, client_id=client.id, time=action['time']))
                case "delete":
                    while mutations_mutex_locked:
                        await asyncio.sleep(0.1)
                        continue
                    actions.append(DeleteAction(action["key"], version=db.data_version, client_id=client.id, time=action['time']))


            await asyncio.sleep(0.4)
            messages = await db.handle_mutations(actions, key="name", logger = queue, clients=clients.keys())
            print(f"{messages = }")
            actions.clear()


            for cid, ws in clients.items():
                for msg in messages[cid]:
                    await ws.send_text(json.dumps(msg))
                messages[cid].clear()

    except WebSocketDisconnect:
        del clients[client_id]
        del client_data[client_id]








count = 0

@app.get("/inc")
async def inc():
    global count
    count += 1
    queue.append({"type": "inc", "count": count})
    return {"count": count}


@app.get("/logs")
async def logs():
    async def event_generator():
        try:
            while True:
                if len(queue) == 0:
                    await asyncio.sleep(0.1)
                    continue
                message = queue.pop()
                yield {"event": "log", "data": message}
        except asyncio.CancelledError:
            pass

    return EventSourceResponse(event_generator())

    

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)