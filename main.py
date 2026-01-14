from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime
import asyncio

from database import engine, SessionLocal
from models import Base, Machine

# =====================================================
# APP INIT
# =====================================================
app = FastAPI(title="Taco Group Live Production")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# DB INIT
# =====================================================
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =====================================================
# WEBSOCKET MANAGER
# =====================================================
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active_connections.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active_connections:
            self.active_connections.remove(ws)

    async def broadcast(self, data: dict):
        for ws in self.active_connections:
            await ws.send_json(data)

manager = ConnectionManager()

# =====================================================
# DASHBOARD DATA
# =====================================================
def get_dashboard_data(db: Session):
    data = {}
    machines = db.query(Machine).all()

    for m in machines:
        data.setdefault(m.location, []).append({
            "id": m.id,
            "name": m.name,
            "status": m.status,
            "target": m.target_qty,
            "produced": m.produced_qty,
            "remaining": max(m.target_qty - m.produced_qty, 0),
            "work_order": m.work_order,
            "pipe_size": m.pipe_size
        })
    return data

# =====================================================
# HTTP
# =====================================================
@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db)):
    return get_dashboard_data(db)

# =====================================================
# WEBSOCKET
# =====================================================
@app.websocket("/ws/dashboard")
async def ws_dashboard(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)

# =====================================================
# MACHINE CONTROLS
# =====================================================
@app.post("/api/machine/start")
async def start_machine(location: str, machine_id: int, db: Session = Depends(get_db)):
    m = db.query(Machine).filter(
        Machine.id == machine_id,
        Machine.location == location
    ).first()

    if not m:
        return {"ok": False}

    m.status = "running"
    m.last_tick_time = datetime.utcnow()
    db.commit()
    await manager.broadcast(get_dashboard_data(db))
    return {"ok": True}

@app.post("/api/machine/pause")
async def pause_machine(location: str, machine_id: int, db: Session = Depends(get_db)):
    m = db.query(Machine).filter(
        Machine.id == machine_id,
        Machine.location == location
    ).first()

    if not m:
        return {"ok": False}

    m.status = "paused"
    db.commit()
    await manager.broadcast(get_dashboard_data(db))
    return {"ok": True}

@app.post("/api/machine/stop")
async def stop_machine(location: str, machine_id: int, db: Session = Depends(get_db)):
    m = db.query(Machine).filter(
        Machine.id == machine_id,
        Machine.location == location
    ).first()

    if not m:
        return {"ok": False}

    m.status = "stopped"
    db.commit()
    await manager.broadcast(get_dashboard_data(db))
    return {"ok": True}

# =====================================================
# STEP-12 — AUTOMATIC METER COUNTER (REAL)
# =====================================================
async def automatic_meter_counter():
    while True:
        db = SessionLocal()
        try:
            machines = db.query(Machine).filter(Machine.status == "running").all()
            now = datetime.utcnow()
            updated = False

            for m in machines:
                if not m.seconds_per_meter:
                    continue

                if not m.last_tick_time:
                    m.last_tick_time = now
                    continue

                diff = (now - m.last_tick_time).total_seconds()

                if diff >= m.seconds_per_meter:
                    if m.produced_qty < m.target_qty:
                        m.produced_qty += 1
                        m.last_tick_time = now
                        updated = True

                        if m.produced_qty >= m.target_qty:
                            m.produced_qty = m.target_qty
                            m.status = "completed"

            if updated:
                db.commit()
                await manager.broadcast(get_dashboard_data(db))

        except Exception as e:
            print("AUTO METER ERROR:", e)
        finally:
            db.close()

        await asyncio.sleep(1)

# =====================================================
# SEED MACHINES
# =====================================================
def seed_machines(db: Session):
    if db.query(Machine).count() > 0:
        return

    locations = {"Modan": 1, "Baldeya": 100, "Al-Khraj": 200}

    for loc, start_id in locations.items():
        for i in range(1, 13):
            db.add(Machine(
                id=start_id + i - 1,
                location=loc,
                name=f"Machine {i}",
                status="free",
                target_qty=100,
                produced_qty=0,
                pipe_size="20",
                seconds_per_meter=20
            ))
    db.commit()

# =====================================================
# STARTUP
# =====================================================
@app.on_event("startup")
async def startup_event():
    db = SessionLocal()
    seed_machines(db)
    db.close()

    asyncio.create_task(automatic_meter_counter())
