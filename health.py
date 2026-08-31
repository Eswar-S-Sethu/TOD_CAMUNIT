import psutil

from config import STORAGE_DIR


def get_health_stats():
    """Returns a dict of current system stats for reporting to the dashboard."""
    stats = {
        "cpu_percent":          psutil.cpu_percent(),
        "memory_percent":       psutil.virtual_memory().percent,
        "disk_percent":         None,
        "temperature_celsius":  None,
        "battery_percent":      None,
        "on_battery":           None,
    }

    # Disk usage for whichever drive holds the captures directory
    try:
        path = str(STORAGE_DIR.resolve()) if STORAGE_DIR.exists() else "."
        stats["disk_percent"] = psutil.disk_usage(path).percent
    except Exception:
        pass

    # CPU temperature — available on Linux/macOS; not on Windows
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            for entries in temps.values():
                if entries:
                    stats["temperature_celsius"] = round(entries[0].current, 1)
                    break
    except (AttributeError, Exception):
        pass

    # Battery / power — None if desktop or unsupported
    try:
        batt = psutil.sensors_battery()
        if batt is not None:
            stats["battery_percent"] = round(batt.percent, 1)
            stats["on_battery"]      = not batt.power_plugged
    except (AttributeError, Exception):
        pass

    return stats
