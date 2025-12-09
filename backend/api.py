from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from backend.models import (
    CPUInfo, MemoryInfo, DiskInfo, NetworkRate, ProcessInfo,
    SystemStaticInfo, SensorMetrics, DiskDetailed, NetworkDetailed,
    NetConnection, ProcessDetail, ServiceInfo
)
from backend.metrics import collector
from backend.security import get_api_key
import os

app = FastAPI(
    title="VantaSys Monitor V6",
    description="Ultimate System Monitoring API - Omniscience Edition",
    version="6.0.0"
)

origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://localhost:6767",
    "http://127.0.0.1",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:6767",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

auth_dep = Depends(get_api_key)

# --- V1 Compatible Endpoints ---

@app.get("/api/cpu", response_model=CPUInfo, dependencies=[auth_dep], tags=["Core Metrics"])
async def get_cpu():
    return collector.get_cpu_info()

@app.get("/api/memory", response_model=MemoryInfo, dependencies=[auth_dep], tags=["Core Metrics"])
async def get_memory():
    return collector.get_memory_info()

@app.get("/api/disk", response_model=DiskInfo, dependencies=[auth_dep], tags=["Core Metrics"])
async def get_disk():
    return collector.get_disk_info()

@app.get("/api/network", response_model=NetworkRate, dependencies=[auth_dep], tags=["Core Metrics"])
async def get_network():
    return collector.get_network_info()

@app.get("/api/processes", response_model=List[ProcessInfo], dependencies=[auth_dep], tags=["Processes"])
async def get_processes(limit: int = 20):
    return collector.get_top_processes(limit=limit)

@app.get("/api/process/{pid}", response_model=ProcessDetail, dependencies=[auth_dep], tags=["Processes"])
async def get_process_detail(pid: int):
    proc = collector.get_process_detail(pid)
    if not proc: raise HTTPException(status_code=404, detail="Process not found")
    return proc

@app.post("/api/process/{pid}/kill", dependencies=[auth_dep], tags=["Processes"])
async def kill_process(pid: int):
    success = collector.kill_process(pid)
    if not success: raise HTTPException(status_code=400, detail="Failed to terminate")
    return {"status": "terminated", "pid": pid}

# --- V2/V3 Advanced Endpoints ---

@app.get("/api/system", response_model=SystemStaticInfo, dependencies=[auth_dep], tags=["System"])
async def get_system_info():
    return collector.get_system_info()

@app.get("/api/sensors", response_model=SensorMetrics, dependencies=[auth_dep], tags=["Hardware"])
async def get_sensors():
    return collector.get_sensors()

@app.get("/api/disk/detailed", response_model=DiskDetailed, dependencies=[auth_dep], tags=["Hardware"])
async def get_disk_detailed():
    return collector.get_disk_detailed()

@app.get("/api/network/detailed", response_model=NetworkDetailed, dependencies=[auth_dep], tags=["Hardware"])
async def get_network_detailed():
    return collector.get_network_detailed()

# --- V4 Deep Dive Endpoints ---

@app.get("/api/network/connections", response_model=List[NetConnection], dependencies=[auth_dep], tags=["Deep Dive"])
async def get_connections(limit: int = 100):
    return collector.get_connections(limit=limit)

# --- V6 Omniscience Endpoints ---

@app.get("/api/services", response_model=List[ServiceInfo], dependencies=[auth_dep], tags=["Omniscience"])
async def get_services():
    """Get all Windows Services."""
    return collector.get_services()

# Static Files
frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="static")

@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok", "version": "6.0.0", "mode": "omniscience"}
