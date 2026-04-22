from typing import List, Dict, Any
from pydantic import BaseModel


class DashboardStats(BaseModel):
    total_users: int
    total_cameras: int
    active_cameras: int
    total_incidents: int
    open_incidents: int
    total_events: int
    entrance_events: int
    exit_events: int
    total_files: int
    system_uptime: str
    last_updated: str


class SystemHealth(BaseModel):
    database_status: str
    redis_status: str
    disk_usage: Dict[str, Any]
    memory_usage: Dict[str, Any]


class QuickStats(BaseModel):
    cameras: Dict[str, int]
    incidents: Dict[str, int]
    events: Dict[str, int]
    users: Dict[str, int]
    files: Dict[str, int]
