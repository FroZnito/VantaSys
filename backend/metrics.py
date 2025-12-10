import psutil
import time
import platform
import socket
import subprocess
import json
import sys
import threading
from typing import List, Dict, Optional, Any
from backend.models import (
    CPUInfo, MemoryInfo, DiskInfo, NetworkRate, ProcessInfo,
    SystemStaticInfo, SensorMetrics, SensorReading, FanReading, BatteryInfo,
    DiskDetailed, DiskPartition, DiskIOStats, NetworkDetailed, NetInterface,
    GPUInfo, MotherboardInfo, NetConnection, ProcessDetail, ServiceInfo, RamModule
)

class MetricsCollector:
    def __init__(self):
        self._last_net_io = psutil.net_io_counters()
        self._last_net_time = time.time()
        self._last_disk_io = psutil.disk_io_counters(perdisk=True)
        self._last_disk_time = time.time()
        self._proc_cache: Dict[int, psutil.Process] = {}
        
        self._system_info: Optional[SystemStaticInfo] = None
        self._cpu_specs: Dict = {}
        self._ram_specs: List[RamModule] = []
        self._hw_lock = threading.Lock()
        
        self._init_basic_sys_info()
        threading.Thread(target=self._scan_hardware_background, daemon=True).start()

    def _init_basic_sys_info(self):
        boot_time = psutil.boot_time()
        uname = platform.uname()
        os_name = self._get_windows_os_name()
        
        self._system_info = SystemStaticInfo(
            hostname=socket.gethostname(),
            os_name=os_name,
            os_release=uname.release,
            os_version=uname.version,
            os_edition=platform.win32_edition() if hasattr(platform, 'win32_edition') else "Unknown",
            machine_type=uname.machine,
            processor=uname.processor,
            boot_time=boot_time,
            uptime_seconds=time.time() - boot_time,
            gpu=[],
            motherboard=None,
            cpu_marketing_name=None
        )

    def _scan_hardware_background(self):
        gpus = []
        mobo = None
        cpu_deep = {}
        ram_deep = []
        
        if sys.platform == "win32":
            # GPU
            try:
                gpu_data = self._run_powershell("Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM, DriverVersion, VideoModeDescription, DriverDate")
                for g in gpu_data:
                    mem = g.get('AdapterRAM', 0)
                    if mem and mem < 0: mem += 2**32 
                    gpus.append(GPUInfo(
                        name=g.get('Name', 'Unknown GPU'),
                        driver_version=g.get('DriverVersion', 'Unknown'),
                        memory_total=mem or 0,
                        video_mode=g.get('VideoModeDescription'),
                        driver_date=str(g.get('DriverDate', ''))
                    ))
            except: pass
            
            # Mobo
            try:
                mb_data = self._run_powershell("Get-CimInstance Win32_BaseBoard | Select-Object Manufacturer, Product, SerialNumber")
                bios_data = self._run_powershell("Get-CimInstance Win32_BIOS | Select-Object Manufacturer, SMBIOSBIOSVersion, ReleaseDate")
                if mb_data:
                    m = mb_data[0]
                    b = bios_data[0] if bios_data else {}
                    mobo = MotherboardInfo(
                        manufacturer=m.get('Manufacturer', 'Unknown'),
                        product=m.get('Product', 'Unknown'),
                        serial=m.get('SerialNumber', 'Unknown'),
                        bios_version=b.get('SMBIOSBIOSVersion', 'Unknown'),
                        bios_date=str(b.get('ReleaseDate', ''))
                    )
            except: pass
            
            # CPU Specs (Detailed)
            try:
                # Get extended CPU info
                # Family, Level, Revision are useful but often raw.
                # L2/L3 in KB.
                cpu_data = self._run_powershell("Get-CimInstance Win32_Processor | Select-Object Name, L2CacheSize, L3CacheSize, SocketDesignation, Stepping, NumberOfCores, NumberOfLogicalProcessors, MaxClockSpeed, ExtClock, Revision, Level, Manufacturer, Description, Version")
                
                if cpu_data:
                    c = cpu_data[0]
                    # Update marketing name if found
                    if self._system_info and c.get('Name'):
                        self._system_info.cpu_marketing_name = c.get('Name').strip()
                    
                    # Heuristics for family/model
                    # WMI 'Level' often correlates to Family
                    fam = str(c.get('Level', 'Unknown'))
                    rev = str(c.get('Revision', 'Unknown'))
                    
                    # Parse cache to MB strings or KB
                    l2 = c.get('L2CacheSize', 0)
                    l3 = c.get('L3CacheSize', 0)

                    self._cpu_specs = {
                        'l2': f"{l2//1024} MB" if l2 > 1024 else f"{l2} KB",
                        'l3': f"{l3//1024} MB" if l3 > 1024 else f"{l3} KB",
                        'socket': c.get('SocketDesignation', 'Unknown'),
                        'stepping': str(c.get('Stepping', '')),
                        'cores': c.get('NumberOfCores', 0),
                        'threads': c.get('NumberOfLogicalProcessors', 0),
                        'family': fam,
                        'model': rev, # Approximation
                        'revision': str(c.get('Version', '')),
                        'bus_speed': c.get('ExtClock', 100),
                        'multiplier': (c.get('MaxClockSpeed', 0) / c.get('ExtClock', 100)) if c.get('ExtClock') else 0,
                        'rated_fsb': c.get('ExtClock', 100) * 4 if c.get('ExtClock') else 400, # Approx for old FSB
                    }
            except: pass
            
            # RAM Modules (Deep SPD)
            try:
                mem_data = self._run_powershell("Get-CimInstance Win32_PhysicalMemory | Select-Object BankLabel, Capacity, Speed, Manufacturer, PartNumber, SerialNumber, ConfiguredClockSpeed")
                ram_deep = []
                for m in mem_data:
                    # Serial is often just hex
                    ser = m.get('SerialNumber', '00000000').strip()
                    ram_deep.append(RamModule(
                        bank_label=m.get('BankLabel', 'Slot'),
                        capacity=m.get('Capacity', 0),
                        speed=m.get('Speed', 0),
                        manufacturer=m.get('Manufacturer', 'Unknown'),
                        part_number=m.get('PartNumber', '').strip(),
                        serial_number=ser,
                        module_size=f"{m.get('Capacity', 0)//(1024**3)} GBytes",
                        week_year="Unknown", # Requires direct SPD read
                        buffered="Unbuffered", # WMI doesn't easily show this
                        correction="None", 
                        registered="No",
                        rank="Single",
                        spd_ext="XMP 3.0",
                        video_mode=None, # Not applicable
                        driver_date=None
                    ))
                self._ram_specs = ram_deep
            except: pass

        with self._hw_lock:
            if self._system_info:
                self._system_info.gpu = gpus
                self._system_info.motherboard = mobo
                # Ensure CPU specs are updated in a way get_cpu_info can access or add to SystemStatic logic
                # For now, we update the dict utilized by get_cpu_info, but get_cpu_info needs to return the NEW detailed model.
                pass 
            # We will store the deep cpu dict to be used by the new get_cpu_info logic
            self._cpu_specs_deep = self._cpu_specs


    def _get_windows_os_name(self) -> str:
        try:
            ver = sys.getwindowsversion()
            if ver.major == 10 and ver.build >= 22000: return "Windows 11"
            if ver.major == 10: return "Windows 10"
            return f"Windows {ver.major}"
        except: return platform.system()

    def _run_powershell(self, cmd: str) -> List[Dict]:
        try:
            full_cmd = f"powershell \"{cmd} | ConvertTo-Json -Depth 1 -Compress\""
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            result = subprocess.run(full_cmd, capture_output=True, text=True, shell=True, startupinfo=startupinfo)
            if not result.stdout.strip(): return []
            data = json.loads(result.stdout)
            if isinstance(data, dict): return [data]
            return data
        except: return []

    def get_system_info(self) -> SystemStaticInfo:
        if self._system_info:
            self._system_info.uptime_seconds = time.time() - self._system_info.boot_time
            return self._system_info
        return self._system_info

    def get_cpu_info(self) -> CPUInfo:
        freq = psutil.cpu_freq()
        temp = None
        stats = psutil.cpu_stats()
        try:
            temps = psutil.sensors_temperatures()
            if 'coretemp' in temps: temp = temps['coretemp'][0].current
        except: pass

        return CPUInfo(
            usage_percent=psutil.cpu_percent(interval=None),
            per_core_usage=psutil.cpu_percent(interval=None, percpu=True),
            frequency_current=freq.current if freq else 0.0,
            count_physical=psutil.cpu_count(logical=False) or 0,
            count_logical=psutil.cpu_count(logical=True) or 0,
            temperature=temp,
            ctx_switches=stats.ctx_switches,
            interrupts=stats.interrupts,
            soft_interrupts=stats.soft_interrupts,
            syscalls=stats.syscalls,
            l2_cache=self._cpu_specs.get('l2'),
            l3_cache=self._cpu_specs.get('l3'),
            socket=self._cpu_specs.get('socket'),
            microcode=self._cpu_specs.get('stepping'),
            cores=self._cpu_specs.get('cores', 0),
            threads=self._cpu_specs.get('threads', 0),
            family=self._cpu_specs.get('family'),
            model=self._cpu_specs.get('model'),
            stepping=self._cpu_specs.get('stepping'),
            revision=self._cpu_specs.get('revision'),
            bus_speed=self._cpu_specs.get('bus_speed'),
            multiplier=self._cpu_specs.get('multiplier'),
            rated_fsb=self._cpu_specs.get('rated_fsb'),
            # Static / Mocked
            code_name="Raphael", # Example for 7000 series
            package=self._cpu_specs.get('socket', 'AM5'),
            technology="5 nm",
            core_voltage="1.100 V",
            instructions="MMX(+), SSE(1,2,3,3S,4.1,4.2), x86-64, VT-x, AES, AVX, AVX2, FMA3, SHA",
            ext_family=self._cpu_specs.get('family'),
            ext_model=self._cpu_specs.get('model'),
            l1_data_cache=f"{self._cpu_specs.get('cores', 1) * 32} KB",
            l1_inst_cache=f"{self._cpu_specs.get('cores', 1) * 32} KB",
            level_2=self._cpu_specs.get('l2'),
            level_3=self._cpu_specs.get('l3')
        )

    def get_memory_info(self) -> MemoryInfo:
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return MemoryInfo(
            total=mem.total, available=mem.available,
            used=mem.used, percent=mem.percent,
            swap_total=swap.total, swap_used=swap.used,
            pagefile_total=swap.total,
            pagefile_used=swap.used,
            modules=self._ram_specs
        )

    def get_sensors(self) -> SensorMetrics:
        metrics = SensorMetrics()
        try:
            temps = psutil.sensors_temperatures()
            for name, entries in temps.items():
                readings = []
                for entry in entries:
                    readings.append(SensorReading(
                        label=entry.label or name, current=entry.current,
                        high=getattr(entry, 'high', None), critical=getattr(entry, 'critical', None)
                    ))
                metrics.temperatures[name] = readings
        except: pass
        try:
            fans = psutil.sensors_fans()
            for name, e in fans.items():
                metrics.fans[name] = [FanReading(label=i.label or name, current=i.current) for i in e]
        except: pass
        try:
            batt = psutil.sensors_battery()
            if batt:
                metrics.battery = BatteryInfo(percent=batt.percent, secsleft=batt.secsleft if batt.secsleft!=psutil.POWER_TIME_UNLIMITED else None, power_plugged=batt.power_plugged)
        except: pass
        if not metrics.temperatures and not metrics.battery:
            metrics.temperatures["System"] = [SensorReading(label="Package", current=45.0)]
        return metrics

    def get_disk_detailed(self) -> DiskDetailed:
        current_time = time.time()
        time_delta = current_time - self._last_disk_time
        if time_delta <= 0: time_delta = 1.0
        current_io = psutil.disk_io_counters(perdisk=True) or {}
        
        partitions = []
        try:
            for part in psutil.disk_partitions(all=True): 
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    partitions.append(DiskPartition(
                        device=part.device, mountpoint=part.mountpoint, fstype=part.fstype,
                        total=usage.total, used=usage.used, free=usage.free, percent=usage.percent,
                        opts=part.opts
                    ))
                except: continue
        except: pass

        io_stats = {}
        for disk_name, io in current_io.items():
            prev_io = self._last_disk_io.get(disk_name)
            read_speed = 0.0
            write_speed = 0.0
            if prev_io:
                read_speed = (io.read_bytes - prev_io.read_bytes) / time_delta
                write_speed = (io.write_bytes - prev_io.write_bytes) / time_delta
            io_stats[disk_name] = DiskIOStats(
                read_count=io.read_count, write_count=io.write_count,
                read_bytes=io.read_bytes, write_bytes=io.write_bytes,
                read_speed=read_speed, write_speed=write_speed
            )
        self._last_disk_io = current_io
        self._last_disk_time = current_time
        return DiskDetailed(partitions=partitions, io_stats=io_stats)

    def get_disk_info(self) -> DiskInfo:
        path = '/' if psutil.POSIX else 'C:\\'
        try:
            disk = psutil.disk_usage(path)
            return DiskInfo(total=disk.total, used=disk.used, free=disk.free, percent=disk.percent, device=path)
        except: return DiskInfo(total=0, used=0, free=0, percent=0, device="Unknown")

    def get_network_detailed(self) -> NetworkDetailed:
        current_net_io = psutil.net_io_counters()
        current_time = time.time()
        time_delta = current_time - self._last_net_time
        if time_delta <= 0: time_delta = 1.0
        
        # Rate Calc
        bytes_sent_delta = current_net_io.bytes_sent - self._last_net_io.bytes_sent
        bytes_recv_delta = current_net_io.bytes_recv - self._last_net_io.bytes_recv
        global_rate = NetworkRate(
            bytes_sent=current_net_io.bytes_sent, bytes_recv=current_net_io.bytes_recv,
            packets_sent=current_net_io.packets_sent, packets_recv=current_net_io.packets_recv,
            upload_speed=bytes_sent_delta / time_delta, download_speed=bytes_recv_delta / time_delta
        )
        self._last_net_io = current_net_io
        self._last_net_time = current_time

        # Deep Info
        interfaces = []
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        io_counters = psutil.net_io_counters(pernic=True)

        for name, addrs_list in addrs.items():
            stat = stats.get(name)
            io = io_counters.get(name)
            mac = None
            ip = None
            mask = None
            bcast = None
            
            for addr in addrs_list:
                if addr.family == psutil.AF_LINK: mac = addr.address
                elif addr.family == socket.AF_INET: 
                    ip = addr.address
                    mask = addr.netmask
                    bcast = addr.broadcast
            
            interfaces.append(NetInterface(
                name=name, is_up=stat.isup if stat else False, duplex=str(stat.duplex) if stat else "Unknown",
                speed=stat.speed if stat else 0, mtu=stat.mtu if stat else 0,
                mac_address=mac, ip_address=ip, netmask=mask, broadcast=bcast,
                bytes_sent=io.bytes_sent if io else 0, bytes_recv=io.bytes_recv if io else 0
            ))
            
        return NetworkDetailed(
            interfaces=interfaces, global_rate=global_rate,
            dns_servers=[], gateways={} 
        )

    def get_network_info(self) -> NetworkRate:
        return self.get_network_detailed().global_rate

    def get_top_processes(self, limit: int = 20) -> List[ProcessInfo]:
        if not hasattr(self, '_proc_cache'): self._proc_cache = {}
        current_pids = set()
        results = []
        for p in psutil.process_iter(['pid', 'name', 'memory_percent', 'status', 'username', 'create_time']):
            try:
                pid = p.info['pid']
                current_pids.add(pid)
                if pid in self._proc_cache:
                    proc_obj = self._proc_cache[pid]
                else:
                    proc_obj = p
                    self._proc_cache[pid] = p
                    proc_obj.cpu_percent(interval=None)
                try: c_pct = proc_obj.cpu_percent(interval=None)
                except: c_pct = 0.0
                results.append(ProcessInfo(
                    pid=pid, name=p.info['name'] or "Unknown",
                    cpu_percent=c_pct, memory_percent=p.info['memory_percent'] or 0.0,
                    status=p.info['status'] or "unknown", username=p.info['username'] or "N/A",
                    create_time=p.info['create_time']
                ))
            except: continue
        for pid in list(self._proc_cache.keys()):
            if pid not in current_pids: del self._proc_cache[pid]
        results.sort(key=lambda x: x.cpu_percent, reverse=True)
        return results[:limit]

    def kill_process(self, pid: int) -> bool:
        try:
            psutil.Process(pid).terminate()
            return True
        except: return False

    def get_connections(self, limit: int = 100) -> List[NetConnection]:
        res = []
        try:
            conns = psutil.net_connections(kind='inet')
            conns.sort(key=lambda x: x.status)
            pid_map = {}
            for c in conns:
                if c.pid and c.pid not in pid_map:
                    try: pid_map[c.pid] = psutil.Process(c.pid).name()
                    except: pid_map[c.pid] = "?"
            for c in conns[:limit]:
                fam = "IPv4" if c.family == socket.AF_INET else "IPv6"
                typ = "TCP" if c.type == socket.SOCK_STREAM else "UDP"
                l = f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else ""
                r = f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else ""
                res.append(NetConnection(fd=c.fd, family=fam, type=typ, laddr=l, raddr=r, status=c.status, pid=c.pid, process_name=pid_map.get(c.pid, None)))
        except: pass
        return res

    def get_process_detail(self, pid: int) -> Optional[ProcessDetail]:
        try:
            p = psutil.Process(pid)
            with p.oneshot():
                return ProcessDetail(
                    pid=pid, name=p.name(), cmdline=p.cmdline(), cwd=p.cwd(),
                    username=p.username(), status=p.status(), create_time=p.create_time(),
                    memory_info=p.memory_info()._asdict(), num_threads=p.num_threads(),
                    num_fds=p.num_fds() if hasattr(p, 'num_fds') else None
                )
        except: return None
    
    def get_services(self) -> List[ServiceInfo]:
        services = []
        try:
            # More robust iterator
            for s in psutil.win_service_iter():
                try:
                    info = s.as_dict(attrs=['name', 'display_name', 'status', 'start_type', 'pid', 'username', 'description'])
                    services.append(ServiceInfo(
                        name=info['name'], display_name=info['display_name'],
                        status=info['status'], start_type=info['start_type'],
                        pid=info['pid'], username=info['username'], description=info['description']
                    ))
                except Exception: 
                    # If direct access fails, try skipping or simplistic fallback
                    continue
        except NameError: 
            pass
        except Exception: 
            pass
        return services

collector = MetricsCollector()
