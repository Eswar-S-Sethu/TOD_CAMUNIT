"""
WiFi and network information module.

Uses nmcli (NetworkManager CLI) for WiFi operations — standard on
modern Raspberry Pi OS (Bookworm) and Ubuntu.
Falls back gracefully on any failure so it never blocks the main loop.
"""

import socket
import subprocess

import psutil


def get_network_info():
    """
    Returns the current network state reported on every poll:
      {
        "ssid":         str | None,           # active WiFi SSID (None if disconnected)
        "ip_addresses": {"wlan0": "x.x.x.x"} # IPv4 per interface, loopback excluded
      }
    """
    result = {"ssid": None, "ip_addresses": {}}

    # Active WiFi SSID via nmcli
    try:
        out = subprocess.check_output(
            ["nmcli", "-t", "-f", "active,ssid", "dev", "wifi"],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
        )
        for line in out.strip().splitlines():
            if line.startswith("yes:"):
                ssid = line[4:]
                result["ssid"] = ssid if ssid else None
                break
    except Exception:
        pass

    # IPv4 addresses per interface (skip loopback)
    try:
        for iface, addrs in psutil.net_if_addrs().items():
            if iface.startswith("lo"):
                continue
            for addr in addrs:
                if addr.family == socket.AF_INET:
                    result["ip_addresses"][iface] = addr.address
    except Exception:
        pass

    return result


def scan_networks():
    """
    Triggers a WiFi rescan and returns visible networks sorted by signal strength.
    Each entry: {"ssid": str, "signal": int (0-100), "secured": bool}
    Blocks for up to 40 seconds — call from a background thread.
    """
    try:
        out = subprocess.check_output(
            ["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "dev", "wifi", "list", "--rescan", "yes"],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=40,
        )
        seen = set()
        networks = []
        for line in out.strip().splitlines():
            parts = line.split(":", 2)
            if len(parts) < 2:
                continue
            ssid = parts[0].strip()
            if not ssid or ssid in seen:
                continue
            seen.add(ssid)
            try:
                signal = int(parts[1])
            except ValueError:
                signal = 0
            secured = len(parts) > 2 and bool(parts[2].strip())
            networks.append({"ssid": ssid, "signal": signal, "secured": secured})
        return sorted(networks, key=lambda n: n["signal"], reverse=True)
    except Exception:
        return []


def connect_to_network(ssid, password):
    """
    Connects to the specified WiFi network using nmcli.
    Returns (success: bool, message: str).
    Blocks for up to 40 seconds — call from a background thread.
    """
    try:
        cmd = ["nmcli", "dev", "wifi", "connect", ssid]
        if password:
            cmd += ["password", password]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=40,
        )
        if result.returncode == 0:
            return True, f"Connected to '{ssid}'"
        msg = (result.stderr or result.stdout).strip()
        return False, msg or "Connection failed"
    except subprocess.TimeoutExpired:
        return False, "Connection attempt timed out after 40 s"
    except Exception as e:
        return False, str(e)
