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
# 遊戲主迴圈
play_card = []  # 上一位玩家的出牌
last_player = None  # 出牌者紀錄

while game.remaining_player(life) > 1:
    print(f"\n========== 第 {round_count} 回合 ==========")

    # 生成本回合的出牌順序（從 player 開始）
    turn_order = [i % 4 for i in range(player, player + 4) if life[i % 4]]

    for i in turn_order:
        print(f"\n目標牌為 {target}")
        action = input(
            f"玩家 {i}，請選擇行動（play 出牌 / challenge 質疑）: ").strip().lower()

        if action == "play":
            cards[f"p{i}"], play_card = game.choice_card(cards[f"p{i}"])
            last_player = i
            print(f"玩家 {i} 出了 {len(play_card)} 張牌（實際牌面保密）")
            continue  # 換下一位玩家

        elif action == "challenge":
            if not play_card:
                print("尚無可質疑的出牌，請等待有人先出牌。")
                continue

            question[i] += 1
            if game.question(play_card, target):
                liar[last_player] += 1
                print(f"玩家 {i} 質疑成功！")
                got_shoot, bullet[last_player] = game.russian_roulette(
                    chamber[last_player], bullet[last_player])
                if got_shoot:
                    print(f"玩家 {last_player} 被擊中並出局！")
                    life[last_player] = False
                    player = last_player  # 下一輪從被開槍者開始
                    break  # 結束本輪
            else:
                print(f"玩家 {i} 質疑失敗！")
                got_shoot, bullet[i] = game.russian_roulette(
                    chamber[i], bullet[i])
                if got_shoot:
                    print(f"玩家 {i} 被擊中並出局！")
                    life[i] = False
                    player = i  # 下一輪從自己開始
                    break  # 結束本輪

        else:
            print("輸入錯誤，請輸入 'play' 或 'challenge'")

    # 更新統計資訊與下一回合
    round_count += 1
    target = game.target_card()  # 每輪換新目標牌
    play_card = []
    last_player = None

# 結束後統計
winner = [i for i, alive in enumerate(life) if alive][0]
print(f"\n🎉 遊戲結束！獲勝者為：玩家 {winner}\n")

print("📊 最終統計資料：")
for i in range(4):
    print(f"\n玩家 {i} 統計：")
    print(f" - 存活狀態：{'存活' if life[i] else '出局'}")
    print(f" - 質疑次數：{question[i]}")
    print(f" - 被質疑成功次數：{liar[i]}")
    print(f" - 子彈位置：{bullet[i]}")
    print(f" - 彈膛位置：{chamber[i]}")
