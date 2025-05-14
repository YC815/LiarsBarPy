from dataclasses import dataclass
from typing import List
import random


@dataclass
class Player:
    """玩家類別，用於管理玩家狀態"""
    id: int                 # 玩家編號 (0-3)
    hand: List[str] = None  # 手牌列表
    alive: bool = True      # 存活狀態
    bullet_pos: int = None  # 子彈位置 (1-6)
    gun_pos: int = 1        # 目前槍管位置 (1-6)
    shots_fired: int = 0    # 開槍次數
    challenge_success: int = 0   # 成功質疑次數
    challenge_fail: int = 0      # 失敗質疑次數
    survival_rounds: int = 0     # 存活回合數

    def __post_init__(self):
        if self.hand is None:
            self.hand = []
        if self.bullet_pos is None:
            self.bullet_pos = random.randint(1, 6)
