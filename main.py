# 模組
import openai
import os
import random
import functions.game as game
import functions.ai as ai
import functions.record as record

# 初始化玩家狀態
life = [True, True, True, True]

# 初始化出牌堆
play_cards = []
# 初始化玩家手牌
cards = game.draw_cards(4)

# 初始化目標牌
target = game.target_card()

# 初始化玩家數量
number_of_players = game.remaining_player(life)

# 初始化俄羅斯轉盤子彈位置
bullet = [random.randint(0, 5), random.randint(
    0, 5), random.randint(0, 5), random.randint(0, 5)]

# 初始化俄羅斯轉盤起始彈膛位置
chamber = [0, 0, 0, 0]


# 初始化遊戲紀錄
game_count = record.init()

# 初始化回合數
round_count = 1

# 初始化玩家列表
player_list = [f"player{idx}" for idx,
               life in enumerate(life) if life]

# 初始化玩家印象
rivew = {
    "p0": {
        "p1": "還不了解此名玩家。",
        "p2": "還不了解此名玩家。",
        "p3": "還不了解此名玩家。"
    },
    "p1": {
        "p0": "還不了解此名玩家。",
        "p2": "還不了解此名玩家。",
        "p3": "還不了解此名玩家。"
    },
    "p2": {
        "p0": "還不了解此名玩家。",
        "p1": "還不了解此名玩家。",
        "p3": "還不了解此名玩家。"
    },
    "p3": {
        "p0": "還不了解此名玩家。",
        "p1": "還不了解此名玩家。",
        "p2": "還不了解此名玩家。"
    }}

# 初始化質疑/被質疑計數
question = [0, 0, 0, 0]
liar = [0, 0, 0, 0]

# 決定誰開始
player = random.randint(0, 3)
while number_of_players > 1:  # 重複直到玩家剩一人
    # 紀錄回合資訊
    record.record_round_info(game_count, round_count,
                             player_list, rivew, chamber, bullet, question, liar, target, cards["p0"], cards["p1"], cards["p2"], cards["p3"])
    for i in range(game.remaining_player(life) - 1):
        cards[f"p{i}"], play_card = game.choice_card(cards[f"p{i}"])
        liar_or_not = game.liar_or_not()
        if liar_or_not:
            question[i] += 1
            if game.question(cards[f"p{i}"], target):
                liar[i] += 1
                print(f"玩家 {i} 質疑成功！")
                # 玩家質疑成功，將對方手牌移除
                cards[f"p{i}"] = []
            else:
                print(f"玩家 {i} 質疑失敗！")
                # 玩家質疑失敗，將對方手牌移除
                cards[f"p{i}"] = []
        else:
            play_cards.append(play_card)
            chamber[i] = (chamber[i] + 1) % 6
            bullet[i] = (bullet[i] + 1) % 6
