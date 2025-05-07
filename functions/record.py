import os
import json


def init():
    """
    初始化記錄環境
    Input: 無
    Output: 無
    """

    # 讀取當前回合數
    with open("log/info.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    round_count = data["round_count"]  # 保留原始值
    data["round_count"] += 1           # 修改記憶體中的值

    # 寫入更新過的 JSON
    with open("log/info.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    os.makedirs(f"log/round_{round_count}", exist_ok=True)
