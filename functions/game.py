# 模組
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
    Output: List[List[str]]: 每位玩家的手牌（已排序）
    """
    if not isinstance(num_players, int) or not (2 <= num_players <= 4):
        raise ValueError("玩家數量必須為 2 到 4 人")

    # 建立牌堆並洗牌
    deck = ["A"] * 6 + ["Q"] * 6 + ["K"] * 6 + ["J"] * 2
    random.shuffle(deck)

    # 確認牌夠抽（理論上最多4人 × 5張 = 20張）
    total_needed = num_players * 5
    if total_needed > len(deck):
        raise ValueError("牌堆不足以發牌")

    # 發牌（每人5張）
    players = [[] for _ in range(num_players)]
    for i in range(total_needed):
        players[i % num_players].append(deck[i])

    # 排序手牌
    for hand in players:
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


def remaining_player(p1, p2, p3, p4):
    """
    計算剩餘玩家
    Input: 四位玩家的狀態(bool|True:存活/False:死亡)
    Output: 剩餘玩家數量(int)
    """
    num = 0
    players = [p1, p2, p3, p4]
    for alive in players:
        if alive:
            num += 1
    return num

