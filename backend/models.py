from pydantic import BaseModel, Field
from typing import List, Optional, Dict

# --- Basic Metrics (V1) ---

class CPUInfo(BaseModel):
    usage_percent: float
    per_core_usage: List[float]
    frequency_current: Optional[float]
    count_physical: int
    count_logical: int
    temperature: Optional[float]
    # V6 Deep Dive
    ctx_switches: Optional[int] = None
    interrupts: Optional[int] = None
    soft_interrupts: Optional[int] = None
    syscalls: Optional[int] = None
    # V7 CPU-Z Specs
    l2_cache: Optional[str] = None
    l3_cache: Optional[str] = None
    socket: Optional[str] = None
    microcode: Optional[str] = None
    voltage: Optional[float] = None

class RamModule(BaseModel):
    bank_label: str
    capacity: int
    speed: int
    manufacturer: str
    part_number: str

class MemoryInfo(BaseModel):
    total: int
    available: int
    used: int
    percent: float
    swap_total: int
    swap_used: int
    pagefile_total: Optional[int] = None
    pagefile_used: Optional[int] = None
    # V7 Specs
    modules: List[RamModule] = Field(default_factory=list)

class DiskInfo(BaseModel):
    total: int
    used: int
    free: int
    percent: float
    device: str

class NetworkRate(BaseModel):
    bytes_sent: int
    bytes_recv: int
    packets_sent: int
    packets_recv: int
    upload_speed: float
    download_speed: float

class ProcessInfo(BaseModel):
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    status: str
    username: Optional[str] = None
    create_time: float

# --- Advanced Metrics (V2/V3) ---

class GPUInfo(BaseModel):
    name: str
    driver_version: str
    memory_total: int
    temperature: Optional[float] = None

class MotherboardInfo(BaseModel):
    manufacturer: str
    product: str
    serial: str
    bios_version: str
    bios_date: str

class SystemStaticInfo(BaseModel):
    hostname: str
    os_name: str
    os_release: str
    os_version: str
    os_edition: str
    machine_type: str
    processor: str
    boot_time: float
    uptime_seconds: float
    gpu: Optional[List[GPUInfo]] = None
    motherboard: Optional[MotherboardInfo] = None

class SensorReading(BaseModel):
    label: str
    current: float
    high: Optional[float] = None
    critical: Optional[float] = None

class FanReading(BaseModel):
    label: str
    current: int

class BatteryInfo(BaseModel):
    percent: float
    secsleft: Optional[int] = None
    power_plugged: Optional[bool] = None

class SensorMetrics(BaseModel):
    temperatures: Dict[str, List[SensorReading]] = Field(default_factory=dict)
    fans: Dict[str, List[FanReading]] = Field(default_factory=dict)
    battery: Optional[BatteryInfo] = None

class DiskPartition(BaseModel):
    device: str
    mountpoint: str
    fstype: str
    total: int
    used: int
    free: int
    percent: float
    opts: str 

class DiskIOStats(BaseModel):
    read_count: int
    write_count: int
    read_bytes: int
    write_bytes: int
    read_speed: float = 0.0
    write_speed: float = 0.0

class DiskDetailed(BaseModel):
    partitions: List[DiskPartition]
    io_stats: Dict[str, DiskIOStats]

class NetInterface(BaseModel):
    name: str
    is_up: bool
    duplex: str
    speed: int
    mtu: int
    mac_address: Optional[str]
    ip_address: Optional[str]
    netmask: Optional[str] 
    broadcast: Optional[str] 
    bytes_sent: int
    bytes_recv: int

class NetworkDetailed(BaseModel):
    interfaces: List[NetInterface]
    global_rate: NetworkRate
    dns_servers: List[str] 
    gateways: Dict[str, str] 

# --- Deep Dive Metrics (V4) ---

class NetConnection(BaseModel):
    fd: int = -1
    family: str
    type: str
    laddr: str
    raddr: str
    status: str
    pid: Optional[int] = None
    process_name: Optional[str] = None

# --- Process Details (V5) ---

class ProcessDetail(BaseModel):
    pid: int
    name: str
    cmdline: List[str]
    cwd: str
    username: str
    status: str
    create_time: float
    memory_info: Dict[str, int]
    num_threads: int
    num_fds: Optional[int] = None

# --- Services (V6) ---

class ServiceInfo(BaseModel):
    name: str
    display_name: str
    status: str 
    start_type: str 
    pid: Optional[int] = None
    username: Optional[str] = None
    description: Optional[str] = None
