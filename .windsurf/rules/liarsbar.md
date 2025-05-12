---
trigger: manual
---

1. 使用Python框架開發
2. /functions 裝有函式
3. main.py是核心
4. prompt是給AI的prompt，主要在functions/ai.py中讀取
5. /log是紀錄區，主要會透過functions/record.py讀寫
6. player0是玩家，所以在prompt/player底下不會有0.txt，玩家也不需要對其他機器人玩家紀錄印象。但是AI玩家依然要生成對玩家0的印象