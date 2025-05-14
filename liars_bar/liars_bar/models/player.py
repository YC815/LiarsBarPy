# liars_bar/models/player.py
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class PlayerType(Enum):
    HUMAN = "human"
    AI = "ai"


@dataclass
class Player:
    """
    統一的玩家類別，整合了之前 functions/player.py 和 game/models/player.py 的功能
    """
    id: int
    player_type: PlayerType = PlayerType.AI
    hand: List[str] = field(default_factory=list)
    alive: bool = True
    bullet_pos: int = None
    gun_pos: int = 1
    shots_fired: int = 0
    challenge_success: int = 0
    challenge_fail: int = 0
    survival_rounds: int = 0

    # 新增玩家行為統計和策略相關屬性
    play_history: List[Dict] = field(default_factory=list)
    opinions: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        import random
        if self.bullet_pos is None:
            self.bullet_pos = random.randint(1, 6)
        if not self.opinions:
            # 初始化對其他玩家的評價
            self.opinions = {
                f"p{i}": "還不了解此名玩家。" for i in range(4) if i != self.id}

    def shoot(self) -> bool:
        """進行俄羅斯輪盤，返回是否中彈"""
        is_hit = self.bullet_pos == self.gun_pos
        self.gun_pos = (self.gun_pos % 6) + 1
        self.shots_fired += 1
        if is_hit:
            self.alive = False
        return is_hit

    def play_cards(self, cards: List[str]) -> bool:
        """出牌，成功返回 True"""
        if not all(card in self.hand for card in cards):
            return False
        for card in cards:
            self.hand.remove(card)
        return True

    def record_action(self, action_type: str, cards=None, success=None):
        """記錄玩家動作"""
        self.play_history.append({
            "type": action_type,
            "cards": cards or [],
            "success": success
        })
