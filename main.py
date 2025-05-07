# 模組
import openai
import os
import random
import functions.game as game
import functions.ai as ai
import functions.record as record
# 玩家狀態
p1_lift = True
p2_lift = True
p3_lift = True
p4_lift = True

# 玩家手牌
p1_card, p2_card, p3_card, p4_card = game.draw_cards()

# 目標牌
target = game.target_card()

# 玩家數量
number_of_players = game.remaining_player(p1_lift, p2_lift, p3_lift, p4_lift)

# 俄羅斯轉盤相關
# 子彈位置
p1_bullet = random.randint(0, 5)
p2_bullet = random.randint(0, 5)
p3_bullet = random.randint(0, 5)
p4_bullet = random.randint(0, 5)

# 起始彈膛位置
p1_chamber = 0
p2_chamber = 0
p3_chamber = 0
p4_chamber = 0


# 遊戲階段
shooting_position = random.randint(1, number_of_players)

ai.ai_selection(1, 1, )
