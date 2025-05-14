#!/usr/bin/env python3
# run_game.py - 運行遊戲的主腳本
from liars_bar.core.game import Game
import os
import sys
import argparse

# 添加項目根目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 從 liars_bar 模組導入


def main():
    """主程序入口"""
    parser = argparse.ArgumentParser(description="說謊者酒吧遊戲")
    parser.add_argument("--num_players", type=int,
                        default=4, help="玩家數量 (2-4)")
    parser.add_argument("--human_player", type=int,
                        default=0, help="人類玩家編號 (0-3)")
    parser.add_argument("--ai_strategy", type=str,
                        default="rule", help="AI策略 (random, rule, llm, learning)")
    parser.add_argument("--debug", action="store_true", help="啟用調試模式")
    args = parser.parse_args()

    # 確保日誌目錄存在
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "log")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 打印遊戲信息
    print("\n===== 說謊者酒吧遊戲 =====")
    print(f"玩家數量: {args.num_players}")
    print(f"人類玩家: 玩家{args.human_player}")
    print(f"AI策略: {args.ai_strategy}")
    print(f"調試模式: {'開啟' if args.debug else '關閉'}\n")

    # 創建並運行遊戲
    try:
        game = Game(
            num_players=args.num_players,
            debug=args.debug,
            human_player_index=args.human_player,
            ai_strategy=args.ai_strategy
        )
        game.run()
    except KeyboardInterrupt:
        print("\n遊戲被用戶中斷")
    except Exception as e:
        print(f"\n遊戲發生錯誤: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
