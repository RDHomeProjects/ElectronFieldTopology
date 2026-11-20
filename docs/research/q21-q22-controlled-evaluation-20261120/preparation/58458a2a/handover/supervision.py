"""Memory-pressure supervision shared with the completed diagnosis."""
import subprocess
from pathlib import Path
UNIT = "matter-waves-q21-q22-evaluation.service"

def service_active():
    p = subprocess.run(['systemctl', 'is-active', UNIT], text=True, capture_output=True)
    return p.stdout.strip() in ('active', 'activating', 'deactivating')

def pressure(path=Path('/proc/pressure/memory')):
    return {label: {k: float(v) for k, v in (item.split('=') for item in fields)} for label, *fields in (row.split() for row in path.read_text().splitlines())}

def pressure_stop(sample, clock, began):
    available = sample['host']['available_gib']
    condition = available < 2 or (available < 4 and sample['pressure'].get('full', {}).get('avg10', 0) >= 20)
    began = clock if condition and began is None else began if condition else None
    return bool(condition and clock - began >= 30), began

def group_path():
    group = next(row.split('::', 1)[1] for row in Path('/proc/self/cgroup').read_text().splitlines() if row.startswith('0::'))
    return Path('/sys/fs/cgroup') / group.lstrip('/')

def group_info(group):
    result = {}
    for name in ['memory.current', 'memory.peak', 'memory.swap.current']:
        if (group / name).exists():
            result[name] = int((group / name).read_text())
    if (group / 'memory.events').exists():
        result['memory.events'] = {k: int(v) for k, v in (line.split() for line in (group / 'memory.events').read_text().splitlines())}
    if (group / 'memory.pressure').exists():
        result['memory.pressure'] = pressure(group / 'memory.pressure')
    return result
