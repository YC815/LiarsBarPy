import os
import json
from string import Template
from typing import Optional, List


def init():
    """
    初始化記錄環境
    Input: 無
    Output: 當前局數(int)
    """

    # 讀取當前局數
    with open("log/game_info.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    data["game_count"] += 1           # 修改記憶體中的值
    game_count = data["game_count"]  # 保留原始值

    # 寫入更新過的 JSON
    with open("log/game_info.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    os.makedirs(f"log/round_{game_count}", exist_ok=True)

    with open(f"log/round_{game_count}/overview.md", "w", encoding="utf-8") as f:
        f.write("")

    with open(f"log/round_{game_count}/player_summary.md", "w", encoding="utf-8") as f:
        f.write("")

    with open(f"log/round_{game_count}/next_round_context.md", "w", encoding="utf-8") as f:
        f.write("")

    with open(f"log/round_{game_count}/game_steps.md", "w", encoding="utf-8") as f:
        f.write("")
        
    with open(f"log/round_{game_count}/ai_round_context.md", "w", encoding="utf-8") as f:
        f.write("")

    return game_count


def log_round_summary(game_count: int, round_count: int, players: list, rivew: dict, shooting_count: list, bullet_position: list, question: list, liar: list, target: str, p0_hand_card: list, p1_hand_card: list, p2_hand_card: list, p3_hand_card: list):
    """
    記錄回合資訊
    Input: 局數(int), 回合數(int), 存活者(list), 回顧訊息(dict), 開槍次數(list), 子彈位置(list), 質疑次數(list), 被質疑次數(list), 目標牌(str), 玩家手牌(list)
    Output: 無
    """
    with open("log/example/round_summary.md", "r", encoding="utf-8") as f:
        example = f.read()
    record = Template(example).substitute({
        "game_count": game_count,
        "round_count": round_count,
        "player_list": players,
        "p0_to_p1": rivew["p0"]["p1"],
        "p0_to_p2": rivew["p0"]["p2"],
        "p0_to_p3": rivew["p0"]["p3"],
        "p1_to_p0": rivew["p1"]["p0"],
        "p1_to_p2": rivew["p1"]["p2"],
        "p1_to_p3": rivew["p1"]["p3"],
        "p2_to_p0": rivew["p2"]["p0"],
        "p2_to_p1": rivew["p2"]["p1"],
        "p2_to_p3": rivew["p2"]["p3"],
        "p3_to_p0": rivew["p3"]["p0"],
        "p3_to_p1": rivew["p3"]["p1"],
        "p3_to_p2": rivew["p3"]["p2"],
        "p0_shoot_count": shooting_count[0],
        "p1_shoot_count": shooting_count[1],
        "p2_shoot_count": shooting_count[2],
        "p3_shoot_count": shooting_count[3],
        "p0_bullet_pos": bullet_position[0],
        "p1_bullet_pos": bullet_position[1],
        "p2_bullet_pos": bullet_position[2],
        "p3_bullet_pos": bullet_position[3],
        "p0_question_count": question[0],
        "p1_question_count": question[1],
        "p2_question_count": question[2],
        "p3_question_count": question[3],
        "p0_liar_count": liar[0],
        "p1_liar_count": liar[1],
        "p2_liar_count": liar[2],
        "p3_liar_count": liar[3],
        "target": target,
        "p0_hand": p0_hand_card,
        "p0_shoot_count": shooting_count[0],
        "p1_hand": p1_hand_card,
        "p1_shoot_count": shooting_count[1],
        "p2_hand": p2_hand_card,
        "p2_shoot_count": shooting_count[2],
        "p3_hand": p3_hand_card,
        "p3_shoot_count": shooting_count[3]
    })
    with open(f"log/round_{game_count}/overview.md", "a", encoding="utf-8") as f:
        f.write("\n")
        f.write(record)


def log_player_action(game_count: int, player_number: int, is_play_card: bool, behavior: str, hand_cards: list, shoot_count: int, play_cards: Optional[List[str]] = None, play_reason: Optional[str] = None, challenge_reason: Optional[str] = None):
    """
    紀錄玩家行動
    Input: 局數(int), 玩家編號(int), 是否出牌(bool), 行為(str), 玩家手牌(list), 開槍次數(int), 出牌(list), 出牌原因(str), 質疑原因(str)
    Output: 無
    """
    if is_play_card == True:  # 出牌
        with open("log/example/player_play_step.md", "r", encoding="utf-8") as f:
            example = f.read()
        record = Template(example).substitute({
            "player_number": player_number,
            "play_cards": play_cards,
            "behavior": behavior,
            "play_reason": play_reason,
            "challenge_reason": challenge_reason or "",
            "hand_cards": hand_cards,
            "shoot_count": shoot_count
        })
    else:  # 質疑
        with open("log/example/player_challenge_step.md", "r", encoding="utf-8") as f:
            example = f.read()
        record = Template(example).substitute({
            "player_number": player_number,
            "behavior": behavior,
            "challenge_reason": challenge_reason,
            "hand_cards": hand_cards,
            "shoot_count": shoot_count
        })
    with open(f"log/round_{game_count}/overview.md", "a", encoding="utf-8") as f:
        f.write("\n")
        f.write(record)


def log_system_verdict(game_count: int, liar_state: bool, player: int, bullet_state: bool):
    """
    系統判決質疑
    Input: 局數(int), 質疑是否成功(bool), 玩家編號(int), 是否中彈(bool)
    Output: 無
    """
    with open("log/example/system_verdict.md", "r", encoding="utf-8") as f:
        example = f.read()
    record = Template(example).substitute({
        "liar_state": liar_state,
        "player": player,
        "bullet_state": bullet_state
    })
    with open(f"log/round_{game_count}/overview.md", "a", encoding="utf-8") as f:
        f.write("\n")
        f.write(record)
    with open(f"log/round_{game_count}/game_steps.md", "a", encoding="utf-8") as f:
        f.write("\n")
        f.write(record)
    with open(f"log/round_{game_count}/ai_round_context.md", "a", encoding="utf-8") as f:
        f.write("\n")
        f.write(record)


def log_game_end_summary(game_count: int, winner: str, player_rounds: list, player_challenge: list, player_challenged: list, player_shoot: list):
    """
    紀錄遊戲結束資訊
    Input: 局數(int), 贏家(str), 玩家回合(list), 玩家質疑(list), 玩家被質疑(list), 玩家開槍(list)
    Output: 無
    """
    with open("log/example/game_end_summary.md", "r", encoding="utf-8") as f:
        example = f.read()
    record = Template(example).substitute({
        "winner": winner,
        "p0_rounds": player_rounds[0],
        "p0_challenge": player_challenge[0],
        "p0_challenged": player_challenged[0],
        "p0_shoot": player_shoot[0],
        "p1_rounds": player_rounds[1],
        "p1_challenge": player_challenge[1],
        "p1_challenged": player_challenged[1],
        "p1_shoot": player_shoot[1],
        "p2_rounds": player_rounds[2],
        "p2_challenge": player_challenge[2],
        "p2_challenged": player_challenged[2],
        "p2_shoot": player_shoot[2],
        "p3_rounds": player_rounds[3],
        "p3_challenge": player_challenge[3],
        "p3_challenged": player_challenged[3],
        "p3_shoot": player_shoot[3]
    })
    with open(f"log/round_{game_count}/overview.md", "a", encoding="utf-8") as f:
        f.write("\n")
        f.write(record)


def log_player_perspective(game_count: int, round_count: int, player: int, shoot_count: int, play_card_count: int, behavior: str):
    """
    無上帝視角record
    Input: 局數(int), 回合數(int), 玩家編號(int), 開槍次數(int), 出牌次數(int), 行為(str)
    Output: 無
    """
    with open("log/example/player_perspective.md", "r", encoding="utf-8") as f:
        example = f.read()
    record = Template(example).substitute({
        "game_count": game_count,
        "round_count": round_count,
        "player": player,
        "shoot_count": shoot_count,
        "play_card_count": play_card_count,
        "behavior": behavior
    })
    with open(f"log/round_{game_count}/player_summary.md", "a", encoding="utf-8") as f:
        f.write("\n")
        f.write(record)





def log_next_round_context(game_count: int, sum_round_count: int, player_list: list, p0_shoot_count: int, p1_shoot_count: int, p2_shoot_count: int, p3_shoot_count: int):
    """
    新回合前AI input
    Input: 局數(int), 回合數(int), 玩家編號(list), 開槍次數(int)
    Output: 無
    """
    with open("log/example/next_round_context_template.md", "r", encoding="utf-8") as f:
        example = f.read()
    with open(f"log/round_{game_count}/game_steps.md", "r", encoding="utf-8") as f:
        game_step = f.read()

    record = Template(example).substitute({
        "game_count": game_count,
        "sum_round_count": sum_round_count,
        "player_list": player_list,
        "p0_shoot_count": p0_shoot_count,
        "p1_shoot_count": p1_shoot_count,
        "p2_shoot_count": p2_shoot_count,
        "p3_shoot_count": p3_shoot_count,
        "game_step": game_step
    })
    with open(f"log/round_{game_count}/next_round_context.md", "a", encoding="utf-8") as f:
        f.write("\n")
        f.write(record)


def log_in_game_action(game_count: int, player_number: int, is_play_card: bool, behavior: str, hand_cards: list, shoot_count: int, play_cards: Optional[List[str]] = None, play_reason: Optional[str] = None, challenge_reason: Optional[str] = None):
    """
    紀錄玩家行動
    Input: 局數(int), 玩家編號(int), 是否出牌(bool), 行為(str), 玩家手牌(list), 開槍次數(int), 出牌(list), 出牌原因(str), 質疑原因(str)
    Output: 無
    """
    # 記錄到 game_steps.md
    if is_play_card == True:  # 出牌
        with open("log/example/in_game_play_step.md", "r", encoding="utf-8") as f:
            example = f.read()
        record = Template(example).substitute({
            "player_number": player_number,
            "play_cards": play_cards,
            "behavior": behavior,
            "play_reason": play_reason or "",
            "challenge_reason": challenge_reason or "",
            "shoot_count": shoot_count
        })
        
        # 同時記錄到 ai_round_context.md
        with open("log/example/round_context_in_game_play_step.md", "r", encoding="utf-8") as f:
            context_example = f.read()
        # 計算出牌數量
        card_count = len(play_cards) if play_cards else 0
        context_record = Template(context_example).substitute({
            "player_number": player_number,
            "card_count": card_count,  # 出牌數量
            "behavior": behavior,
            "challenge_reason": challenge_reason or "",
            "shoot_count": shoot_count
        })
    else:  # 質疑
        with open("log/example/in_game_challenge_step.md", "r", encoding="utf-8") as f:
            example = f.read()
        record = Template(example).substitute({
            "player_number": player_number,
            "behavior": behavior,
            "challenge_reason": challenge_reason or "",
            "shoot_count": shoot_count
        })
        # 質疑時直接使用相同的記錄
        context_record = record
    
    # 寫入 game_steps.md
    with open(f"log/round_{game_count}/game_steps.md", "a", encoding="utf-8") as f:
        f.write("\n")
        f.write(record)
    
    # 寫入 ai_round_context.md
    with open(f"log/round_{game_count}/ai_round_context.md", "a", encoding="utf-8") as f:
        f.write("\n")
        f.write(context_record)
