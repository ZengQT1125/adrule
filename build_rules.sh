#!/usr/bin/env bash
# 拉取 -> 去重 -> 合并 -> 精简 -> 生成 dns.txt
# 用法: bash build_rules.sh   (需已安装 python3)
set -euo pipefail
cd "$(dirname "$0")"
python3 build_rules.py
