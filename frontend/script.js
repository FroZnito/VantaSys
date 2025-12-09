
// Config
const API = '/api';
const FAST_RATE = 1000;
const SLOW_RATE = 5000;
const HISTORY_LEN = 300; 

// State
let charts = {};
let systemInfo = null;
let currentView = 'dashboard';
// Deep caches for inspector
let latestData = {
    cpu: null, mem: null, disk: null, net: null, sys: null, sensors: null
};

const historyStore = {
    cpu: Array(HISTORY_LEN).fill(0),
    mem: Array(HISTORY_LEN).fill(0),
    netIn: Array(HISTORY_LEN).fill(0),
    netOut: Array(HISTORY_LEN).fill(0)
};

// Utils
const formatBytes = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024, sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
};

const formatTime = (secs) => {
    const h = Math.floor(secs / 3600);
    const m = Math.floor((secs % 3600) / 60);
    const s = Math.floor(secs % 60);
    return `${h.toString().padStart(2,'0')}:${m.toString().padStart(2,'0')}:${s.toString().padStart(2,'0')}`;
};

const logEvent = (msg) => {
    const box = document.getElementById('event-log-list');
    const div = document.createElement('div');
    div.className = 'log-item new';
    div.innerText = `> ${msg}`;
    box.prepend(div); // Add to top
    if (box.children.length > 50) box.lastChild.remove();
};

// --- Initialization ---

async function init() {
    setupNavigation();
    initCharts(); 
    initAnalyticsCharts(); 

    setInterval(fastLoop, FAST_RATE);
    setInterval(slowLoop, SLOW_RATE);
    fastLoop();
    slowLoop();
}

function setupNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const viewId = item.getAttribute('data-view');
            navItems.forEach(n => n.classList.remove('active'));
            item.classList.add('active');
            
            document.querySelectorAll('.view-section').forEach(sec => sec.classList.remove('active'));
            document.getElementById(`view-${viewId}`).classList.add('active');
            currentView = viewId;

            logEvent(`Switched View: ${viewId.toUpperCase()}`);

            if (currentView === 'hardware') fetchNetstat();
            if (currentView === 'services') fetchServices();
        });
    });
}

// --- Loops ---

async function fastLoop() {
    try {
        const [cpu, mem, sensors] = await Promise.all([
            fetch(`${API}/cpu`).then(r=>r.json()),
            fetch(`${API}/memory`).then(r=>r.json()),
            fetch(`${API}/sensors`).then(r=>r.json())
        ]);
        
        latestData.cpu = cpu; latestData.mem = mem; latestData.sensors = sensors;
        updateConnection(true);
        
        historyStore.cpu.shift(); historyStore.cpu.push(cpu.usage_percent);
        historyStore.mem.shift(); historyStore.mem.push(mem.percent);
        
        if (currentView === 'dashboard') {
            renderCPU(cpu);
            renderMemory(mem);
            renderSensors(sensors);
        } else if (currentView === 'analytics') {
            updateAnalyticsCharts();
        }
    } catch (e) { updateConnection(false); }
}

async function slowLoop() {
    try {
        if (!systemInfo || !systemInfo.gpu || systemInfo.gpu.length === 0) {
            const res = await fetch(`${API}/system`);
            systemInfo = await res.json();
            latestData.sys = systemInfo;
            renderIdentity();
        }

        const [disks, net, procs] = await Promise.all([
            fetch(`${API}/disk/detailed`).then(r=>r.json()),
            fetch(`${API}/network/detailed`).then(r=>r.json()),
            fetch(`${API}/processes`).then(r=>r.json())
        ]);
        latestData.disk = disks; latestData.net = net;
        
        historyStore.netIn.shift(); historyStore.netIn.push(net.global_rate.download_speed);
        historyStore.netOut.shift(); historyStore.netOut.push(net.global_rate.upload_speed);

        if (currentView === 'dashboard') {
            renderDisks(disks);
            renderNetwork(net);
            renderProcs(procs);
        }

        if (systemInfo) {
            systemInfo.uptime_seconds += SLOW_RATE/1000;
            document.getElementById('sys-uptime').innerText = formatTime(systemInfo.uptime_seconds);
        }
    } catch(e) { console.error(e); }
}

function updateConnection(isUp) {
    const dot = document.getElementById('conn-dot');
    if (isUp) {
        dot.classList.remove('disconnected');
        dot.classList.add('connected');
    } else {
        dot.classList.remove('connected');
        dot.classList.add('disconnected');
    }
}

// --- Renderers ---

function renderIdentity() {
    if (!systemInfo) return;
    document.getElementById('sys-hostname').innerText = systemInfo.hostname;
    document.getElementById('sys-os-full').innerText = `${systemInfo.os_name} ${systemInfo.os_edition}`;
    document.getElementById('cpu-model').innerText = systemInfo.processor || systemInfo.machine_type;

    if (systemInfo.gpu && systemInfo.gpu.length > 0) document.getElementById('gpu-name').innerText = systemInfo.gpu[0].name;
    if (systemInfo.motherboard) {
        document.getElementById('mobo-name').innerText = `${systemInfo.motherboard.manufacturer} ${systemInfo.motherboard.product}`;
        document.getElementById('bios-ver').innerText = systemInfo.motherboard.bios_version;
    }
}

function renderCPU(data) {
    document.getElementById('cpu-val').innerText = Math.round(data.usage_percent) + '%';
    charts.cpuGauge.data.datasets[0].data = [data.usage_percent, 100 - data.usage_percent];
    charts.cpuGauge.data.datasets[0].backgroundColor[0] = data.usage_percent > 85 ? '#fb7185' : '#38bdf8';
    charts.cpuGauge.update();
    const histData = charts.cpu.data.datasets[0].data; histData.shift(); histData.push(data.usage_percent); charts.cpu.update('none');
    
    // Core Grid
    const coresDiv = document.getElementById('cpu-cores');
    if (coresDiv.children.length !== data.count_logical) {
        coresDiv.innerHTML = '';
        data.per_core_usage.forEach(() => {
            const tick = document.createElement('div'); tick.className = 'core-tick';
            const fill = document.createElement('div'); fill.className = 'core-fill';
            tick.appendChild(fill); coresDiv.appendChild(tick);
        });
    }
    const ticks = coresDiv.getElementsByClassName('core-fill');
    data.per_core_usage.forEach((val, i) => {
        if (ticks[i]) {
            ticks[i].style.height = val + '%';
            ticks[i].style.backgroundColor = val > 90 ? '#fb7185' : '#38bdf8';
        }
    });

    // CPU-Z Specs
    if (data.socket) document.getElementById('cpu-socket').innerText = data.socket;
    if (data.microcode) document.getElementById('cpu-stepping').innerText = data.microcode;
    if (data.l2_cache) document.getElementById('cpu-l2').innerText = data.l2_cache;
    if (data.l3_cache) document.getElementById('cpu-l3').innerText = data.l3_cache;
}

function renderMemory(data) {
    document.getElementById('mem-used').innerText = formatBytes(data.used);
    document.getElementById('mem-free').innerText = formatBytes(data.available);
    document.getElementById('ram-fill-bar').style.height = data.percent + '%';

    // Dense Modules Info
    const modCount = document.getElementById('mem-modules-count');
    if (data.modules && data.modules.length > 0) {
        modCount.innerText = `${data.modules.length} Stick(s) Detected`;
        // We could render a list here if space allowed, 
        // but for now the count is a good indicator of successful reading
    } else {
        modCount.innerText = "Analyzing...";
    }
}

function renderSensors(data) {
    const container = document.getElementById('sensor-container');
    container.innerHTML = '';
    const allTemps = [];
    Object.values(data.temperatures).forEach(g => allTemps.push(...g));
    if (allTemps.length === 0 && !data.battery) {
        container.innerHTML = '<div style="color:var(--text-muted); font-size:0.8rem;">No sensor data</div>'; return;
    }
    allTemps.slice(0, 5).forEach(r => { 
        const div = document.createElement('div'); div.className = 'sensor-item';
        div.innerHTML = `<div class="sensor-label"><ion-icon name="thermometer-outline"></ion-icon> ${r.label}</div><div class="sensor-val ${r.current > 80 ? 'val-hot':''}">${r.current.toFixed(0)}°C</div>`;
        container.appendChild(div);
    });
}

function renderDisks(data) {
    const container = document.getElementById('disk-grid');
    container.innerHTML = '';
    data.partitions.forEach(p => {
        const div = document.createElement('div'); div.className = 'mini-card';
        div.innerHTML = `<div style="font-weight:600;font-size:0.9rem;margin-bottom:5px;">${p.mountpoint}</div><div style="font-size:0.75rem;color:var(--text-muted);">${formatBytes(p.free)} Free</div><div style="height:4px;background:rgba(255,255,255,0.1);margin-top:8px;border-radius:2px;"><div style="height:100%;width:${p.percent}%;background:var(--secondary);border-radius:2px;"></div></div>`;
        container.appendChild(div);
    });
}

function renderNetwork(data) {
    const grid = document.getElementById('net-grid');
    grid.innerHTML = '';
    data.interfaces.forEach(iface => {
        if (!iface.is_up) return;
        const div = document.createElement('div'); div.className = `mini-card ${iface.is_up ? 'active' : ''}`;
        div.innerHTML = `<div style="font-weight:600;font-size:0.85rem;margin-bottom:4px;">${iface.name.substring(0,8)}</div><div style="font-size:0.7rem;color:var(--text-muted);font-family:var(--font-mono);">${iface.ip_address||'---'}</div><div style="display:flex;gap:10px;margin-top:8px;font-size:0.7rem;"><span style="color:var(--accent)">↓${formatBytes(iface.bytes_recv/1024/1024)}M</span><span style="color:var(--primary)">↑${formatBytes(iface.bytes_sent/1024/1024)}M</span></div>`;
        grid.appendChild(div);
    });
    const downHist = charts.net.data.datasets[0].data; const upHist = charts.net.data.datasets[1].data;
    downHist.shift(); downHist.push(data.global_rate.download_speed);
    upHist.shift(); upHist.push(data.global_rate.upload_speed);
    charts.net.update('none');
}

function renderProcs(data) {
    const tbody = document.getElementById('proc-list');
    tbody.innerHTML = '';
    data.forEach(p => {
        const row = document.createElement('tr');
        row.onclick = () => inspect('process', p.pid);
        row.innerHTML = `<td>${p.name.substring(0,18)}</td><td style="color:var(--text-muted);font-family:var(--font-mono);">${p.pid}</td><td style="text-align:right;font-weight:700;color:var(--primary);">${p.cpu_percent.toFixed(1)}%</td>`;
        tbody.appendChild(row);
    });
}

async function fetchNetstat() {
    logEvent("Fetching active connections...");
    const tbody = document.getElementById('netstat-body');
    try {
        const res = await fetch(`${API}/network/connections`);
        const data = await res.json();
        tbody.innerHTML = '';
        data.forEach(c => {
            const row = document.createElement('tr');
            row.innerHTML = `<td style="color:var(--text-muted)">${c.pid||'-'}</td><td style="font-weight:600;color:var(--primary)">${c.process_name||'?'}</td><td>${c.type}</td><td>${c.laddr}</td><td>${c.raddr}</td><td><span class="badge">${c.status}</span></td>`;
            tbody.appendChild(row);
        });
    } catch(e) { tbody.innerHTML = '<tr><td colspan="6">Failed to load</td></tr>'; }
}

async function fetchServices() {
    logEvent("Fetching Windows Services...");
    const tbody = document.getElementById('svc-body');
    try {
        const res = await fetch(`${API}/services`);
        if (!res.ok) throw new Error("API Error");
        const data = await res.json();
        tbody.innerHTML = '';
        
        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6">No services found (Check Permissions).</td></tr>';
            return;
        }

        const limit = 100;
        data.slice(0,limit).forEach(s => {
            const row = document.createElement('tr');
            const statusColor = s.status === 'running' ? 'var(--accent)' : 'var(--danger)';
            row.innerHTML = `
                <td style="font-weight:600">${s.name}</td>
                <td>${s.display_name}</td>
                <td style="color:${statusColor}">${s.status.toUpperCase()}</td>
                <td>${s.start_type}</td>
                <td style="font-family:var(--font-mono)">${s.pid || '-'}</td>
                <td>${s.username || '-'}</td>
            `;
            tbody.appendChild(row);
        });
        logEvent(`Loaded ${data.length} Services.`);
    } catch(e) { 
        tbody.innerHTML = '<tr><td colspan="6">Fetch Failed (Is backend running?)</td></tr>'; 
        logEvent("Service Fetch Failed.");
    }
}

// --- Inspector Modal ---

async function inspect(type, id=null) {
    const modal = document.getElementById('inspector-modal');
    modal.classList.add('visible');
    const title = document.getElementById('modal-title');
    const content = document.getElementById('modal-content');
    const actions = document.getElementById('modal-actions');
    actions.innerHTML = '';
    
    logEvent(`Inspecting ${type} ${id || ''}`);

    if (type === 'process') {
        title.innerText = `Process Inspector [PID ${id}]`;
        content.innerHTML = 'Fetching detailed process structure...';
        try {
            const res = await fetch(`${API}/process/${id}`);
            const p = await res.json();
            content.innerHTML = renderJsonTree(p);
            
            const btn = document.createElement('button');
            btn.className = 'btn btn-danger';
            btn.innerText = 'Terminate Process';
            btn.onclick = () => killProc(id);
            actions.appendChild(btn);
        } catch(e) { content.innerText = "Error: " + e.message; }
        
    } else {
        // Inspect static/polled data
        title.innerText = `${type.toUpperCase()} Inspector`;
        const data = latestData[type];
        if (data) {
             content.innerHTML = renderJsonTree(data);
        } else {
            content.innerText = 'No data available to inspect.';
        }
    }
}

function renderJsonTree(obj) {
    if (typeof obj !== 'object' || obj === null) return `<span style="color:var(--accent)">${obj}</span>`;
    let html = '<div style="margin-left:10px; border-left:1px solid rgba(255,255,255,0.1); padding-left:10px;">';
    for (const [k, v] of Object.entries(obj)) {
        if (Array.isArray(v) && v.length > 20) {
             html += `<div style="margin-bottom:4px;"><strong style="color:var(--primary)">${k}</strong>: [Array(${v.length})]</div>`;
        } else {
             html += `<div style="margin-bottom:4px;"><strong style="color:var(--primary)">${k}</strong>: ${
                 (typeof v === 'object' && v!==null) ? renderJsonTree(v) : `<span style="color:var(--text-main)">${v}</span>`
             }</div>`;
        }
    }
    html += '</div>';
    return html;
}

async function killProc(pid) {
    if(confirm('Terminate?')) {
        await fetch(`${API}/process/${pid}/kill`, {method:'POST'});
        closeInspector();
        logEvent(`Killed PID ${pid}`);
    }
}

function closeInspector() {
    document.getElementById('inspector-modal').classList.remove('visible');
}

// Chart Inits
function initAnalyticsCharts() {
    const commonOpts = { responsive: true, maintainAspectRatio: false, animation: false, elements: { point: { radius: 0 } } };
    charts.longCpu = new Chart(document.getElementById('chartLongCPU'), { type: 'line', data: { labels: Array(HISTORY_LEN).fill(''), datasets: [{ label: 'CPU', data: historyStore.cpu, borderColor: '#38bdf8', borderWidth: 1, fill: true, backgroundColor: 'rgba(56,189,248,0.1)' }] }, options: commonOpts });
    charts.longMem = new Chart(document.getElementById('chartLongMem'), { type: 'line', data: { labels: Array(HISTORY_LEN).fill(''), datasets: [{ label: 'Mem', data: historyStore.mem, borderColor: '#818cf8', borderWidth: 1 }] }, options: commonOpts });
    charts.longNet = new Chart(document.getElementById('chartLongNet'), { type: 'line', data: { labels: Array(HISTORY_LEN).fill(''), datasets: [{ label: 'Down', data: historyStore.netIn, borderColor: '#2add7e' }, { label: 'Up', data: historyStore.netOut, borderColor: '#38bdf8' }] }, options: commonOpts });
}

function updateAnalyticsCharts() {
    charts.longCpu.data.datasets[0].data = historyStore.cpu; charts.longCpu.update('none');
    charts.longMem.data.datasets[0].data = historyStore.mem; charts.longMem.update('none');
    charts.longNet.data.datasets[0].data = historyStore.netIn; 
    charts.longNet.data.datasets[1].data = historyStore.netOut; charts.longNet.update('none');
}

// Chart Defaults
Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.color = '#64748b';
Chart.defaults.borderColor = 'rgba(255,255,255,0.03)';
window.addEventListener('load', init);

function initCharts() {
    const cpuCtx = document.getElementById('cpuHistory').getContext('2d');
    charts.cpu = new Chart(cpuCtx, { type: 'line', data: { labels: Array(40).fill(''), datasets: [{ data: Array(40).fill(0), borderColor: '#38bdf8', borderWidth:2, fill: true, backgroundColor:'rgba(56,189,248,0.2)' }] }, options: { responsive: true, maintainAspectRatio: false, animation: false, plugins:{legend:false}, scales:{x:{display:false}, y:{display:false, min:0, max:100}} } });
    const gaugeCtx = document.getElementById('cpuGauge').getContext('2d');
    charts.cpuGauge = new Chart(gaugeCtx, { type: 'doughnut', data: { datasets: [{ data: [0, 100], backgroundColor: ['#38bdf8', 'rgba(255,255,255,0.05)'], borderWidth:0, cutout:'88%', circumference:260, rotation:-130, borderRadius:20 }] }, options: { responsive:true, maintainAspectRatio:false, plugins:{tooltip:false} } });
    const netCtx = document.getElementById('netGlobalChart').getContext('2d');
    charts.net = new Chart(netCtx, { type: 'line', data: { labels: Array(40).fill(''), datasets: [{ data: Array(40).fill(0), borderColor: '#2add7e', fill:true, backgroundColor:'rgba(42,221,126,0.05)'}, { data: Array(40).fill(0), borderColor: '#818cf8', fill:true}] }, options: { responsive:true, maintainAspectRatio:false, animation:false, plugins:{legend:false}, scales:{x:{display:false}, y:{display:false}} } });
}
