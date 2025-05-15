# liars_bar/core/game.py
from typing import List, Dict, Optional, Tuple
from models.player import Player, PlayerType
from utils.card_utils import create_deck, shuffle_and_deal, validate_played_cards
from utils.record_manager import RecordManager
import json
import os
import random
from enum import Enum
from datetime import datetime


class Game:
    """統一的遊戲控制器，整合了之前 class_game.py 和 game_core.py 的功能"""

    def __init__(self, num_players=4, debug=False, human_player_index=0, ai_strategy="rule", kill_player_on_start: Optional[int] = None, interactive_pause: bool = True):
        self.num_players = num_players
        self.debug = debug
        self.human_player_index = human_player_index
        self.ai_strategy = ai_strategy
        self.kill_player_on_start = kill_player_on_start
        self.interactive_pause = interactive_pause

        # 創建玩家
        self.players = self._create_players()

        # 生成唯一的 session_id 給 RecordManager
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")  # 年月日_時分秒_微秒

        # 初始化遊戲狀態
        self.current_idx = 0
        self.round_count = 0
        self.game_count = 0  # 會在 start() 中被 _get_next_game_count() 更新
        self.target_card = None
        self.last_play_cards = []
        self.last_player_idx = None
        self.play_history = []

        # 初始化記錄管理器 (會在 start() 中被賦值)
        self.record_manager: Optional[RecordManager] = None
        self.current_log_directory: Optional[str] = None

    def _create_players(self) -> List[Player]:
        """創建玩家列表"""
        players = []
        for i in range(self.num_players):
            player_type = PlayerType.HUMAN if i == self.human_player_index else PlayerType.AI
            players.append(Player(id=i, player_type=player_type))
        return players

    def start(self):
        """開始新遊戲"""
        # 初始化記錄管理器
        self.game_count = self._get_next_game_count()
        self.record_manager = RecordManager(
            self.game_count, self.session_id)  # 傳遞 session_id
        self.current_log_directory = self.record_manager.get_log_directory_path()
        # 偵錯輸出
        # print(
        #     f"DEBUG: Log directory for this session: {self.current_log_directory}")

        # 抽取目標牌
        self.target_card = self._draw_target_card()
        self.record_manager.update_target_card(self.target_card)

        # 發牌並設置初始狀態
        deck = create_deck()
        hands = shuffle_and_deal(deck, self.num_players)
        for i in range(self.num_players):
            self.players[i].hand = hands[f"p{i}"]
            self.players[i].bullet_pos = random.randint(1, 6)
            self.players[i].alive = True

        # 新增：根據 kill_player_on_start 設定玩家死亡狀態
        if self.kill_player_on_start is not None and 0 <= self.kill_player_on_start < self.num_players:
            player_to_kill = self.players[self.kill_player_on_start]
            if player_to_kill.alive:  # 確保只 "殺死" 活著的玩家一次
                player_to_kill.alive = False
                print(f"DEBUG: 玩家 {player_to_kill.id} 已在遊戲開始時被設定為死亡狀態。")
                # 可以在此處添加日誌記錄，如果 RecordManager 已經初始化且可用
                if self.record_manager:
                    self.record_manager.log_action(
                        player_id=player_to_kill.id,
                        action_type='debug_kill_on_start',
                        cards_played=[],
                        cards_remaining=player_to_kill.hand,
                        shots_fired=player_to_kill.shots_fired,
                        behavior='被偵錯選項在開局殺死',
                        strategy='N/A'
                    )

        # 初始化遊戲數據
        self.current_idx = 0
        self.last_player_idx = None
        self.round_count = 1

        return self.get_game_state()

    def next(self, player_decision: Dict):
        """處理當前玩家的決策，並更新遊戲狀態"""
        # print("DEBUG player_decision:", player_decision)
        current = self.players[self.current_idx]
        action = player_decision.get('action')
        played_cards = player_decision.get('played_cards', [])
        behavior = player_decision.get('behavior', '')
        strategy = player_decision.get('play_reason', '')

        if action == 'play':
            # print("DEBUG played_cards before validate:", played_cards)
            valid, msg = validate_played_cards(played_cards, current.hand)
            if not valid:
                print(f"出牌無效: {msg}")
                return self.get_game_state()

            # 移除出的牌
            for card in played_cards:
                current.hand.remove(card)

            # 記錄動作
            self.record_manager.log_action(
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
            self.record_manager.log_action(
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
        self.record_manager.next_round()
        return self.get_game_state()

    def _get_next_game_count(self) -> int:
        """獲取下一局遊戲的編號"""
        try:
            with open("log/game_info.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            game_count = data.get("game_count", 0) + 1
        except (FileNotFoundError, json.JSONDecodeError):
            game_count = 1
            os.makedirs("log", exist_ok=True)
            data = {"game_count": game_count}

        with open("log/game_info.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        return game_count

    def _draw_target_card(self) -> str:
        """抽取目標牌"""
        return random.choice(["A", "K", "Q"])

    def _get_next_player_idx(self, idx: int) -> int:
        """獲取下一位活著的玩家索引"""
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
        self.record_manager.log_action(
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

        self.target_card = self._draw_target_card()
        self.record_manager.update_target_card(self.target_card)
        print(f"新目標牌：{self.target_card}")

        deck = create_deck()
        alive_players = [p for p in self.players if p.alive]
        print(f"DEBUG: _reset_game_state - 存活玩家數量: {len(alive_players)}")
        hands = shuffle_and_deal(deck, len(alive_players))
        # print(
        # f"DEBUG: _reset_game_state - shuffle_and_deal 返回的 hands: {hands}")

        for i, player in enumerate(alive_players):
            player.hand = hands[f"p{i}"]
            player.bullet_pos = random.randint(1, 6)
            player.gun_pos = 1
            # print(
            #     f"DEBUG: _reset_game_state - 玩家 {player.id} (alive_players[{i}]) 被分配到手牌: {player.hand} (數量: {len(player.hand)})")

            if i == 0 and self.human_player_index == player.id:
                print(f"你的新手牌: {player.hand} | 子彈位置: {player.bullet_pos}")
            elif self.debug:
                print(
                    f"p{player.id} 的新手牌: {player.hand} | 子彈位置: {player.bullet_pos}")

        self.last_play_cards = []
        self.last_player_idx = None
        return False

    def get_game_state(self) -> Dict:
        """獲取當前遊戲狀態的完整描述"""
        current_player = self.players[self.current_idx]

        # 安全地處理 last_play 資訊
        last_play = None
        if self.last_player_idx is not None and self.last_play_cards:
            last_play = {
                "player_id": self.last_player_idx,
                "cards": self.last_play_cards
            }

        return {
            "game_count": self.game_count,
            "round_count": self.round_count,
            "target_card": self.target_card,
            "players": self.players,  # 傳遞完整的 Player 物件列表
            "current_player": {  # 提供當前玩家的簡化資訊
                "id": current_player.id,
                "hand": current_player.hand,
                "bullet_pos": current_player.bullet_pos,
                "gun_pos": current_player.gun_pos,
                "shots_fired": current_player.shots_fired
            },
            "last_play": last_play,
            "last_player_idx": self.last_player_idx,  # 為了相容舊的 AI 邏輯，可考慮移除
            "last_play_cards": self.last_play_cards,  # 為了相容舊的 AI 邏輯，可考慮移除
            "available_actions": self._get_available_actions(),
            "alive_players": [p.id for p in self.players if p.alive],
            "players_stats": [{  # 提供所有玩家的統計資訊，AI 可能會用到
                "id": p.id,
                "alive": p.alive,
                "hand_count": len(p.hand),
                "shots_fired": p.shots_fired
            } for p in self.players],
            "record_manager": self.record_manager,  # AI 可能需要用 RecordManager 的方法
            "current_log_directory": self.current_log_directory  # 新增：當前記錄目錄
        }

    def _get_available_actions(self) -> List[str]:
        """獲取當前可用的動作列表"""
        actions = ["play"]
        if self.last_player_idx is not None and self.last_play_cards:
            actions.append("challenge")
        return actions

    def is_game_over(self) -> bool:
        """檢查遊戲是否結束"""
        alive_count = sum(1 for p in self.players if p.alive)
        return alive_count <= 1

    def get_winner(self) -> Optional[int]:
        """獲取贏家ID，如果沒有贏家則返回None"""
        for player in self.players:
            if player.alive:
                return player.id
        return None

    def run(self):
        """運行完整的遊戲流程"""
        from interfaces.cli import GameCLI

        class GameState(Enum):
            """遊戲狀態類，使用列舉型別來增加程式可讀性和型別安全"""
            INITIALIZING = 0
            STARTED = 1
            PLAYER_TURN = 2
            PROCESSING_ACTION = 3
            ROUND_END = 4
            GAME_OVER = 5

        class GameEvent:
            """遊戲事件類，用於處理遊戲中的各種事件"""

            def __init__(self, event_type, data=None):
                self.event_type = event_type
                self.data = data if data else {}

        class EventHandler:
            """事件處理器類，處理遊戲中的各種事件並更新狀態"""

            def __init__(self, game, interface):
                self.game = game
                self.interface = interface
                self.state = GameState.INITIALIZING

            def change_state(self, new_state):
                """改變遊戲狀態"""
                self.state = new_state

            def handle_event(self, event):
                """處理遊戲事件"""
                if event.event_type == "game_start":
                    self._handle_game_start()
                elif event.event_type == "round_start":
                    self._handle_round_start()
                elif event.event_type == "player_input":
                    return self._handle_player_input(event.data)
                elif event.event_type == "action_processed":
                    self._handle_action_processed(event.data)
                elif event.event_type == "game_over":
                    self._handle_game_over()

            def _handle_game_start(self):
                """處理遊戲開始事件"""
                self.game.start()
                self.change_state(GameState.STARTED)

            def _handle_round_start(self):
                """處理回合開始事件"""
                self.interface.display_game_status()
                self.change_state(GameState.PLAYER_TURN)

            def _handle_player_input(self, data):
                """處理玩家輸入事件"""
                player_action = self.interface.get_player_action()
                self.change_state(GameState.PROCESSING_ACTION)
                return player_action

            def _handle_action_processed(self, data):
                """處理動作處理完成事件"""
                result = self.game.next(data.get("player_action"))
                self.interface.display_action_result(result)

                if self.game.is_game_over():
                    self.change_state(GameState.GAME_OVER)
                else:
                    self.change_state(GameState.ROUND_END)

            def _handle_game_over(self):
                """處理遊戲結束事件"""
                self.interface.display_game_result()

        # 初始化命令行界面，傳遞 AI 策略參數
        try:
            cli = GameCLI(self, self.ai_strategy, self.interactive_pause)
            # 初始化事件處理器
            event_handler = EventHandler(self, cli)

            # 開始遊戲
            event_handler.handle_event(GameEvent("game_start"))

            # 主遊戲循環
            while event_handler.state != GameState.GAME_OVER:
                try:
                    # 開始新回合
                    event_handler.handle_event(GameEvent("round_start"))

                    # 獲取玩家輸入
                    player_action = event_handler.handle_event(
                        GameEvent("player_input"))

                    # 處理玩家動作
                    event_handler.handle_event(GameEvent("action_processed",
                                                         {"player_action": player_action}))

                except Exception as e:
                    print(f"回合處理錯誤: {str(e)}")
                    # 繼續下一回合而不中斷遊戲
                    continue

            # 遊戲結束處理
            event_handler.handle_event(GameEvent("game_over"))

        except Exception as e:
            print(f"遊戲初始化錯誤: {str(e)}")
            # 遊戲無法繼續時的優雅退出
            print("遊戲被迫終止")

        finally:
            # 清理資源（如有必要）
            print("遊戲結束，感謝遊玩！")

        return True
