import uuid
import json
import asyncio
import threading
import os
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from codeguard.config import Config, load_config
from codeguard.cli import create_agent_from_config
from codeguard.governance import HITLStatus


SESSIONS_FILE = Path(__file__).parent.parent / ".codeguard" / "sessions.json"


class TaskRequest(BaseModel):
    task: str
    project_root: str = "."


class Session:
    def __init__(self, session_id: str, task: str, project_root: str):
        self.id = session_id
        self.task = task
        self.project_root = Path(project_root)
        self.status = "running"
        self.logs: list[str] = []
        self.agent = None
        self.config = load_config()
        self.hitl_pending = False

    def start(self):
        self.agent = create_agent_from_config(self.config, self.project_root)
        self.logs.append(f"Session started. Task: {self.task}")
        result = self.agent.run(self.task)
        self.status = result["status"]
        self.logs.append(f"Agent finished with status: {result['status']}")
        if "summary" in result:
            self.logs.append(f"Summary: {result['summary']}")
        if self.status == "HITL_PENDING":
            self.hitl_pending = True
        save_sessions()
        return result


def save_sessions():
    data = {}
    for sid, s in sessions.items():
        data[sid] = {
            "id": s.id,
            "task": s.task,
            "project_root": str(s.project_root),
            "status": s.status,
            "logs": s.logs,
        }
    SESSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SESSIONS_FILE.write_text(json.dumps(data, indent=2))


def load_sessions():
    if not SESSIONS_FILE.exists():
        return
    try:
        data = json.loads(SESSIONS_FILE.read_text())
        for sid, sdata in data.items():
            session = Session(sdata["id"], sdata["task"], sdata["project_root"])
            session.status = sdata.get("status", "done")
            session.logs = sdata.get("logs", [])
            sessions[sid] = session
    except Exception:
        pass


sessions: dict[str, Session] = {}


def create_app() -> FastAPI:
    app = FastAPI(title="CodeGuard", description="Coding Agent Harness WebUI")

    load_sessions()

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.post("/sessions")
    async def create_session(req: TaskRequest):
        session_id = str(uuid.uuid4())[:8]
        session = Session(session_id, req.task, req.project_root)
        sessions[session_id] = session
        thread = threading.Thread(target=session.start, daemon=True)
        thread.start()
        return {"session_id": session_id}

    @app.get("/sessions/{session_id}/files")
    async def list_files(session_id: str):
        session = sessions.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        project_root = Path(session.project_root)
        files = []
        for f in project_root.rglob("*"):
            if f.is_file() and ".codeguard" not in str(f) and "__pycache__" not in str(f):
                files.append({
                    "name": str(f.relative_to(project_root)),
                    "size": f.stat().st_size,
                })
        return {"files": files}

    @app.get("/sessions/{session_id}/files/{file_path:path}")
    async def read_file(session_id: str, file_path: str):
        session = sessions.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        full_path = Path(session.project_root) / file_path
        if not full_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        content = full_path.read_text(encoding="utf-8", errors="replace")
        return {"name": file_path, "content": content}

    @app.get("/sessions")
    async def list_sessions():
        return {"sessions": [
            {"id": s.id, "task": s.task, "status": s.status}
            for s in sessions.values()
        ]}

    @app.get("/sessions/{session_id}")
    async def get_session(session_id: str):
        session = sessions.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return {
            "id": session.id,
            "task": session.task,
            "status": session.status,
            "logs": session.logs,
            "hitl_pending": session.hitl_pending,
        }

    @app.post("/sessions/{session_id}/approve")
    async def approve_action(session_id: str):
        session = sessions.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        if session.agent and session.agent.hitl.status == HITLStatus.AWAITING_APPROVAL:
            session.agent.hitl.approve()
            session.hitl_pending = False
            session.logs.append("HITL action approved by user")
            return {"status": "approved"}
        raise HTTPException(status_code=400, detail="No pending approval")

    @app.post("/sessions/{session_id}/deny")
    async def deny_action(session_id: str):
        session = sessions.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        if session.agent and session.agent.hitl.status == HITLStatus.AWAITING_APPROVAL:
            session.agent.hitl.deny()
            session.hitl_pending = False
            session.logs.append("HITL action denied by user")
            return {"status": "denied"}
        raise HTTPException(status_code=400, detail="No pending approval")

    @app.websocket("/ws/{session_id}")
    async def websocket_endpoint(websocket: WebSocket, session_id: str):
        await websocket.accept()
        session = sessions.get(session_id)
        if not session:
            await websocket.send_text("Session not found")
            await websocket.close()
            return
        try:
            while True:
                await websocket.receive_text()
                if session.logs:
                    await websocket.send_text(json.dumps({"logs": session.logs}))
                await asyncio.sleep(0.5)
        except WebSocketDisconnect:
            pass

    @app.get("/")
    async def index():
        static_path = Path(__file__).parent.parent / "static" / "index.html"
        if static_path.exists():
            return FileResponse(static_path)
        return {"message": "CodeGuard API is running. Place static/index.html for WebUI."}

    return app