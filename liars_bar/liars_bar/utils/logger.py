# liars_bar/utils/logger.py
import os
import datetime
from typing import List, Dict, Any


class GameLogger:
    """遊戲日誌記錄器"""

    def __init__(self, log_dir="log"):
        self.log_dir = log_dir
        self.current_game_id = None
        self.round_count = 0

        # 確保日誌目錄存在
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

    def log_game_start(self, game_id: int, target_card: str, players: List[Any]) -> None:
        """記錄遊戲開始"""
        self.current_game_id = game_id
        self.round_count = 1

        # 創建遊戲日誌目錄
        game_dir = os.path.join(self.log_dir, f"game_{game_id}")
        if not os.path.exists(game_dir):
            os.makedirs(game_dir)

        # 記錄遊戲初始狀態
        with open(os.path.join(game_dir, "game_info.md"), "w", encoding="utf-8") as f:
            f.write(f"# 遊戲 {game_id} 資訊\n\n")
            f.write(
                f"開始時間: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"目標牌: {target_card}\n\n")
            f.write("## 玩家初始狀態\n\n")

            for player in players:
                f.write(f"### 玩家 {player.id}\n")
                f.write(f"- 手牌: {player.hand}\n")
                f.write(f"- 子彈位置: {player.bullet_pos}\n")
                f.write(f"- 槍管位置: {player.gun_pos}\n\n")

        # 創建回合記錄文件
        with open(os.path.join(game_dir, "rounds.md"), "w", encoding="utf-8") as f:
            f.write(f"# 遊戲 {game_id} 回合記錄\n\n")

        # 創建 AI 決策記錄文件
        with open(os.path.join(game_dir, "ai_decisions.md"), "w", encoding="utf-8") as f:
            f.write(f"# 遊戲 {game_id} AI 決策記錄\n\n")

    def log_action(self, player_id: int, action_type: str, cards=None, **kwargs) -> None:
        """記錄玩家動作"""
        if self.current_game_id is None:
            return

        game_dir = os.path.join(self.log_dir, f"game_{self.current_game_id}")

        # 獲取額外參數
        behavior = kwargs.get("behavior", "")
        play_reason = kwargs.get("play_reason", "")
        challenge_reason = kwargs.get("challenge_reason", "")
        result = kwargs.get("result", "")

        # 格式化動作描述
        action_desc = f"## 回合 {self.round_count} - 玩家 {player_id} 的動作\n\n"
        action_desc += f"- 動作類型: {action_type}\n"

        if action_type == "play" and cards:
            action_desc += f"- 出牌: {cards}\n"

        if behavior:
            action_desc += f"- 表現: {behavior}\n"

        if play_reason and action_type == "play":
            action_desc += f"- 出牌原因: {play_reason}\n"

        if challenge_reason and action_type == "challenge":
            action_desc += f"- 質疑原因: {challenge_reason}\n"

        if result:
            action_desc += f"- 結果: {result}\n"

        action_desc += f"\n時間: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        # 添加到回合記錄
        with open(os.path.join(game_dir, "rounds.md"), "a", encoding="utf-8") as f:
            f.write(action_desc)

    def next_round(self) -> None:
        """進入下一回合"""
        self.round_count += 1

    def log_game_reset(self, target_card: str, alive_players: List[int]) -> None:
        """記錄遊戲重置"""
        if self.current_game_id is None:
            return

        game_dir = os.path.join(self.log_dir, f"game_{self.current_game_id}")

        with open(os.path.join(game_dir, "rounds.md"), "a", encoding="utf-8") as f:
            f.write(f"## 遊戲重置\n\n")
            f.write(f"- 新目標牌: {target_card}\n")
            f.write(f"- 存活玩家: {alive_players}\n\n")

    def log_game_end(self, winner_id: int, statistics: Dict) -> None:
        """記錄遊戲結束"""
        if self.current_game_id is None:
            return

        game_dir = os.path.join(self.log_dir, f"game_{self.current_game_id}")

        with open(os.path.join(game_dir, "game_result.md"), "w", encoding="utf-8") as f:
            f.write(f"# 遊戲 {self.current_game_id} 結果\n\n")
            f.write(
                f"結束時間: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"獲勝者: 玩家 {winner_id}\n\n")
            f.write("## 玩家統計\n\n")

            for player_id, stats in statistics.items():
                f.write(f"### 玩家 {player_id}\n")
                f.write(f"- 存活回合數: {stats['survival_rounds']}\n")
                f.write(f"- 成功質疑次數: {stats['challenge_success']}\n")
                f.write(f"- 失敗質疑次數: {stats['challenge_fail']}\n")
                f.write(f"- 開槍次數: {stats['shots_fired']}\n\n")

    def log_ai_thinking(self, player_id: int, reasoning: str) -> None:
        """記錄 AI 思考過程"""
        if self.current_game_id is None:
            return

        game_dir = os.path.join(self.log_dir, f"game_{self.current_game_id}")

        with open(os.path.join(game_dir, "ai_decisions.md"), "a", encoding="utf-8") as f:
            f.write(f"## 回合 {self.round_count} - 玩家 {player_id} 的思考\n\n")
            f.write(f"{reasoning}\n\n")
            f.write(
                f"時間: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

    def log_error(self, error_message: str) -> None:
        """記錄錯誤信息"""
        if self.current_game_id is None:
            return

        game_dir = os.path.join(self.log_dir, f"game_{self.current_game_id}")

        with open(os.path.join(game_dir, "errors.log"), "a", encoding="utf-8") as f:
            f.write(
                f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {error_message}\n")
