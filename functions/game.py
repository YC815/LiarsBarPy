# 模組
from collections import Counter
import random
import readchar
import os
import subprocess
import sys
import tempfile


def russian_roulette(bullet_position: int, shoooting_position: int):
    """
    俄羅斯轉盤
    Input: 子彈位置(int), 目前彈膛位置(int)
    Output: 中彈與否(bool|True:中彈/False:未中彈), 目前彈膛位置(int)
    """
    if shoooting_position == bullet_position:
        condition = True
    else:
        condition = False
    shoooting_position = shoooting_position % 6 + 1
    return condition, shoooting_position


def draw_cards(num_players=4):
    """
    發牌
    Input: num_players (int): 玩家數量(2~4人)
    Output: Dict[str, List[str]]: 每位玩家的手牌（已排序），例如 {'p1': [...], 'p2': [...], ...}
    """
    if not isinstance(num_players, int) or not (2 <= num_players <= 4):
        raise ValueError("玩家數量必須為 2 到 4 人")

    import random  # 確保 random 被 import

    deck = ["A"] * 6 + ["Q"] * 6 + ["K"] * 6 + ["J"] * 2
    random.shuffle(deck)

    total_needed = num_players * 5
    if total_needed > len(deck):
        raise ValueError("牌堆不足以發牌")

    # 初始化玩家手牌（字典）
    players = {f"p{i}": [] for i in range(num_players)}

    # 發牌
    for i in range(total_needed):
        player_key = f"p{(i % num_players) + 1}"
        players[player_key].append(deck[i])

    # 排序
    for hand in players.values():
        hand.sort()

    return players


def target_card():
    """
    抽取目標牌
    Input: 無
    Output: 目標牌(str)
    """
    return random.choice(["A", "Q", "K"])


def play_card(card_list: list, play_list: str):
    """
    出牌
    Input: 玩家手牌(list), 出牌(list)
    Output: 剩餘手牌(list)
    """
    for i in play_list:
        card_list.remove(play_list[i])
    return card_list


def lier(last_play: list, target: str):
    """
    質疑
    Input: 上一位玩家出牌(list), 目標牌(str)
    Output: 是否說謊(bool|True:質疑成功/False:質疑失敗)
    """
    for i in last_play:
        if last_play[i] != target and last_play[i] != "J":
            return False
    return True


def remaining_player(life: list):
    """
    計算剩餘玩家
    Input: 四位玩家的狀態(bool|True:存活/False:死亡)
    Output: 剩餘玩家數量(int)
    """
    num = 0
    players = life
    for alive in players:
        if alive:
            num += 1
    return num


def choice_card(hand_cards: list):
    """
    選擇卡片
    Input: 玩家手牌(list)
    Output: 玩家剩餘手牌(list), 選擇的卡片(list)
    """
    print(f"請從 {hand_cards} 中選擇 1~3 張卡片（以空格分開）: ")
    selection = input().split()

    if not (1 <= len(selection) <= 3):
        print("張數錯誤，請重新選擇。")
        return choice_card(hand_cards)

    hand_count = Counter(hand_cards)
    select_count = Counter(selection)

    for card, count in select_count.items():
        if hand_count[card] < count:
            print(f"你選了太多張「{card}」，請重新選擇。")
            return choice_card(hand_cards)

    # 移除選擇的牌
    for card in selection:
        hand_cards.remove(card)

    return hand_cards, selection


def liar_or_not():
    """
    判斷是否質疑
    Input: 無
    Output: 是否質疑(bool|True:質疑/False:不質疑)
    """
    while True:
        choice = input("是否質疑？(y/n): ")
        if choice == "y":
            return True
        elif choice == "n":
            return False
        else:
            print("請輸入 y 或 n。")


def question(play_card: list, target: str):
    """
    質疑
    Input: 上一位玩家出牌(list), 目標牌(str)
    Output: 是否質疑成功(bool|True:質疑成功/False:質疑失敗)
    """
    for i in play_card:
        if play_card[i] != target and play_card[i] != "J":
            return False
    return True
