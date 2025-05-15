from functions import record as record_fn
from functions import ai as ai_fn
import random
from typing import List, Dict, Optional
from ..models.player import Player
from ..utils.game_utils import (
    create_deck, shuffle_and_deal, validate_played_cards,
    format_game_status, format_game_statistics
)
import datetime
import sys
sys.path.append('./functions')


class Game:
    """遊戲主類別，包含遊戲流程與狀態管理"""

    def __init__(self, num_players=4, debug=False, human_player=True):
        # 基本設定
        assert 2 <= num_players <= 4, "玩家數量必須在2到4之間"
        self.num_players = num_players
        self.debug = debug
        self.human_player = human_player
        self.players = [Player(id=i) for i in range(num_players)]
        self.current_idx = 0
        self.target_card = None
        self.round_count = 0
        self.game_count = None
        self.logger = None

        # 遊戲記錄
        self.play_history = []
        self.opinions = {i: {} for i in range(num_players)}

        # 上一次動作相關
        self.last_play_cards = []
        self.last_player_idx = None

    def start(self):
        """初始化遊戲"""
        # 初始化記錄環境
        self.game_count = record_fn.init()
        self.logger = record_fn.GameLogger(self.game_count)

        # 抽取目標牌
        self.target_card = random.choice(["A", "K", "Q"])
        self.logger.update_target_card(self.target_card)

        # 發牌並設置初始狀態
        deck = create_deck()
        hands = shuffle_and_deal(deck, self.num_players)
        for i in range(self.num_players):
            self.players[i].hand = hands[f"p{i}"]
            self.players[i].bullet_pos = random.randint(1, 6)
            self.players[i].alive = True

        # 初始化遊戲數據
        self.current_idx = 0
        self.last_player_idx = None
        self.round_count = 1

        # 輸出遊戲初始狀態
        print(f"===== 遊戲開始！第 {self.game_count} 局 =====")
        print(f"目標牌：{self.target_card}")
        if self.debug:
            for p in self.players:
                print(
                    f"p{p.id} 手牌: {p.hand} | 子彈位置: {p.bullet_pos} | 槍管位置: {p.gun_pos}")

        return self.get_game_state()

    def next(self, player_decision: Dict):
        """處理當前玩家的決策，並更新遊戲狀態"""
        current = self.players[self.current_idx]
        action = player_decision.get('action')
        played_cards = player_decision.get('played_cards', [])
        behavior = player_decision.get('behavior', '')
        strategy = player_decision.get('play_reason', '')

        if action == 'play':
            # 處理出牌
            valid, msg = validate_played_cards(played_cards, current.hand)
            if not valid:
                print(f"出牌無效: {msg}")
                return self.get_game_state()

            # 移除出的牌
            for card in played_cards:
                current.hand.remove(card)

            # 記錄動作
            self.logger.log_action(
                player_id=current.id,
                action_type='play',
                cards_played=played_cards,
                cards_remaining=current.hand,
                shots_fired=current.shots_fired,
                behavior=behavior,
                strategy=strategy,
                bullet_pos=current.bullet_pos if self.debug else None
            )

            self.last_play_cards = played_cards
            self.last_player_idx = current.id

            # 檢查是否出完所有牌
            if len(current.hand) == 0:
                print(f"p{current.id} 出完所有牌，系統對其自動質疑")
                is_cheating = not all(
                    card in [self.target_card, 'J'] for card in played_cards)

                if is_cheating:
                    print(f"質疑成功！p{current.id} 被系統發現出了非目標牌")
                    hit = self._russian_roulette(current.id)
                else:
                    print(f"質疑失敗！p{current.id} 所出的牌全部是目標牌或萬能牌")

                if self._reset_game_state():
                    return self.get_game_state()

            # 更新下一輪玩家
            self.current_idx = self._get_next_player_idx(self.current_idx)

        elif action == 'challenge':
            # 處理質疑
            if self.last_player_idx is None or not self.last_play_cards:
                print("錯誤：沒有可質疑的上一輪出牌")
                return self.get_game_state()

            is_cheating = not all(card in [self.target_card, 'J']
                                  for card in self.last_play_cards)
            print(f"質疑結果: {'成功' if is_cheating else '失敗'}")

            # 記錄動作
            self.logger.log_action(
                player_id=current.id,
                action_type='challenge',
                cards_played=[],
                cards_remaining=current.hand,
                shots_fired=current.shots_fired,
                behavior=behavior,
                strategy=player_decision.get('challenge_reason', ''),
                bullet_pos=current.bullet_pos if self.debug else None
            )

            # 根據質疑結果決定誰開槍
            shooter_idx = self.last_player_idx if is_cheating else current.id
            print(f"p{shooter_idx} 將進行俄羅斯輪盤...")
            hit = self._russian_roulette(shooter_idx)

            if self._reset_game_state():
                return self.get_game_state()

            # 更新下一位玩家
            if self.players[shooter_idx].alive:
                self.current_idx = shooter_idx
            else:
                self.current_idx = self._get_next_player_idx(shooter_idx)

        self.round_count += 1
        self.logger.next_round()
        return self.get_game_state()

    def end(self):
        """結束遊戲，顯示結果"""
        winner = self.get_winner()
        if winner is not None:
            print(f"\n===== 遊戲結束！p{winner} 勝利！=====\n")
        else:
            print("\n===== 遊戲結束！沒有獲勝者 =====\n")

        # 顯示統計資訊
        print(format_game_statistics(self.players))

        return {
            "winner": winner,
            "statistics": {p.id: {
                "survival_rounds": p.survival_rounds,
                "challenge_success": p.challenge_success,
                "challenge_fail": p.challenge_fail,
                "shots_fired": p.shots_fired
            } for p in self.players}
        }

    def _get_next_player_idx(self, idx):
        """取得下一位活著的玩家索引"""
        next_idx = (idx + 1) % self.num_players
        while not self.players[next_idx].alive:
            next_idx = (next_idx + 1) % self.num_players
        return next_idx

    def _russian_roulette(self, player_idx: int) -> bool:
        """玩家進行俄羅斯輪盤"""
        player = self.players[player_idx]
        is_hit = player.bullet_pos == player.gun_pos
        player.gun_pos = (player.gun_pos % 6) + 1
        player.shots_fired += 1

        print(f"p{player_idx} {'中彈！' if is_hit else '倖存！'}")

        if is_hit:
            player.alive = False
            print(f"p{player_idx} 已出局！")

        # 記錄開槍動作
        self.logger.log_action(
            player_id=player_idx,
            action_type='shoot',
            cards_played=[],
            cards_remaining=player.hand,
            shots_fired=player.shots_fired,
            behavior='進行俄羅斯輪盤',
            bullet_pos=player.bullet_pos if self.debug else None
        )

        return is_hit

    def _reset_game_state(self) -> bool:
        """重置遊戲狀態"""
        alive_count = sum(1 for p in self.players if p.alive)
        if alive_count <= 1:
            return True

        print("\n===== 重新洗牌與發牌 =====\n")

        self.target_card = random.choice(["A", "K", "Q"])
        self.logger.update_target_card(self.target_card)
        print(f"新目標牌：{self.target_card}")

        deck = create_deck()
        alive_players = [p for p in self.players if p.alive]
        hands = shuffle_and_deal(deck, len(alive_players))

        for i, player in enumerate(alive_players):
            player.hand = hands[f"p{i}"]
            player.bullet_pos = random.randint(1, 6)
            player.gun_pos = 1

            if i == 0 and self.human_player:
                print(f"你的新手牌: {player.hand} | 子彈位置: {player.bullet_pos}")
            elif self.debug:
                print(f"p{i} 的新手牌: {player.hand} | 子彈位置: {player.bullet_pos}")

        self.last_play_cards = []
        self.last_player_idx = None
        return False

    def get_game_state(self):
        """獲取當前遊戲狀態"""
        return {
            "round": self.round_count,
            "current_player": self.current_idx,
            "target_card": self.target_card,
            "alive_players": [p.id for p in self.players if p.alive],
            "game_over": self.is_game_over(),
            "winner": self.get_winner() if self.is_game_over() else None,
            "last_play": {
                "player": self.last_player_idx,
                "cards": self.last_play_cards
            } if self.last_player_idx is not None else None
        }

    def is_game_over(self):
        """檢查遊戲是否結束"""
        alive_count = sum(1 for p in self.players if p.alive)
        return alive_count <= 1

    def get_winner(self):
        """獲取贏家"""
        for p in self.players:
            if p.alive:
                return p.id
        return None

    def run(self):
        """執行完整遊戲流程"""
        self.start()

        game_over = False
        while not game_over:
            # 獲取當前玩家的決策
            current = self.players[self.current_idx]
            if self.human_player and current.id == 0:
                # 真人玩家
                decision = self._get_human_choice(current.id)
            else:
                # AI 玩家
                try:
                    decision = self._make_ai_decision(current.id)
                except Exception as e:
                    if self.debug:
                        print(f"[AI 模型錯誤: {str(e)}]")
                    decision = self._make_basic_decision(current.id)

            # 處理玩家決策
            game_state = self.next(decision)
            game_over = game_state["game_over"]

        # 遊戲結束，顯示結果
        result = self.end()

        # 進行玩家互評
        try:
            if self.debug:
                print("[嘗試使用 AI 互評玩家]")
            self.opinions = ai_fn.review_players(
                self.game_count, self.opinions, True, self.debug)
        except Exception as e:
            if self.debug:
                print(f"[AI 互評失敗: {str(e)}]")
            self.opinions = self._make_basic_reviews()

        return result

    def _make_basic_reviews(self):
        """產生基本互評，當AI API 無法使用時的備用方案"""
        opinions = {}
        for i in range(self.num_players):
            opinions[f"p{i}"] = {}
            for j in range(self.num_players):
                if i != j:
                    # 根據遊戲表現生成簡單的互評
                    player_i = self.players[i]
                    player_j = self.players[j]

                    if not player_i.alive and player_j.alive:
                        # 評價存活者
                        opinions[f"p{i}"][f"p{j}"] = "比我幸運，手牌運氣也好。"
                    elif player_i.alive and not player_j.alive:
                        # 評價出局者
                        opinions[f"p{i}"][f"p{j}"] = "運氣不佳，可能做出了錯誤的決策。"
                    else:
                        # 一般評價
                        if random.random() < 0.3:
                            opinions[f"p{i}"][f"p{j}"] = "玩得較為錯級，很難看透。"
                        elif random.random() < 0.6:
                            opinions[f"p{i}"][f"p{j}"] = "策略合理，為自己設想了生歛之路。"
                        else:
                            opinions[f"p{i}"][f"p{j}"] = "有小心機，但有時候會高估自己。"
        return opinions

    def _get_human_choice(self, player_idx, can_challenge=True):
        """獲取真人玩家的決策與選擇"""
        player = self.players[player_idx]

        # 顯示遊戲資訊
        print(f"\n=== 玩家行動 ===\n"
              f"目標牌: {self.target_card}\n"
              f"你的手牌: {player.hand}\n"
              f"子彈位置: {player.bullet_pos} | 槍管位置: {player.gun_pos} | 開槍次數: {player.shots_fired}")

        if self.last_player_idx is not None and self.last_play_cards and can_challenge:
            last_p = self.players[self.last_player_idx]
            # print(f"\n上家 p{last_p.id} 出了: {self.last_play_cards}")

            # 選擇出牌或質疑
            while True:
                choice = input("\n請選擇: 1=出牌, 2=質疑: ")
                if choice in ['1', '2']:
                    break
                print("請輸入有效的選項（1或 2）")

            if choice == '2':  # 質疑
                reason = input("質疑原因 (選填): ")
                return {
                    'action': 'challenge',
                    'played_cards': [],
                    'behavior': '對對手的言行感到不信任',
                    'play_reason': '',
                    'challenge_reason': reason or '對手行為可疑'
                }
        else:
            # 必須出牌
            print("\n你必須出牌（無法質疑）")

        # 選擇出牌
        while True:
            try:
                cards_input = input(f"\n請從 {player.hand} 中選擇 1-3 張牌出（空格分隔）: ")
                cards_to_play = cards_input.strip().upper().split()

                # 檢查合法性
                if not (1 <= len(cards_to_play) <= 3):
                    print("出牌數量必須在 1-3 張之間")
                    continue

                valid, msg = validate_played_cards(cards_to_play, player.hand)
                if not valid:
                    print(f"出牌無效: {msg}")
                    continue

                break
            except Exception as e:
                print(f"輸入錯誤: {e}")

        # 產生題外理由及行為
        reason = input("出牌理由 (選填): ")

        return {
            'action': 'play',
            'played_cards': cards_to_play,
            'behavior': '思考後出牌',
            'play_reason': reason or '根據目前狀況做出的最佳決策',
            'challenge_reason': ''
        }

    def _make_ai_decision(self, player_id: int) -> dict:
        """AI 玩家做出決策"""
        try:
            # 創建 GameState 物件
            game_state = ai_fn.GameState(
                game_count=self.game_count,
                target_card=self.target_card,
                players=self.players,
                play_history=self.play_history,
                player_insights=self.opinions,
                last_played_cards=self.last_play_cards
            )
            return ai_fn.ai_selection_langchain(
                game_state=game_state,
                player_id=player_id,
                round_count=self.round_count
            )
        except Exception as e:
            print(f"[AI 模型錯誤: {str(e)}]")
            return self._make_basic_decision(player_id)

    def _make_basic_decision(self, player_id: int) -> dict:
        """使用簡單規則進行 AI 決策"""
        player = self.players[player_id]
        hand = player.hand
        target_count = hand.count(self.target_card)  # 目標牌數量
        joker_count = hand.count('J')               # 王牌數量
        strong_cards = target_count + joker_count   # 強牌總數

        # 預設返回模板
        ai_response = {
            'action': None,
            'played_cards': [],
            'behavior': '',
            'play_reason': '',
            'challenge_reason': ''
        }

        # 上一輪是否有人出牌
        can_challenge = self.last_player_idx is not None and len(
            self.last_play_cards) > 0

        # 決策邏輯
        if not can_challenge:
            # 必須出牌
            ai_response['action'] = 'play'
            # 選擇 1-3 張牌 (優先選擇目標牌)
            num_cards = min(random.randint(1, 3), len(hand))
            hand_copy = hand.copy()
            cards_to_play = []

            # 優先排序出目標牌和王牌
            for card_type in [self.target_card, 'J', 'A', 'K', 'Q']:
                for card in hand_copy[:]:
                    if len(cards_to_play) >= num_cards:
                        break
                    if card == card_type:
                        cards_to_play.append(card)
                        hand_copy.remove(card)

            ai_response['played_cards'] = cards_to_play
            ai_response['behavior'] = "謹慎地出牌"
            ai_response['play_reason'] = "根據策略選擇最佳牌組"
        else:
            # 簡單邏輯判斷是否質疑
            if len(self.last_play_cards) > 2 and random.random() < 0.5:
                ai_response['action'] = 'challenge'
                ai_response['behavior'] = "懷疑地看著對方的出牌"
                ai_response['challenge_reason'] = "對手出牌數量過多，值得懷疑"
            else:
                ai_response['action'] = 'play'
                # 選擇 1-3 張牌 (優先選擇目標牌)
                num_cards = min(random.randint(1, 3), len(hand))
                hand_copy = hand.copy()
                cards_to_play = []

                # 優先排序出目標牌和王牌
                for card_type in [self.target_card, 'J', 'A', 'K', 'Q']:
                    for card in hand_copy[:]:
                        if len(cards_to_play) >= num_cards:
                            break
                        if card == card_type:
                            cards_to_play.append(card)
                            hand_copy.remove(card)

                ai_response['played_cards'] = cards_to_play
                ai_response['behavior'] = "謹慎地出牌"
                ai_response['play_reason'] = "根據策略選擇最佳牌組"

        return ai_response
