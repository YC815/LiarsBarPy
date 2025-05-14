from dataclasses import dataclass
from typing import List, Dict, Optional
import os
import json
from datetime import datetime


@dataclass
class RoundRecord:
    """回合記錄數據類別"""
    round_number: int
    target_card: str
    timestamp: str
    actions: List[Dict]
    shots_fired: Dict[int, int]  # 玩家ID -> 開槍次數


@dataclass
class PlayerRecord:
    """玩家記錄數據類別"""
    player_id: int
    cards_played: List[str]
    behavior: str
    strategy: str
    shots_fired: int
    hand: List[str]
    bullet_pos: Optional[int] = None


class RecordManager:
    """遊戲記錄管理器"""

    def __init__(self, game_id: int, session_id: str):
        self.game_id = game_id
        self.session_id = session_id
        self.log_directory_path = f"log/game_{self.game_id}_{self.session_id}"
        self.current_round = 1
        self.round_records: List[RoundRecord] = []
        self.target_card = ""

        # 建立記錄目錄
        self._create_directories()
        self._init_record_files()

    def _create_directories(self):
        """建立記錄目錄"""
        os.makedirs(self.log_directory_path, exist_ok=True)

    def _init_record_files(self):
        """初始化記錄文件"""
        # 回合內記錄
        with open(os.path.join(self.log_directory_path, "round_records.md"), "w", encoding="utf-8") as f:
            f.write("# 回合內記錄\n\n")

        # 玩家視角記錄
        with open(os.path.join(self.log_directory_path, "player_perspective.md"), "w", encoding="utf-8") as f:
            f.write("# 玩家視角記錄\n\n")

        # 上帝視角記錄
        with open(os.path.join(self.log_directory_path, "god_perspective.md"), "w", encoding="utf-8") as f:
            f.write("# 上帝視角記錄\n\n")

    def get_log_directory_path(self) -> str:
        """返回當前遊戲記錄的完整目錄路徑"""
        return self.log_directory_path

    def get_round_context(self, round_number: Optional[int] = None) -> str:
        """獲取指定回合的上下文記錄，用於 AI 決策參考

        Args:
            round_number: 回合編號，如果為 None 則返回當前回合的記錄

        Returns:
            str: 格式化的回合記錄文本
        """
        if not self.round_records:
            return ""

        # 如果沒有指定回合編號，使用當前回合
        if round_number is None:
            round_number = self.current_round

        # 找到指定回合的記錄
        round_record = None
        for record in self.round_records:
            if record.round_number == round_number:
                round_record = record
                break

        if not round_record:
            return ""

        # 構建回合記錄文本
        context = [
            f"# 回合 {round_record.round_number} 記錄",
            f"目標牌: {round_record.target_card}",
            f"時間: {round_record.timestamp}",
            "\n## 玩家動作記錄"
        ]

        # 添加每個玩家的動作記錄
        for action in round_record.actions:
            context.extend([
                f"\n### 玩家 {action['player_id']}",
                f"- 動作類型: {action['action_type']}",
                f"- 出牌: {action['cards_played']}",
                f"- 開槍次數: {action['shots_fired']}",
                f"- 表現: {action['behavior']}"
            ])

            # 如果是質疑動作，添加質疑結果
            if action['action_type'] == 'challenge':
                context.append(f"- 質疑原因: {action['strategy']}")

        # 添加回合總結
        context.extend([
            "\n## 回合總結",
            f"- 總開槍次數: {sum(round_record.shots_fired.values())}",
            "- 玩家開槍次數統計:"
        ])

        for player_id, shots in round_record.shots_fired.items():
            context.append(f"  - 玩家 {player_id}: {shots} 次")

        return "\n".join(context)

    def log_action(self,
                   player_id: int,
                   action_type: str,
                   cards_played: List[str],
                   cards_remaining: List[str],
                   shots_fired: int,
                   behavior: str,
                   strategy: Optional[str] = None,
                   bullet_pos: Optional[int] = None):
        """記錄玩家動作"""
        # 創建玩家記錄
        player_record = PlayerRecord(
            player_id=player_id,
            cards_played=cards_played,
            behavior=behavior,
            strategy=strategy or "",
            shots_fired=shots_fired,
            hand=cards_remaining,
            bullet_pos=bullet_pos
        )

        # 如果是新回合，創建新的回合記錄
        if not self.round_records or self.round_records[-1].round_number != self.current_round:
            self.round_records.append(RoundRecord(
                round_number=self.current_round,
                target_card=self.target_card,
                timestamp=datetime.now().isoformat(),
                actions=[],
                shots_fired={}
            ))

        # 更新當前回合記錄
        current_round = self.round_records[-1]
        current_round.actions.append({
            "player_id": player_id,
            "action_type": action_type,
            "cards_played": cards_played,
            "cards_remaining": cards_remaining,
            "shots_fired": shots_fired,
            "behavior": behavior,
            "strategy": strategy,
            "bullet_pos": bullet_pos
        })
        current_round.shots_fired[player_id] = shots_fired

        # 寫入所有視角的記錄
        self._write_all_records()

    def update_target_card(self, target_card: str):
        """更新目標牌"""
        self.target_card = target_card
        if self.round_records:
            self.round_records[-1].target_card = target_card
            self._write_all_records()

    def next_round(self):
        """進入下一回合"""
        self.current_round += 1
        self._write_all_records()

    def _write_all_records(self):
        """寫入所有視角的記錄"""
        self._write_round_records()
        self._write_player_perspective()
        self._write_god_perspective()

    def _write_round_records(self):
        """寫入回合內記錄"""
        if not self.round_records:
            return

        current_round = self.round_records[-1]
        content = [
            f"\n## 回合 {current_round.round_number}",
            f"目標牌: {current_round.target_card}",
            f"時間: {current_round.timestamp}",
            "\n### 玩家動作"
        ]

        for action in current_round.actions:
            content.extend([
                f"\n#### 玩家 {action['player_id']}",
                f"- 動作: {action['action_type']}",
                f"- 出牌: {action['cards_played']}",
                f"- 開槍次數: {action['shots_fired']}",
                f"- 表現: {action['behavior']}"
            ])

        with open(os.path.join(self.log_directory_path, "round_records.md"), "a", encoding="utf-8") as f:
            f.write("\n".join(content))

    def _write_player_perspective(self):
        """寫入玩家視角記錄"""
        if not self.round_records:
            return

        current_round = self.round_records[-1]
        content = [
            f"\n## 回合 {current_round.round_number}",
            f"目標牌: {current_round.target_card}",
            f"時間: {current_round.timestamp}",
            "\n### 玩家動作"
        ]

        for action in current_round.actions:
            content.extend([
                f"\n#### 玩家 {action['player_id']}",
                f"- 動作: {action['action_type']}",
                f"- 出牌: {action['cards_played']}",
                f"- 剩餘手牌: {action['cards_remaining']}",
                f"- 開槍次數: {action['shots_fired']}",
                f"- 表現: {action['behavior']}",
                f"- 策略: {action['strategy']}"
            ])

        with open(os.path.join(self.log_directory_path, "player_perspective.md"), "a", encoding="utf-8") as f:
            f.write("\n".join(content))

    def _write_god_perspective(self):
        """寫入上帝視角記錄"""
        if not self.round_records:
            return

        current_round = self.round_records[-1]
        content = [
            f"\n## 回合 {current_round.round_number}",
            f"目標牌: {current_round.target_card}",
            f"時間: {current_round.timestamp}",
            "\n### 玩家動作"
        ]

        for action in current_round.actions:
            content.extend([
                f"\n#### 玩家 {action['player_id']}",
                f"- 動作: {action['action_type']}",
                f"- 出牌: {action['cards_played']}",
                f"- 剩餘手牌: {action['cards_remaining']}",
                f"- 開槍次數: {action['shots_fired']}",
                f"- 表現: {action['behavior']}",
                f"- 策略: {action['strategy']}",
                f"- 子彈位置: {action['bullet_pos'] or '未知'}"
            ])

        with open(os.path.join(self.log_directory_path, "god_perspective.md"), "a", encoding="utf-8") as f:
            f.write("\n".join(content))
