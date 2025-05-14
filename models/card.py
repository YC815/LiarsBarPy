from enum import Enum
from typing import List, Optional


class CardType(Enum):
    ACE = "A"
    KING = "K"
    QUEEN = "Q"
    JOKER = "J"


class Card:
    """卡牌類別"""

    def __init__(self, card_type: str):
        if card_type not in [t.value for t in CardType]:
            raise ValueError(f"無效的卡牌類型: {card_type}")

        self.card_type = card_type

    def __str__(self) -> str:
        return self.card_type

    def __repr__(self) -> str:
        return f"Card({self.card_type})"

    def __eq__(self, other) -> bool:
        if isinstance(other, Card):
            return self.card_type == other.card_type
        elif isinstance(other, str):
            return self.card_type == other
        return False


class Deck:
    """牌組類別"""

    def __init__(self):
        self.cards = []

    def initialize(self):
        """初始化一副標準的說謊者酒吧牌組"""
        self.cards = []
        # 每種牌各 6 張
        for card_type in [CardType.ACE.value, CardType.KING.value, CardType.QUEEN.value]:
            self.cards.extend([Card(card_type) for _ in range(6)])
        # Joker 2 張
        self.cards.extend([Card(CardType.JOKER.value) for _ in range(2)])

    def shuffle(self):
        """洗牌"""
        import random
        random.shuffle(self.cards)

    def deal(self, num_players: int) -> dict:
        """發牌"""
        if not (2 <= num_players <= 4):
            raise ValueError("玩家數量必須在2到4之間")

        cards_per_player = len(self.cards) // num_players
        hands = {}

        for i in range(num_players):
            start_idx = i * cards_per_player
            end_idx = start_idx + cards_per_player
            hands[f"p{i}"] = self.cards[start_idx:end_idx]

        return hands
