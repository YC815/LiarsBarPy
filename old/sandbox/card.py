import random

# 建立牌堆
cards = ["A"] * 6 + ["Q"] * 6 + ["K"] * 6 + ["J"] * 2

# 洗牌
random.shuffle(cards)

# 四位玩家的容器
p1, p2, p3, p4 = [], [], [], []

# 集合成列表供迴圈使用
players = [p1, p2, p3, p4]

# 發牌（使用 enumerate）
for index, card in enumerate(cards):
    players[index % 4].append(card)

# 抽取目標牌
target = random.choice(["A", "Q", "K"])

# 整理玩家手牌
for i in range(4):
    players[i].sort()

# 輸出
print("Target:", target)
print("Player1:", p1)
print("Player2:", p2)
print("Player3:", p3)
print("Player4:", p4)
