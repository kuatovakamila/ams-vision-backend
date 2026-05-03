from typing import List, Dict, Any, Optional
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


class AttendanceStats(BaseModel):
    total_employees: int
    present_today: int
    absent_today: int
    late_today: int
    on_time_today: int
    attendance_rate: float
    late_percentage: float
    work_start_time: str
    date: str


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
