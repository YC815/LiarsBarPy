from typing import List, Dict, Tuple, Optional
from models.player import Player


class Rules:
    """定義遊戲規則的類別"""

    @staticmethod
    def validate_play_action(player: Player, cards: List[str], target_card: str) -> Tuple[bool, str]:
        """驗證出牌動作是否合法"""
        # 檢查數量
        if not cards:
            return False, "必須指定要出的牌"

        if not (1 <= len(cards) <= 3):
            return False, "出牌數量必須在1到3張之間"

        # 檢查是否是有效的牌
        valid_cards = {"A", "K", "Q", "J"}
        invalid_cards = [card for card in cards if card not in valid_cards]
        if invalid_cards:
            return False, f"無效的牌: {invalid_cards}"

        # 檢查是否擁有這些牌
        if not all(card in player.hand for card in cards):
            return False, "你沒有這些牌"

        return True, ""

    @staticmethod
    def validate_challenge_action(last_player_idx: Optional[int], last_play_cards: List[str]) -> Tuple[bool, str]:
        """驗證質疑動作是否合法"""
        if last_player_idx is None or not last_play_cards:
            return False, "沒有可質疑的上一輪出牌"
        return True, ""

    @staticmethod
    def validate_skip_action(last_play_cards: List[str]) -> Tuple[bool, str]:
        """驗證跳過動作是否合法"""
        if not last_play_cards:
            return False, "沒有可跳過的出牌"
        return True, ""

    @staticmethod
    def validate_shoot_action() -> Tuple[bool, str]:
        """驗證開槍動作是否合法"""
        # 開槍動作通常沒有特別的限制
        return True, ""

    @staticmethod
    def is_game_over(players: List[Player]) -> bool:
        """檢查遊戲是否結束"""
        # 如果只剩一名玩家存活，遊戲結束
        alive_players = [p for p in players if p.alive]
        return len(alive_players) <= 1

    @staticmethod
    def get_winner(players: List[Player]) -> Optional[int]:
        """獲取遊戲勝利者"""
        alive_players = [p for p in players if p.alive]
        if len(alive_players) == 1:
            return alive_players[0].id
        return None
