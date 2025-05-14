import random
from typing import List, Dict, Tuple
import datetime
from collections import Counter


def create_deck() -> List[str]:
    """創建完整的牌組"""
    return ["Q"] * 6 + ["K"] * 6 + ["A"] * 6 + ["J"] * 2


def shuffle_and_deal(deck: List[str], num_players: int) -> Dict[str, List[str]]:
    """洗牌並發牌"""
    random.shuffle(deck)
    hands = {}
    for i in range(num_players):
        hands[f"p{i}"] = sorted(deck[i*5:(i+1)*5])
    return hands


def validate_played_cards(cards: List[str], hand: List[str]) -> Tuple[bool, str]:
    """驗證出牌是否合法"""
    # 1. 檢查出牌數量
    if not (1 <= len(cards) <= 3):
        return False, "出牌數量必須在 1-3 張之間"

    # 2. 檢查是否為合法牌型
    valid_cards = {"A", "K", "Q", "J"}
    if not all(card in valid_cards for card in cards):
        return False, f"出現不合法的牌型: {[card for card in cards if card not in valid_cards]}"

    # 3. 檢查手牌中是否有足夠的牌
    hand_counter = Counter(hand)
    play_counter = Counter(cards)

    for card, count in play_counter.items():
        if hand_counter[card] < count:
            return False, f"超出手牌數量: 嘗試出 {count} 張 {card}，但手牌中只有 {hand_counter[card]} 張"

    return True, ""


def format_game_status(round_count: int, target_card: str, players: List) -> str:
    """格式化遊戲狀態顯示"""
    alive_players = [p.id for p in players if p.alive]
    status = [
        f"\n----- 回合 {round_count} -----",
        f"目標牌: {target_card}",
        f"存活玩家: {alive_players} (共 {len(alive_players)} 名)"
    ]

    for p in players:
        status_text = "存活" if p.alive else "出局"
        hand_info = f"手牌數: {len(p.hand)}" if p.alive else ""
        gun_info = f"槍管位置: {p.gun_pos}/6" if p.alive else ""
        status.append(
            f"p{p.id}: {status_text} | {hand_info} | {gun_info} | 開槍次數: {p.shots_fired}")

    return "\n".join(status)


def format_game_statistics(players: List) -> str:
    """格式化遊戲統計資訊"""
    stats = ["\n===== 遊戲統計 ====="]
    for p in players:
        status = "存活" if p.alive else "出局"
        stats.extend([
            f"玩家 p{p.id}: {status}",
            f"  存活回合: {p.survival_rounds}",
            f"  質疑成功/失敗: {p.challenge_success}/{p.challenge_fail}",
            f"  開槍次數: {p.shots_fired}"
        ])
    return "\n".join(stats)
