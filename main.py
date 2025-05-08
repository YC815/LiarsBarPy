import os
import random
import json
from openai import OpenAI
import functions.game as game
import functions.record as record
import functions.player as Player
from functions.ai import ai_selection

# 假設 player0 是人類，1~3 為 AI
HUMAN_IDX = 0

# 輔助：將歷史紀錄格式化成字串，供 AI 讀取
format_history = getattr(record, 'format_history', lambda: "")


def main():
    # 初始化遊戲與記錄環境
    game_count = record.init()

    life = [True, True, True, True]
    question = [0, 0, 0, 0]
    liar = [0, 0, 0, 0]
    play_card = []
    last_player = None
    round_count = 1
    player = random.randint(0, 3)

    bullet = [random.randint(0, 5) for _ in range(4)]
    chamber = [0, 0, 0, 0]
    shots_fired = [0, 0, 0, 0]

    review = {
        "p0": {"p1": "還不了解此名玩家。", "p2": "還不了解此名玩家。", "p3": "還不了解此名玩家。"},
        "p1": {"p0": "還不了解此名玩家。", "p2": "還不了解此名玩家。", "p3": "還不了解此名玩家。"},
        "p2": {"p0": "還不了解此名玩家。", "p1": "還不了解此名玩家。", "p3": "還不了解此名玩家。"},
        "p3": {"p0": "還不了解此名玩家。", "p1": "還不了解此名玩家。", "p2": "還不了解此名玩家。"}
    }

    target = game.target_card()
    cards = game.draw_cards(4)
    first_round = True

    while game.remaining_player(life) > 1:
        # 記錄回合前資訊
        players_alive = [f"p{i}" for i, alive in enumerate(life) if alive]
        record.record_round_info(
            game_count, round_count, players_alive,
            review, shots_fired, bullet,
            question, liar, target,
            cards.get('p0', []), cards.get('p1', []), cards.get(
                'p2', []), cards.get('p3', [])
        )

        print(f"\n========== 第 {round_count} 回合 ==========\n")
        gun_fired = False
        turn_order = [i for i in range(
            player, player + 4) if life[i % 4] for i in [i % 4]]

        for i in turn_order:
            print(f"目標牌為 {target}，玩家 {i} 的手牌為 {cards[f'p{i}']}")

            # 若只剩你有牌，自動變質疑
            non_empty = [j for j in range(4) if cards.get(f'p{j}', [])]
            if len(non_empty) == 1 and non_empty[0] == i:
                print(f"只剩玩家 {i} 有牌，自動質疑。")
                action = 'challenge'
                behavior = ''
                play_reason = ''
                challenge_reason = '僅剩唯一手牌，改為質疑。'
            else:
                # 正常決策
                if i == HUMAN_IDX:
                    action = input(
                        f"玩家 {i}，請選擇行動（play / challenge）: ").strip().lower()
                    behavior = ''
                    play_reason = ''
                    challenge_reason = ''
                else:
                    decision = ai_selection(
                        player_number=i,
                        round_count=round_count,
                        play_history=format_history(),
                        self_hand=cards[f'p{i}'],
                        opinions_on_others=json.dumps(review[f'p{i}']),
                        number_of_shots_fired=shots_fired[i]
                    )
                    action = decision.action
                    behavior = decision.behavior
                    play_reason = getattr(decision, 'play_reason', '')
                    challenge_reason = getattr(
                        decision, 'challenge_reason', '')

                    if action == 'play':
                        played = decision.played_cards
                        for c in played:
                            cards[f'p{i}'].remove(c)
                        play_card = played
                        last_player = i
                        print(f"玩家 {i} (AI) 出牌：{played}")
                    else:
                        print(f"玩家 {i} (AI) 決定質疑。")

            # 出牌
            if action == 'play':
                if i == HUMAN_IDX:
                    cards[f'p{i}'], play_card = game.choice_card(
                        cards[f'p{i}'])
                    last_player = i
                    print(f"玩家 {i} 出了 {len(play_card)} 張牌（保密）")
                record.record_game_play_step(
                    game_count, i, True, behavior,
                    cards[f'p{i}'], shots_fired[i],
                    play_cards=play_card, play_reason=play_reason, challenge_reason=challenge_reason
                )
                continue

            # 質疑
            if action == 'challenge':
                if not play_card:
                    print("尚無可質疑的出牌。")
                    if i == HUMAN_IDX:
                        continue
                    else:
                        break

                question[i] += 1
                result = game.question(play_card, target)

                # 質疑成功：被質疑者開槍
                if result:
                    shooter = last_player
                    got_shoot, new_bullet = game.russian_roulette(
                        chamber[shooter], bullet[shooter]
                    )
                    bullet[shooter] = new_bullet
                    shots_fired[shooter] += 1
                    record.system_record(game_count, True, shooter, got_shoot)
                    print(f"玩家 {shooter} 被質疑成功並開槍 ({shots_fired[shooter]}/6)")
                    if got_shoot:
                        life[shooter] = False
                        player = shooter
                else:
                    # 質疑失敗：直接下一輪
                    print("質疑失敗，本回合結束，進入下一回合。")
                    record.system_record(game_count, False, i, False)
                    # 無需射擊，不改 life
                    player = last_player or player

                record.record_game_play_step(
                    game_count, i, False, behavior,
                    cards[f'p{i}'], shots_fired[i],
                    play_reason=play_reason, challenge_reason=challenge_reason
                )

                gun_fired = True
                break

            # 非法輸入
            print("輸入錯誤，請重新輸入。")
            if i == HUMAN_IDX:
                continue
            else:
                raise RuntimeError(f"AI 回傳未知 action: {action}")

        # 下一回合或延續
        if gun_fired:
            round_count += 1
            play_card = []
            target = game.target_card()
            cards = game.draw_cards(4)
            first_round = True
        else:
            print("本回合無人扣板機，繼續當前回合。")
            first_round = False

    # 遊戲結束記錄
    winner = [i for i, alive in enumerate(life) if alive][0]
    record.game_end_record(
        game_count, f"p{winner}", [round_count]*4, question, liar, shots_fired
    )
    print(f"遊戲結束！勝利者為玩家 {winner}。")


if __name__ == '__main__':
    main()
