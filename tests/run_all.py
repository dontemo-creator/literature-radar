#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run every test suite in its own process and report a single verdict.

    python3 tests/run_all.py

Each suite runs separately because two of them rebind ``config.DB_PATH`` to a
temporary database, which must happen before anything opens a connection.
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUITES = [
    ("textnorm  文本归一化", "test_textnorm.py"),
    ("classify  分类与相关性规则（固态电池）", "test_classify.py"),
    ("fields    研究方向之间互不误收", "test_field_isolation.py"),
    ("sources   数据源解析与日期逻辑", "test_sources.py"),
    ("store     数据库、账号、检索与分面", "test_store.py"),
    ("netinfo   局域网地址识别与代理检测", "test_netinfo.py"),
    ("qrcode    二维码编码（Vision 实解码验证）", "test_qrcode.py"),
    ("api       HTTP 接口、登录与方向切换", "test_api.py"),
    ("live      实时全学科检索（OpenAlex/Crossref）", "test_live_search.py"),
    ("desktop   桌面布局与换方向（需 Chrome）", "test_desktop.py"),
    ("phone     手机布局与触屏交互（需 Chrome）", "test_phone.py"),
]


def main() -> int:
    results = []
    for label, script in SUITES:
        print("\n" + "=" * 68)
        print("  " + label)
        print("=" * 68)
        proc = subprocess.run([sys.executable, str(HERE / script)],
                              capture_output=True, text=True)
        out = proc.stdout.rstrip()
        # Show the tail on success, everything on failure.
        lines = out.splitlines()
        if proc.returncode == 0:
            print("\n".join(lines[-3:]) if len(lines) > 3 else out)
        else:
            print(out)
            if proc.stderr.strip():
                print(proc.stderr.rstrip())
        results.append((label, proc.returncode))

    print("\n" + "=" * 68)
    bad = [l for l, rc in results if rc != 0]
    for label, rc in results:
        print("  {}  {}".format("通过 PASS" if rc == 0 else "失败 FAIL", label))
    print("=" * 68)
    if bad:
        print("  %d/%d 套件失败" % (len(bad), len(results)))
        return 1
    print("  全部 %d 个套件通过" % len(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
