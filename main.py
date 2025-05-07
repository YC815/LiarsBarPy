# 模組
import openai
import os
import random
import functions.game as game
import functions.ai as ai

# 玩家狀態
p1_lift = True
p2_lift = True
p3_lift = True
p4_lift = True

# 玩家手牌
p1_card, p2_card, p3_card, p4_card = game.draw_cards()

print(f"玩家1手牌: {p1_card}")
print(f"玩家2手牌: {p2_card}")
print(f"玩家3手牌: {p3_card}")
print(f"玩家4手牌: {p4_card}")
# 目標牌
target = game.target_card()

# 玩家數量
number_of_players = game.remaining_player(p1_lift, p2_lift, p3_lift, p4_lift)

# 其他初始化
play_list = []
# 遊戲階段
shooting_position = random.randint(1, number_of_players)

ai.ai_selection(1, 1, )
