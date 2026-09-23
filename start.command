#!/bin/bash
# Double-click launcher for macOS.
cd "$(dirname "$0")" || exit 1
PY=""
for c in python3 /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
  if command -v "$c" >/dev/null 2>&1; then PY="$c"; break; fi
done
if [ -z "$PY" ]; then
  echo "找不到 python3。请先安装 Python 3.9 或更高版本。"
  read -r -p "按回车关闭…" _
  exit 1
fi
exec "$PY" run.py
