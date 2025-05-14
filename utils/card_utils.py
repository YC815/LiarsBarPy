# liars_bar/utils/card_utils.py
from typing import List, Dict, Tuple
import random


def create_deck() -> List[str]:
    """創建一副牌"""
    deck = []
    # 每種牌各 6 張
    for card_type in ["A", "K", "Q"]:
        deck.extend([card_type] * 6)
    # Joker 2 張
    deck.extend(["J"] * 2)
    return deck


def shuffle_and_deal(deck: List[str], num_players: int) -> Dict[str, List[str]]:
    """洗牌並發牌"""
    if not (2 <= num_players <= 4):
        raise ValueError("玩家數量必須在2到4之間")

    # 洗牌
    shuffled_deck = deck.copy()
    random.shuffle(shuffled_deck)

    # 計算每位玩家應得的牌數
    cards_per_player = len(shuffled_deck) // num_players

    # 發牌
    hands = {}
    for i in range(num_players):
        start_idx = i * cards_per_player
        end_idx = start_idx + cards_per_player
        hand = shuffled_deck[start_idx:end_idx]
        hand.sort()  # 排序手牌
        hands[f"p{i}"] = hand

    return hands


def validate_played_cards(played_cards: List[str], hand: List[str]) -> Tuple[bool, str]:
    """驗證出牌是否合法"""
    # 檢查數量
    if not (1 <= len(played_cards) <= 3):
        return False, "出牌數量必須在1到3張之間"

    # 檢查是否是有效的牌
    valid_cards = {"A", "K", "Q", "J"}
    invalid_cards = [card for card in played_cards if card not in valid_cards]
    if invalid_cards:
        return False, f"無效的牌: {invalid_cards}"

    # 檢查是否擁有這些牌
    if not all(card in hand for card in played_cards):
        return False, "你沒有這些牌"

    return True, ""
