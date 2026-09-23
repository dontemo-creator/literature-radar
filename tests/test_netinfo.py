# -*- coding: utf-8 -*-
"""Address classification: the phone must never be pointed at a VPN tunnel."""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from app import netinfo

fails = []


def check(name, got, want=True):
    ok = got == want
    if not ok:
        fails.append((name, got, want))
    print(f"  [{'OK ' if ok else 'FAIL'}] {name}: {got!r}")


CLASSIFY = [
    ("en0", "Wi-Fi", "wifi"),
    ("en1", "Ethernet Adapter (en1)", "ethernet"),
    ("en5", "Thunderbolt Bridge", "ethernet"),
    ("utun4", "", "tunnel"),          # Clash / WARP / Tailscale
    ("utun0", "", "tunnel"),
    ("ppp0", "", "tunnel"),
    ("ipsec0", "", "tunnel"),
    # Internet Sharing puts the hotspot here -- the phone's only usable address
    ("bridge100", "", "hotspot"),
    ("ap1", "", "hotspot"),
    ("vmnet1", "", "virtual"),
    ("awdl0", "", "virtual"),         # AirDrop link
    ("eth9", "", "other"),
]


def run():
    for iface, port, want in CLASSIFY:
        check("classify %s (%s)" % (iface, port or "-"), netinfo._classify(iface, port), want)

    def addr(ip, iface, kind, default=False):
        return netinfo.Address(ip=ip, iface=iface, kind=kind, port_name="", is_default=default)

    check("wifi is offered to the phone", addr("192.168.1.5", "en0", "wifi").reachable_hint)
    check("ethernet is offered", addr("10.0.0.9", "en1", "ethernet").reachable_hint)
    check("tunnel is never offered", addr("198.18.0.1", "utun4", "tunnel").reachable_hint, False)
    check("virtual is never offered", addr("192.168.64.1", "vmnet1", "virtual").reachable_hint, False)
    check("hotspot IS offered", addr("192.168.2.1", "bridge100", "hotspot").reachable_hint)
    check("link-local is never offered",
          addr("169.254.10.2", "en0", "wifi").reachable_hint, False)
    check("tunnel is labelled as such", "VPN" in addr("198.18.0.1", "utun4", "tunnel").label())

    # Whatever this machine looks like, the result must be self-consistent.
    addrs = netinfo.addresses()
    check("addresses() returns a list", isinstance(addrs, list))
    check("no loopback in the list", all(not a.ip.startswith("127.") for a in addrs))
    check("no duplicate addresses", len({a.ip for a in addrs}), len(addrs))
    check("usable ones sort first", [a.reachable_hint for a in addrs] ==
          sorted([a.reachable_hint for a in addrs], reverse=True))
    b = netinfo.best()
    check("best() is usable or None", b is None or b.reachable_hint)
    check("proxy_state has the expected keys",
          set(netinfo.proxy_state()) >= {"http", "https", "socks", "tunnels", "any"})
    check("firewall_state is known", netinfo.firewall_state() in ("on", "off", "unknown"))
    ok, why = netinfo.can_connect("127.0.0.1", 1)   # nothing listens on port 1
    check("can_connect reports refusal, not a crash", ok, False)
    check("  with a reason", bool(why))

    print("\n%s" % ("ALL NETINFO CHECKS PASS" if not fails else "FAILURES:"))
    for f in fails:
        print("   ", f)
    return len(fails)


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
