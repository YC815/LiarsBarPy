#!/usr/bin/env python3
import sys
import os

# 打印當前工作目錄和 Python 路徑
print(f"Current working directory: {os.getcwd()}")
print(f"Python path: {sys.path}")

# 嘗試手動添加模組路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
print(f"Updated Python path: {sys.path}")

# 嘗試導入模組
try:
    from liars_bar.core.game import Game
    print("Successfully imported Game from liars_bar.core.game")
except ImportError as e:
    print(f"Import error: {e}")

try:
    from core.game import Game
    print("Successfully imported Game from core.game")
except ImportError as e:
    print(f"Import error: {e}")

# 查看文件結構
for root, dirs, files in os.walk('.', topdown=True):
    level = root.count(os.sep)
    indent = ' ' * 4 * level
    print(f"{indent}{os.path.basename(root)}/")
    sub_indent = ' ' * 4 * (level + 1)
    for f in files:
        print(f"{sub_indent}{f}")
