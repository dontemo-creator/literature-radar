#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Entry point for the Solid-State Battery Literature Radar.

    python3 run.py                 start the app and open the browser
    python3 run.py --no-browser    start the app only
    python3 run.py --refresh       run one refresh in the terminal and exit
    python3 run.py --reclassify    re-apply the current rules to stored papers
    python3 run.py --port 9000     use a specific port
    python3 run.py --stats         print a short summary and exit
"""
from __future__ import annotations

import argparse
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import config, fields, ingest, netinfo, qrcode, server, store  # noqa: E402
from app.logging_util import get_logger  # noqa: E402

log = get_logger("main")


def _field_label(field: str) -> str:
    pack = fields.get(field)
    if pack is not None:
        return pack.zh
    return "自定义方向" if fields.is_custom(field) else field


def _target_fields(explicit: str = "") -> list[str]:
    """Which directions a terminal command should act on.

    Defaults to the ones accounts have actually chosen, so a command never
    spends minutes scanning a direction nobody reads.
    """
    if explicit:
        return [explicit]
    active = store.active_fields()
    if active:
        return active
    stored = [row["field"] for row in store.field_summary()]
    return stored or [fields.default_id()]


def _print_stats() -> None:
    rows = store.field_summary()
    users = store.user_count()
    print()
    if not rows:
        print("  文献库还是空的。打开页面创建账号并选择研究方向后会自动抓取。")
        print()
        return
    print("  账号：{} 个".format(users))
    for row in rows:
        field = row["field"]
        s = store.stats(field)
        last = store.last_refresh(field)
        print("  ── {}（{}）".format(_field_label(field), field))
        print("     {} 篇（含摘要 {} 篇）　近 7 天 {} 篇".format(
            s.get("total") or 0, s.get("with_abs") or 0, s.get("week") or 0))
        if s.get("newest"):
            print("     出版日期范围 {} ~ {}".format(s.get("oldest") or "-", s.get("newest")))
        if last:
            print("     上次更新 {}（扫描 {}，命中 {}，新增 {}）".format(
                last.get("finished"), last.get("scanned"), last.get("matched"),
                last.get("added")))
    print()


def _print_qr(url: str, indent: str = "  ") -> None:
    """Show a scannable code so nobody has to type an address that changes
    every time the machine joins a different network."""
    try:
        colour = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
        art = qrcode.render(url, colour=colour, quiet=3)
    except Exception as exc:                      # never let this break startup
        log.debug("QR rendering skipped: %s", exc)
        return
    print()
    for line in art.splitlines():
        print(indent + line)
    print()


def _diagnose(port: int) -> int:
    """Explain, concretely, why a phone might not be reaching this machine."""
    import socket as _socket

    print("\n" + "=" * 66)
    print("  手机连接诊断")
    print("=" * 66)

    print("\n[1] 服务在哪个端口")
    # The port auto-advances when one is busy, so look across the range rather
    # than only at the configured number -- otherwise the diagnosis reports
    # "not running" while the app is happily serving one port over.
    import json as _json
    import urllib.request as _url
    found = []
    for cand in range(port, port + 20):
        probe = _socket.socket()
        probe.settimeout(0.25)
        try:
            probe.connect(("127.0.0.1", cand))
        except OSError:
            continue
        finally:
            probe.close()
        try:
            # Bypass any system proxy: we are testing the direct path, and a
            # proxy would answer for a server that is not actually reachable.
            opener = _url.build_opener(_url.ProxyHandler({}))
            with opener.open("http://127.0.0.1:%d/healthz" % cand, timeout=2) as r:
                info = _json.load(r)
            if info.get("ok"):
                found.append((cand, info.get("papers", 0)))
        except Exception:
            pass
    if not found:
        listening = False
        print("    在 {}–{} 上没找到本软件 —— 服务没在运行".format(port, port + 19))
        print("    先在另一个终端窗口执行： python3 run.py --lan")
    else:
        listening = True
        for cand, n in found:
            print("    端口 {} 上有本软件在运行（库内 {} 篇）".format(cand, n))
        if found[0][0] != port:
            print("    注意：{} 被占用了，实际用的是 {} —— 手机地址里的端口要跟着改"
                  .format(port, found[0][0]))
        port = found[0][0]

    addrs = netinfo.addresses()
    usable = [a for a in addrs if a.reachable_hint]
    print("\n[2] 本机地址")
    if not addrs:
        print("    未检测到任何网络地址 —— 电脑可能没连上网络。")
    for a in addrs:
        mark = "可用" if a.reachable_hint else "不可用"
        print("    {:<16} {:<38} {}".format(a.ip, a.label(), mark))
    if usable:
        url = "http://{}:{}/".format(usable[0].ip, port)
        print("\n    -> 手机上应该打开：{}".format(url))
        _print_qr(url, indent="       ")
    else:
        print("\n    -> 没有可用的局域网地址。请确认电脑已连上 Wi-Fi 或网线；")
        print("       若只剩 VPN 隧道地址，请先关闭 VPN 再试。")

    if listening and usable:
        ok, why = netinfo.can_connect(usable[0].ip, port)
        print("    从局域网地址 {}:{} 连接：{}".format(usable[0].ip, port, why))
        if not ok:
            print("    -> 服务没有监听局域网。请确认启动时带了 --lan")

    print("\n[3] 本机拦截")
    fw = netinfo.firewall_state()
    print("    macOS 应用防火墙：{}".format(
        {"off": "已关闭（不会拦截）", "on": "已开启",
         "unknown": "无法读取"}[fw]))
    if fw == "on":
        print("    -> 若仍连不上，在 系统设置 → 网络 → 防火墙 → 选项 中")
        print("       允许 Python 接受传入连接")

    proxy = netinfo.proxy_state()
    print("\n[4] 代理 / VPN")
    if proxy["any"]:
        on = [k for k in ("http", "https", "socks", "pac") if proxy[k]]
        if on:
            print("    本机系统代理已开启：{}".format("、".join(on)))
        for t in proxy["tunnels"]:
            print("    检测到隧道接口：{}".format(t))
        print("    -> 电脑上的代理通常不影响手机连入。")
        print("       但如果**手机上也装了代理/VPN**（Shadowrocket、Clash、Surge 等），")
        print("       它会把 http://{}... 的请求送去远端服务器而不是本地网络，".format(
            usable[0].ip if usable else "192.168.x.x"))
        print("       表现就是 Safari 提示无法连接。请在手机上二选一：")
        print("         a) 暂时关闭代理再打开页面；或")
        print("         b) 在代理规则里把该地址设为直连（绕过局域网）")
    else:
        print("    未检测到系统代理或隧道接口")

    print("\n[5] 还是不行的话，按顺序排查")
    print("    1. 手机与电脑是否连的同一个 Wi-Fi（注意 2.4G/5G 有时是两个网络，")
    print("       访客网络也算不同网络）")
    print("    2. 手机上关闭代理/VPN 再试")
    print("    3. 地址和端口是否抄对（端口被占用时程序会自动往后顺延，")
    print("       以启动时打印的那一行为准）")
    print("    4. 路由器是否开了「AP 隔离 / 客户端隔离」，开了的话同一 Wi-Fi 下")
    print("       设备之间无法互访，需要在路由器设置里关闭")
    print("    5. 手机浏览器地址要写全 http://，Safari 有时会当成搜索词")
    print("=" * 66 + "\n")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(add_help=True, description="文献雷达（按研究方向推送）")
    ap.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    ap.add_argument("--refresh", action="store_true", help="仅在终端执行一次更新后退出")
    ap.add_argument("--reclassify", action="store_true", help="用当前规则重新分类已存文献")
    ap.add_argument("--stats", action="store_true", help="打印统计后退出")
    ap.add_argument("--field", default="", metavar="ID",
                    help="只对某个研究方向执行（默认：所有账号在用的方向）")
    ap.add_argument("--list-fields", action="store_true", help="列出可选研究方向后退出")
    ap.add_argument("--window", type=int, default=None, help="更新回溯天数")
    ap.add_argument("--port", type=int, default=None, help="服务端口")
    ap.add_argument("--host", default=None, help="绑定地址（默认 127.0.0.1）")
    ap.add_argument("--lan", action="store_true",
                    help="同时监听局域网，便于手机访问（同一 Wi-Fi 下）")
    ap.add_argument("--diagnose", action="store_true",
                    help="排查手机连不上的原因")
    ap.add_argument("--qr", action="store_true",
                    help="只打印手机访问地址的二维码后退出")
    args = ap.parse_args(argv)

    # Line-buffer stdout so the startup banner appears immediately even when
    # the output is redirected to a file (block buffering would swallow it
    # until the process exits).
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass

    store.init()

    if args.qr:
        best = netinfo.best()
        port = args.port or int(config.get("server_port"))
        if not best:
            print("  未找到可用的局域网地址，请先连上 Wi-Fi 或运行 --diagnose")
            return 1
        url = "http://{}:{}/".format(best.ip, port)
        print("\n  手机扫码打开： {}".format(url))
        _print_qr(url)
        return 0

    if args.diagnose:
        return _diagnose(args.port or int(config.get("server_port")))

    if args.stats:
        _print_stats()
        return 0

    if args.list_fields:
        print("\n  可选研究方向：")
        for f in fields.summaries():
            print("    {:<24} {}  —  {}".format(f["id"], f["zh"], f["tagline"]))
        print("\n  也可以在页面上用关键词自定义一个方向。\n")
        return 0

    if args.reclassify:
        for field in _target_fields(args.field):
            print("  正在按当前规则重新分类「{}」…".format(_field_label(field)))
            res = ingest.reclassify(field)
            print("    {} 篇标签有更新，{} 篇已不符合规则被移除，现存 {} 篇".format(
                res["changed"], res["removed"], res["total"]))
        _print_stats()
        return 0

    if args.refresh:
        worst = 0
        for field in _target_fields(args.field):
            print("  正在更新「{}」（可能需要 1–3 分钟）…".format(_field_label(field)))
            try:
                res = ingest.refresh(field, window_days=args.window)
            except Exception as exc:
                print("    未完成：{}".format(exc))
                worst = 1
                continue
            print("    {}：扫描 {} 条，命中 {} 篇，新增 {} 篇，更新 {} 篇，用时 {} 秒".format(
                "完成" if res.get("ok") else "未完成", res.get("scanned"),
                res.get("matched"), res.get("added"), res.get("updated"),
                res.get("elapsed")))
            for err in (res.get("errors") or [])[:5]:
                print("    ! {}".format(err))
            if not res.get("ok"):
                worst = 1
        _print_stats()
        return worst

    host = args.host or ("0.0.0.0" if args.lan else config.get("server_host"))
    httpd, port = server.serve(host, args.port)
    local = "127.0.0.1" if host in ("0.0.0.0", "") else host
    url = "http://{}:{}/".format(local, port)

    print("\n" + "=" * 66)
    print("  {} v{}".format(config.APP_NAME, config.APP_VERSION))
    print("  本机地址： {}".format(url))
    if args.lan or host == "0.0.0.0":
        addrs = netinfo.addresses()
        usable = [a for a in addrs if a.reachable_hint]
        if usable:
            phone_url = "http://{}:{}/".format(usable[0].ip, port)
            print("  手机访问： 手机连同一 Wi-Fi，用相机扫码，或手动输入")
            print("             ->  {}".format(phone_url))
            for a in usable[1:]:
                print("                 http://{}:{}/   （{}）".format(a.ip, port, a.label()))
            _print_qr(phone_url, indent="             ")
        else:
            print("  手机访问： 未找到可用的局域网地址，请运行 python3 run.py --diagnose")
        for a in addrs:
            if not a.reachable_hint:
                print("             （{} 是{}，手机连不上，不要用）".format(a.ip, a.label()))
        proxy = netinfo.proxy_state()
        if proxy["any"]:
            print("  提醒：     本机开着代理/VPN；如果手机上也开着代理，需要让它")
            print("             放行局域网地址，否则请求会被送去远端而连不上")
        print("  注意：     已监听局域网，同一网络内的其他设备都能打开本页面")
        print("  连不上？   运行 python3 run.py --diagnose")
    else:
        print("  手机访问： 用 python3 run.py --lan 启动，即可在手机上打开")
    print("  数据目录： {}".format(config.DATA_DIR))
    print("  停止运行： 在此窗口按 Ctrl+C")
    print("=" * 66)
    if not store.user_count():
        print("  首次运行：打开页面创建账号，选好研究方向后会自动抓取近期文献，")
        print("            约需 2–4 分钟。手机用同一个账号登录即可同步。\n")
    else:
        rows = store.field_summary()
        if not rows:
            print("  已有账号但还没有选定研究方向；打开页面选择后会自动抓取。\n")
        for row in rows:
            should, reason = ingest.needs_refresh(row["field"])
            print("  {}：{} 篇；{}。".format(_field_label(row["field"]), row["n"], reason))
        print()

    if config.get("open_browser") and not args.no_browser:
        threading.Thread(target=lambda: (time.sleep(0.7), webbrowser.open(url)),
                         daemon=True).start()

    try:
        httpd.serve_forever(poll_interval=0.4)
    except KeyboardInterrupt:
        print("\n  正在停止…")
    finally:
        try:
            httpd.shutdown()
        except Exception:
            pass
        httpd.server_close()
    print("  已停止。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
