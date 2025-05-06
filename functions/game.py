# 模組
import random



def russian_roulette(bullet_position:int, shoooting_position:int):
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


def draw_card():
    """
    抽卡
    Input: 無
    Output: 四位玩家的手牌(list)
    """
    cards = ["A"] * 6 + ["Q"] * 6 + ["K"] * 6 + ["J"] * 2
    random.shuffle(cards)
    p1, p2, p3, p4 = [], [], [], []
    players = [p1, p2, p3, p4]
    for index, card in enumerate(cards):
        players[index % 4].append(card)
    for i in range(4):
        players[i].sort()
    return players

def target_card():
    """
    抽取目標牌
    Input: 無
    Output: 目標牌(str)
    """
    target = random.choice(["A", "Q", "K"])
    return target


def play_card(card_list:list, play_list:str):
    """
    出牌
    Input: 玩家手牌(list), 出牌(list)
    Output: 剩餘手牌(list)
    """
    for i in play_card:
        card_list.remove(play_list[i])
    return card_list


def lier(last_play:list, target:str):
    """
    質疑
    Input: 上一位玩家出牌(list), 目標牌(str)
    Output: 是否說謊(bool|True:質疑成功/False:質疑失敗)
    """
    for i in last_play:
        if last_play[i] != target or last_play[i] != "J":
            return False
            break
    return True


def remaining_player(p1, p2, p3, p4):
    """
    計算剩餘玩家
    Input: 四位玩家的狀態(bool|True:存活/False:死亡)
    Output: 剩餘玩家數量(int)
    """
    num = 0
    players = [p1, p2, p3, p4]
    for i in players:
        if players[i] == True:
            num += 1
    return num

