# 模組
import openai
import os
import random
import functions.game as game

# 設定 OpenAI API 金鑰
openai.api_key = os.getenv("OPENAI_API_KEY")

# 玩家狀態
p1_lift = True
p2_lift = True
p3_lift = True
p4_lift = True

# 玩家手牌
p1_card, p2_card, p3_card, p4_card = game.draw_card()

# 目標牌
target = game.target_card()

# 玩家數量
number_of_players = game.remaining_player(p1_lift, p2_lift, p3_lift, p4_lift)

# 遊戲階段
while number_of_players > 1:
    # 隨機選擇出牌玩家
    shooting_position = random.randint(1, number_of_players)
    