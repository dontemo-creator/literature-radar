#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A minimal Chrome DevTools Protocol client -- test tooling, not shipped code.

Headless Chrome refuses a window narrower than 500 px, so verifying the phone
layout (and the touch interactions on it) needs device emulation over CDP.
Implements just enough WebSocket to send commands and read replies, using only
the standard library.
"""
from __future__ import annotations

import base64
import json
import os
import socket
import struct
import shutil
import subprocess
import tempfile
import time
import urllib.request

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


class WS:
    """Text-frame-only WebSocket client (client->server frames are masked)."""

    def __init__(self, url: str, timeout: float = 25.0):
        assert url.startswith("ws://"), url
        rest = url[len("ws://"):]
        hostport, _, path = rest.partition("/")
        host, _, port = hostport.partition(":")
        self.sock = socket.create_connection((host, int(port or 80)), timeout=timeout)
        self.sock.settimeout(timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        req = (
            "GET /{} HTTP/1.1\r\nHost: {}\r\nUpgrade: websocket\r\n"
            "Connection: Upgrade\r\nSec-WebSocket-Key: {}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        ).format(path, hostport, key)
        self.sock.sendall(req.encode())
        head = b""
        while b"\r\n\r\n" not in head:
            chunk = self.sock.recv(1)
            if not chunk:
                raise ConnectionError("handshake closed early")
            head += chunk
        if b"101" not in head.split(b"\r\n")[0]:
            raise ConnectionError("upgrade refused: " + head[:120].decode("latin1"))
        self.buf = b""

    def send(self, text: str) -> None:
        payload = text.encode("utf-8")
        n = len(payload)
        frame = bytearray([0x81])
        if n < 126:
            frame.append(0x80 | n)
        elif n < 1 << 16:
            frame.append(0x80 | 126)
            frame += struct.pack(">H", n)
        else:
            frame.append(0x80 | 127)
            frame += struct.pack(">Q", n)
        mask = os.urandom(4)
        frame += mask
        frame += bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        self.sock.sendall(bytes(frame))

    def _read(self, n: int) -> bytes:
        while len(self.buf) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("socket closed")
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def recv(self) -> str:
        while True:
            b0, b1 = self._read(2)
            opcode = b0 & 0x0F
            length = b1 & 0x7F
            if length == 126:
                length = struct.unpack(">H", self._read(2))[0]
            elif length == 127:
                length = struct.unpack(">Q", self._read(8))[0]
            data = self._read(length) if length else b""
            if opcode == 0x9:                      # ping -> pong
                self.sock.sendall(b"\x8a" + bytes([0x80 | len(data)]) + os.urandom(4) + data)
                continue
            if opcode == 0x8:
                raise ConnectionError("server closed")
            if opcode in (0x1, 0x0):
                return data.decode("utf-8", "replace")

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass


class Browser:
    def __init__(self, url: str, width: int = 390, height: int = 844,
                 scale: float = 3.0, port: int = 9222):
        self.port = port
        # A fresh profile per run: otherwise a service worker cached by an
        # earlier run would serve a stale UI and the test would check nothing.
        self.profile = tempfile.mkdtemp(prefix="cdp-profile-")
        self.proc = subprocess.Popen(
            [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
             "--no-first-run", "--no-default-browser-check",
             "--remote-debugging-port=%d" % port,
             "--user-data-dir=" + self.profile,
             "--window-size=800,900", "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        target = None
        for _ in range(60):
            time.sleep(0.35)
            try:
                with urllib.request.urlopen(
                        "http://127.0.0.1:%d/json/list" % port, timeout=3) as r:
                    for t in json.load(r):
                        if t.get("type") == "page" and t.get("webSocketDebuggerUrl"):
                            target = t
                            break
                if target:
                    break
            except Exception:
                continue
        if not target:
            raise RuntimeError("could not reach Chrome's debugger")
        self.ws = WS(target["webSocketDebuggerUrl"])
        self._id = 0
        self.call("Page.enable")
        self.call("Runtime.enable")
        self.call("Emulation.setDeviceMetricsOverride", {
            "width": width, "height": height, "deviceScaleFactor": scale,
            "mobile": True, "screenWidth": width, "screenHeight": height})
        self.call("Emulation.setTouchEmulationEnabled", {"enabled": True, "maxTouchPoints": 5})
        self.call("Emulation.setUserAgentOverride", {"userAgent":
            "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"})
        self.call("Page.navigate", {"url": url})

    def call(self, method: str, params: dict | None = None, timeout: float = 25.0):
        self._id += 1
        mid = self._id
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        deadline = time.time() + timeout
        while time.time() < deadline:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError("%s -> %s" % (method, msg["error"]))
                return msg.get("result", {})
        raise TimeoutError(method)

    def js(self, expr: str):
        r = self.call("Runtime.evaluate", {
            "expression": expr, "returnByValue": True, "awaitPromise": True})
        res = r.get("result", {})
        if r.get("exceptionDetails"):
            raise RuntimeError("JS error: %s" % r["exceptionDetails"].get("text"))
        return res.get("value")

    def wait_js(self, expr: str, tries: int = 40, delay: float = 0.3):
        for _ in range(tries):
            try:
                if self.js(expr):
                    return True
            except RuntimeError:
                pass
            time.sleep(delay)
        return False

    def tap(self, selector: str, verify: bool = True) -> bool:
        """Scroll the element into view, tap its centre, and confirm the hit.

        Without the scroll-and-verify step a tap on an off-screen element
        silently lands on whatever is at those coordinates, and the test
        reports a pass for an interaction that never happened.
        """
        self.js("(function(){var e=document.querySelector(%s);"
                "if(e&&e.scrollIntoView)e.scrollIntoView({block:'center'});})()"
                % json.dumps(selector))
        time.sleep(0.35)
        info = self.js(
            "(function(){var e=document.querySelector(%s);if(!e)return null;"
            "var r=e.getBoundingClientRect();"
            "if(r.width<1||r.height<1)return {vis:false};"
            "var x=r.left+r.width/2, y=r.top+r.height/2;"
            "if(y<0||y>window.innerHeight||x<0||x>window.innerWidth)return {vis:false};"
            "var h=document.elementFromPoint(x,y);"
            "var ok=!!(h&&(h===e||e.contains(h)||(h.closest&&h.closest(%s)===e)));"
            "return {vis:true,x:x,y:y,ok:ok,"
            "hit:h?h.tagName.toLowerCase()+'.'+String(h.className||'').split(' ')[0]:'null'};})()"
            % (json.dumps(selector), json.dumps(selector)))
        if not info or not info.get("vis"):
            print("       tap(%s): not visible" % selector)
            return False
        if verify and not info.get("ok"):
            print("       tap(%s): blocked by %s" % (selector, info.get("hit")))
            return False
        for kind in ("mousePressed", "mouseReleased"):
            self.call("Input.dispatchMouseEvent", {
                "type": kind, "x": info["x"], "y": info["y"], "button": "left",
                "clickCount": 1, "pointerType": "mouse"})
        return True

    def tap_at(self, x: float, y: float) -> None:
        for kind in ("mousePressed", "mouseReleased"):
            self.call("Input.dispatchMouseEvent", {
                "type": kind, "x": x, "y": y, "button": "left",
                "clickCount": 1, "pointerType": "mouse"})

    def shot(self, path: str, full: bool = False) -> None:
        params = {"format": "png"}
        if full:
            params["captureBeyondViewport"] = True
        data = self.call("Page.captureScreenshot", params)["data"]
        with open(path, "wb") as fh:
            fh.write(base64.b64decode(data))

    def close(self) -> None:
        try:
            self.ws.close()
        finally:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=6)
            except subprocess.TimeoutExpired:
                self.proc.kill()
            shutil.rmtree(self.profile, ignore_errors=True)
