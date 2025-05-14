# main.py
from liars_bar.core.game import Game
import argparse
import os
import sys

# 添加當前目錄到 Python 路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 從相對路徑導入


def main():
    """主程序入口"""
    parser = argparse.ArgumentParser(description="說謊者酒吧遊戲")
    parser.add_argument("--num_players", type=int,
                        default=4, help="玩家數量 (2-4)")
    parser.add_argument("--human_player", type=int,
                        default=0, help="人類玩家編號 (0-3)")
    parser.add_argument("--debug", action="store_true", help="啟用調試模式")
    parser.add_argument("--ai_strategy", type=str,
                        default="llm", help="AI策略類型 (random/rule/llm/learning)")
    args = parser.parse_args()

    # 創建並運行遊戲
    game = Game(
        num_players=args.num_players,
        debug=args.debug,
        human_player_index=args.human_player,
        ai_strategy=args.ai_strategy
    )
    game.run()


if __name__ == "__main__":
    main()
