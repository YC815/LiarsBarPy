# 模組
import openai
import os
import random
import functions.game as game
import functions.ai as ai
import functions.record as record
import functions.player as Player
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
# game_count = record.init()

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
    for i in range(game.remaining_player(life)):
        print(f"目標牌為 {target}")
        action = input(
            f"玩家 {i}，請選擇行動（play 出牌 / challenge 質疑）: ").strip().lower()

        if action == "play":
            cards[f"p{i}"], play_card = game.choice_card(cards[f"p{i}"])
            print(f"玩家 {i} 出了 {len(play_card)} 張牌（實際牌面保密）")
            # 可選：紀錄 play_card 給記錄用（不顯示給其他玩家）

        elif action == "challenge":
            question[i] += 1
            last_player_index = Player.last_player(i)
            if game.question(play_card, target):  # 檢查上一位玩家的出牌
                liar[last_player_index] += 1
                print(f"玩家 {i} 質疑成功！")
                got_shoot, bullet[last_player_index] = game.russian_roulette(
                    chamber[last_player_index], bullet[last_player_index])
                if got_shoot:
                    print(f"玩家 {last_player_index} 被擊中！")
                    life[last_player_index] = False
            else:
                print(f"玩家 {i} 質疑失敗！")
                got_shoot, bullet[i] = game.russian_roulette(
                    chamber[i], bullet[i])
                if got_shoot:
                    print(f"玩家 {i} 被擊中！")
                    life[i] = False

        else:
            print("輸入錯誤，請輸入 'play' 或 'challenge'")
