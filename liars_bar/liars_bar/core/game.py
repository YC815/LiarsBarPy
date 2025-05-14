# liars_bar/core/game.py
from typing import List, Dict, Optional, Tuple
from ..models.player import Player, PlayerType
from ..utils.card_utils import create_deck, shuffle_and_deal, validate_played_cards
from ..utils.record_manager import RecordManager
import json
import os
import random


class Game:
    """統一的遊戲控制器，整合了之前 class_game.py 和 game_core.py 的功能"""

    def __init__(self, num_players=4, debug=False, human_player_index=0, ai_strategy="rule"):
        self.num_players = num_players
        self.debug = debug
        self.human_player_index = human_player_index
        self.ai_strategy = ai_strategy

        # 創建玩家
        self.players = self._create_players()

        # 初始化遊戲狀態
        self.current_idx = 0
        self.round_count = 0
        self.game_count = 0
        self.target_card = None
        self.last_play_cards = []
        self.last_player_idx = None
        self.play_history = []

        # 初始化記錄管理器
        self.record_manager = None

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
        self.record_manager = RecordManager(self.game_count)

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

        # 初始化遊戲數據
        self.current_idx = 0
        self.last_player_idx = None
        self.round_count = 1

        return self.get_game_state()

    def next(self, player_decision: Dict):
        """處理當前玩家的決策，並更新遊戲狀態"""
        print("DEBUG player_decision:", player_decision)
        current = self.players[self.current_idx]
        action = player_decision.get('action')
        played_cards = player_decision.get('played_cards', [])
        behavior = player_decision.get('behavior', '')
        strategy = player_decision.get('play_reason', '')

        if action == 'play':
            print("DEBUG played_cards before validate:", played_cards)
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
        hands = shuffle_and_deal(deck, len(alive_players))

        for i, player in enumerate(alive_players):
            player.hand = hands[f"p{i}"]
            player.bullet_pos = random.randint(1, 6)
            player.gun_pos = 1

            if i == 0 and self.human_player_index == 0:
                print(f"你的新手牌: {player.hand} | 子彈位置: {player.bullet_pos}")
            elif self.debug:
                print(f"p{i} 的新手牌: {player.hand} | 子彈位置: {player.bullet_pos}")

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
            "players": self.players,
            "current_player": {
                "id": current_player.id,
                "hand": current_player.hand,
                "bullet_pos": current_player.bullet_pos,
                "gun_pos": current_player.gun_pos,
                "shots_fired": current_player.shots_fired
            },
            "last_play": last_play,
            "last_player_idx": self.last_player_idx,
            "last_play_cards": self.last_play_cards,
            "available_actions": self._get_available_actions(),
            "alive_players": [p.id for p in self.players if p.alive],
            "players_stats": [{
                "id": p.id,
                "alive": p.alive,
                "hand_count": len(p.hand),
                "shots_fired": p.shots_fired
            } for p in self.players]
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
        from ..interfaces.cli import GameCLI

        # 初始化命令行界面，傳遞 AI 策略參數
        cli = GameCLI(self, self.ai_strategy)

        # 開始遊戲
        self.start()

        # 主遊戲循環
        while not self.is_game_over():
            # 顯示當前狀態
            cli.display_game_status()

            # 處理玩家輸入
            player_action = cli.get_player_action()

            # 執行動作
            result = self.next(player_action)

            # 顯示結果
            cli.display_action_result(result)

        # 顯示遊戲結果
        cli.display_game_result()
