# -*- coding: utf-8 -*-
"""Work out which of this machine's addresses a phone can actually reach.

A laptop typically has several IPv4 addresses and only one of them is useful:
VPN and proxy tools (Clash, Tailscale, WARP ...) add ``utun`` interfaces whose
addresses look plausible but are unreachable from the local network.  Listing
those first sends people to an address that can never work, so addresses are
classified by interface and ranked with the default-route interface first.
"""
from __future__ import annotations

import re
import socket
import subprocess
from dataclasses import dataclass

from .logging_util import get_logger

log = get_logger("netinfo")

TUNNEL_PREFIXES = ("utun", "tun", "ppp", "ipsec", "gif", "stf", "wg")
# NOTE: bridge* and ap* are deliberately absent here.  When this Mac shares its
# connection ("Internet Sharing"), macOS puts the hotspot on bridge100 (or ap1)
# at 192.168.2.1 -- that is precisely the address a phone joining the hotspot
# must use, so treating it as "virtual" would hide the only one that works.
VIRTUAL_PREFIXES = ("vmnet", "vnic", "awdl", "llw", "anpi", "vboxnet", "utap")
HOTSPOT_PREFIXES = ("bridge", "ap")


@dataclass
class Address:
    ip: str
    iface: str
    kind: str          # "wifi"|"ethernet"|"hotspot"|"tunnel"|"virtual"|"other"
    port_name: str     # macOS hardware port label, when known
    is_default: bool   # sits on the interface owning the default route

    @property
    def reachable_hint(self) -> bool:
        """Whether a phone on the same network could plausibly reach it."""
        return (self.kind in ("wifi", "ethernet", "hotspot")
                and not self.ip.startswith("169.254."))

    def label(self) -> str:
        bits = [self.iface]
        if self.port_name and self.port_name.lower() not in self.iface.lower():
            bits.append(self.port_name)
        if self.kind == "tunnel":
            bits.append("VPN/代理隧道")
        elif self.kind == "virtual":
            bits.append("虚拟接口")
        elif self.kind == "hotspot":
            bits.append("本机热点/网络共享")
        if self.is_default:
            bits.append("默认出口")
        return "，".join(bits)


def _run(cmd: list[str], timeout: float = 4.0) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout
    except Exception:
        return ""


def _hardware_ports() -> dict[str, str]:
    """macOS: map ``en0`` -> ``Wi-Fi``."""
    out, ports, name = _run(["networksetup", "-listallhardwareports"]), {}, ""
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("Hardware Port:"):
            name = line.split(":", 1)[1].strip()
        elif line.startswith("Device:"):
            dev = line.split(":", 1)[1].strip()
            if dev:
                ports[dev] = name
    return ports


def _default_iface() -> str:
    for line in _run(["netstat", "-rn", "-f", "inet"]).splitlines():
        parts = line.split()
        if parts and parts[0] == "default" and len(parts) >= 4:
            return parts[-1]
    return ""


def _classify(iface: str, port_name: str) -> str:
    low = iface.lower()
    if low.startswith(TUNNEL_PREFIXES):
        return "tunnel"
    if low.startswith(VIRTUAL_PREFIXES):
        return "virtual"
    if low.startswith(HOTSPOT_PREFIXES):
        return "hotspot"
    pn = (port_name or "").lower()
    if "wi-fi" in pn or "wifi" in pn or "airport" in pn:
        return "wifi"
    if "ethernet" in pn or "lan" in pn or "thunderbolt" in pn:
        return "ethernet"
    return "other"


def addresses() -> list[Address]:
    """Every usable IPv4 address, best candidate first."""
    ports = _hardware_ports()
    default = _default_iface()
    out: list[Address] = []
    seen: set[str] = set()

    text = _run(["ifconfig"])
    iface = ""
    for line in text.splitlines():
        m = re.match(r"^([a-zA-Z0-9_.]+):\s", line)
        if m:
            iface = m.group(1)
            continue
        m = re.search(r"^\s+inet (\d+\.\d+\.\d+\.\d+)", line)
        if not m or not iface:
            continue
        ip = m.group(1)
        if ip.startswith(("127.", "0.")) or ip in seen:
            continue
        seen.add(ip)
        port_name = ports.get(iface, "")
        out.append(Address(ip=ip, iface=iface, kind=_classify(iface, port_name),
                           port_name=port_name, is_default=(iface == default)))

    if not out:                       # ifconfig unavailable: fall back to a probe
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.settimeout(0.4)
            probe.connect(("8.8.8.8", 80))
            ip = probe.getsockname()[0]
            if not ip.startswith("127."):
                out.append(Address(ip, "?", "other", "", True))
        except OSError:
            pass
        finally:
            probe.close()

    rank = {"hotspot": 0, "wifi": 1, "ethernet": 2, "other": 3, "virtual": 4, "tunnel": 5}
    out.sort(key=lambda a: (0 if a.is_default and a.reachable_hint else 1,
                            rank.get(a.kind, 5),
                            0 if a.ip.startswith(("192.168.", "10.", "172.20.10.")) else 1))
    return out


def best() -> Address | None:
    for a in addresses():
        if a.reachable_hint:
            return a
    return None


def proxy_state() -> dict:
    """Whether a system proxy or tunnel is active -- both can break phone access."""
    out = _run(["scutil", "--proxy"])
    def flag(key: str) -> bool:
        m = re.search(key + r"\s*:\s*(\d+)", out)
        return bool(m and m.group(1) == "1")
    tunnels = [a for a in addresses() if a.kind == "tunnel"]
    return {
        "http": flag("HTTPEnable"),
        "https": flag("HTTPSEnable"),
        "socks": flag("SOCKSEnable"),
        "pac": flag("ProxyAutoConfigEnable"),
        "tunnels": [a.iface + " " + a.ip for a in tunnels],
        "any": flag("HTTPEnable") or flag("HTTPSEnable") or flag("SOCKSEnable")
               or flag("ProxyAutoConfigEnable") or bool(tunnels),
    }


def firewall_state() -> str:
    out = _run(["/usr/libexec/ApplicationFirewall/socketfilterfw", "--getglobalstate"])
    if "disabled" in out.lower():
        return "off"
    if "enabled" in out.lower():
        return "on"
    return "unknown"


def can_connect(ip: str, port: int, timeout: float = 3.0) -> tuple[bool, str]:
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect((ip, port))
        return True, "可连接"
    except ConnectionRefusedError:
        return False, "连接被拒绝（该地址上没有服务在监听）"
    except socket.timeout:
        return False, "超时（被拦截或路由劫持）"
    except OSError as exc:
        return False, "失败：{}".format(exc)
    finally:
        s.close()
