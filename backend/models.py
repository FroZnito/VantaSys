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
    
    # New CPU-Z Fields
    code_name: Optional[str] = "Unknown"
    max_tdp: Optional[str] = "Unknown"
    package: Optional[str] = "Unknown"
    technology: Optional[str] = "Unknown" # nm
    core_voltage: Optional[str] = "Unknown"
    family: Optional[str] = "Unknown"
    model: Optional[str] = "Unknown"
    stepping: Optional[str] = "Unknown"
    ext_family: Optional[str] = "Unknown"
    ext_model: Optional[str] = "Unknown"
    revision: Optional[str] = "Unknown"
    instructions: Optional[str] = "MMX, SSE, SSE2, SSE3, SSSE3, SSE4.1, SSE4.2, EMT64, VT-x, AES, AVX, AVX2, FMA3" # Static/Approx
    
    # Clocks
    core_speed: Optional[float] = None
    multiplier: Optional[float] = None
    bus_speed: Optional[float] = 100.0
    rated_fsb: Optional[float] = None
    
    # Cache Detailed
    l1_data_cache: Optional[str] = None
    l1_inst_cache: Optional[str] = None
    
    threads: int = 0
    cores: int = 0

class RamModule(BaseModel):
    bank_label: str
    capacity: int
    speed: int
    manufacturer: str
    bank_label: str
    capacity: int
    speed: int
    manufacturer: str
    part_number: str
    serial_number: Optional[str] = None
    module_size: Optional[str] = None
    spd_ext: Optional[str] = "XMP 3.0" # Mock/Static if unavailable
    week_year: Optional[str] = None
    buffered: Optional[str] = "Unbuffered"
    correction: Optional[str] = "None"
    registered: Optional[str] = "No"
    rank: Optional[str] = "Single"
    
    # Timings Table (Mocked/Best Effort)
    cas_latency: Optional[str] = "CL30"
    ras_to_cas: Optional[str] = "36"
    ras_precharge: Optional[str] = "36"
    tras: Optional[str] = "76"
    trc: Optional[str] = "112"
    command_rate: Optional[str] = "1T"
    voltage_ram: Optional[str] = "1.35 V"

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
    
    # Global Memory Controller Info
    type: Optional[str] = "DDR5"
    channel_num: Optional[str] = "Dual"
    mem_controller_freq: Optional[str] = None
    dram_frequency: Optional[str] = None
    fsb_dram_ratio: Optional[str] = "1:30"
    total_cas: Optional[str] = None

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
    video_mode: Optional[str] = None
    driver_date: Optional[str] = None
    
    # Deep Dive GPU
    board_manuf: Optional[str] = "Unknown"
    code_name: Optional[str] = "Unknown"
    revision_gpu: Optional[str] = "Unknown"
    technology_gpu: Optional[str] = "Unknown" # nm
    rops_tmus: Optional[str] = "Unknown"
    shaders: Optional[str] = "Unknown"
    memory_type: Optional[str] = "GDDR6"
    bus_width: Optional[str] = "Unknown"
    bandwidth: Optional[str] = "Unknown"

class MotherboardInfo(BaseModel):
    manufacturer: str
    product: str
    serial: str
    bios_version: str
    bios_date: str
    # Deep Mobo
    chipset: Optional[str] = "Unknown"
    southbridge: Optional[str] = "Unknown"
    lpcio: Optional[str] = "Unknown"
    bios_brand: Optional[str] = "Unknown"
    graphic_interface_bus: Optional[str] = "PCI-Express 4.0"
    link_width_curr: Optional[str] = "x16"
    link_speed_curr: Optional[str] = "16.0 GT/s"

class SystemStaticInfo(BaseModel):
    hostname: str
    os_name: str
    os_release: str
    os_version: str
    os_edition: str
    machine_type: str
    processor: str
    cpu_marketing_name: Optional[str] = None
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
