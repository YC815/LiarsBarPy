from typing import List, Dict, Optional
import random
from dataclasses import dataclass
from enum import Enum
import argparse


class CardType(Enum):
    ACE = "A"
    KING = "K"
    QUEEN = "Q"
    JOKER = "J"


class ActionType(Enum):
    PLAY = "play"           # 出牌
    CHALLENGE = "challenge"  # 質疑
    SKIP = "skip"          # 跳過
    SHOOT = "shoot"        # 開槍


@dataclass
class Player:
    """玩家類別"""
    id: int
    hand: List[str] = None
    alive: bool = True
    bullet_pos: int = None
    gun_pos: int = 1
    shots_fired: int = 0
    challenge_success: int = 0
    challenge_fail: int = 0
    survival_rounds: int = 0

    def __post_init__(self):
        if self.hand is None:
            self.hand = []
        if self.bullet_pos is None:
            self.bullet_pos = random.randint(1, 6)

    def play_cards(self, cards: List[str]) -> bool:
        """出牌"""
        if not all(card in self.hand for card in cards):
            return False
        for card in cards:
            self.hand.remove(card)
        return True

    def shoot(self) -> bool:
        """進行俄羅斯輪盤"""
        is_hit = self.bullet_pos == self.gun_pos
        self.gun_pos = (self.gun_pos % 6) + 1
        self.shots_fired += 1
        if is_hit:
            self.alive = False
        return is_hit


class GameState:
    """遊戲狀態類別"""

    def __init__(self, num_players: int = 4, debug: bool = False):
        self.players = [Player(id=i) for i in range(num_players)]
        self.current_player_idx = 0
        self.target_card = None
        self.round_count = 0
        self.last_play_cards = []
        self.last_player_idx = None
        self.deck = self._create_deck()
        self.debug = debug

    def _create_deck(self) -> List[str]:
        """創建牌組"""
        deck = []
        # 每種牌各 6 張
        for card_type in [CardType.ACE, CardType.KING, CardType.QUEEN]:
            deck.extend([card_type.value] * 6)
        # Joker 2 張
        deck.extend([CardType.JOKER.value] * 2)
        return deck

    def shuffle_and_deal(self):
        """洗牌並發牌"""
        random.shuffle(self.deck)
        # 確保每個玩家拿到相同數量的牌
        cards_per_player = len(self.deck) // len(self.players)
        for i, player in enumerate(self.players):
            start_idx = i * cards_per_player
            end_idx = start_idx + cards_per_player
            player.hand = self.deck[start_idx:end_idx]
            if self.debug:
                print(f"玩家 {player.id} 的手牌：{player.hand}")

    def get_next_player(self) -> Player:
        """取得下一位玩家"""
        next_idx = (self.current_player_idx + 1) % len(self.players)
        while not self.players[next_idx].alive:
            next_idx = (next_idx + 1) % len(self.players)
        return self.players[next_idx]

    def is_game_over(self) -> bool:
        """檢查遊戲是否結束"""
        return sum(1 for p in self.players if p.alive) <= 1

    def get_winner(self) -> Optional[Player]:
        """取得贏家"""
        for player in self.players:
            if player.alive:
                return player
        return None

    def get_available_actions(self) -> List[ActionType]:
        """取得當前可用的動作列表"""
        available_actions = [ActionType.PLAY]  # 出牌永遠可用

        if self.last_play_cards:  # 如果有上家出牌
            available_actions.append(ActionType.CHALLENGE)  # 可以質疑
            available_actions.append(ActionType.SKIP)      # 可以跳過

            # 只有在特定條件下才能直接開槍
            current_player = self.players[self.current_player_idx]
            if current_player.shots_fired < 6:  # 開槍次數未達上限
                available_actions.append(ActionType.SHOOT)

        return available_actions


class Game:
    """遊戲主類別"""

    def __init__(self, num_players: int = 4, debug: bool = False):
        self.state = GameState(num_players, debug)
        self.debug = debug

    def start(self):
        """開始遊戲"""
        self.state.target_card = random.choice(
            [CardType.ACE.value, CardType.KING.value, CardType.QUEEN.value])
        self.state.shuffle_and_deal()
        if self.debug:
            print(f"目標牌：{self.state.target_card}")
            for player in self.state.players:
                print(f"玩家 {player.id} 的手牌：{player.hand}")

    def get_game_status(self) -> Dict:
        """取得當前遊戲狀態"""
        current_player = self.state.players[self.state.current_player_idx]
        return {
            "round": self.state.round_count,
            "target_card": self.state.target_card,
            "current_player": {
                "id": current_player.id,
                "hand": current_player.hand,
                "bullet_pos": current_player.bullet_pos,
                "gun_pos": current_player.gun_pos,
                "shots_fired": current_player.shots_fired
            },
            "last_play": {
                "player_id": self.state.last_player_idx,
                "cards": self.state.last_play_cards
            } if self.state.last_player_idx is not None else None,
            "available_actions": self.get_available_actions(),
            "alive_players": [p.id for p in self.state.players if p.alive]
        }

    def next(self, action: ActionType, cards: Optional[List[str]] = None) -> Dict:
        """執行下一個動作"""
        result = self.play_turn(action, cards)
        if result["success"]:
            self.state.round_count += 1
        return {
            **result,
            "game_status": self.get_game_status()
        }

    def play_turn(self, action: ActionType, cards: Optional[List[str]] = None) -> Dict:
        """執行一個回合"""
        current_player = self.state.players[self.state.current_player_idx]

        if action == ActionType.PLAY:
            if not cards:
                return {"success": False, "message": "必須指定要出的牌"}

            if not current_player.play_cards(cards):
                return {"success": False, "message": "無效的出牌"}

            self.state.last_play_cards = cards
            self.state.last_player_idx = current_player.id
            self.state.current_player_idx = self.state.players.index(
                self.state.get_next_player())

            return {"success": True, "message": f"玩家 {current_player.id} 出牌：{cards}"}

        elif action == ActionType.CHALLENGE:
            if not self.state.last_play_cards:
                return {"success": False, "message": "沒有可質疑的出牌"}

            is_cheating = not all(card in [self.state.target_card, CardType.JOKER.value]
                                  for card in self.state.last_play_cards)

            shooter = self.state.players[self.state.last_player_idx] if is_cheating else current_player
            return self._handle_shoot(shooter)

        elif action == ActionType.SKIP:
            if not self.state.last_play_cards:
                return {"success": False, "message": "沒有可跳過的出牌"}

            self.state.current_player_idx = self.state.players.index(
                self.state.get_next_player())
            return {"success": True, "message": f"玩家 {current_player.id} 選擇跳過"}

        elif action == ActionType.SHOOT:
            return self._handle_shoot(current_player)

        return {"success": False, "message": "無效的動作"}

    def _handle_shoot(self, shooter: Player) -> Dict:
        """處理開槍邏輯"""
        hit = shooter.shoot()

        if hit:
            print(f"玩家 {shooter.id} 中彈！")
        else:
            print(f"玩家 {shooter.id} 倖存！")

        if self.state.is_game_over():
            return {"success": True, "message": "遊戲結束", "game_over": True}

        # 重置遊戲狀態
        self.state.target_card = random.choice(
            [CardType.ACE.value, CardType.KING.value, CardType.QUEEN.value])
        self.state.shuffle_and_deal()
        self.state.last_play_cards = []
        self.state.last_player_idx = None

        return {"success": True, "message": "開槍完成", "hit": hit}

    def get_available_actions(self) -> List[ActionType]:
        """取得當前可用的動作列表"""
        return self.state.get_available_actions()

    def get_action_description(self, action: ActionType) -> str:
        """取得動作的描述"""
        descriptions = {
            ActionType.PLAY: "出牌",
            ActionType.CHALLENGE: "質疑上家",
            ActionType.SKIP: "跳過回合",
            ActionType.SHOOT: "直接開槍"
        }
        return descriptions.get(action, "未知動作")

    def run(self):
        """執行遊戲"""
        self.start()

        while not self.state.is_game_over():
            status = self.get_game_status()
            current = status["current_player"]

            print(f"\n=== 第 {status['round']} 回合 ===")
            print(f"目標牌：{status['target_card']}")
            print(f"當前玩家：{current['id']}")
            print(f"手牌：{current['hand']}")
            print(f"子彈位置：{current['bullet_pos']} | 槍管位置：{current['gun_pos']}")
            print(f"已開槍次數：{current['shots_fired']}")

            if status["last_play"]:
                # print(
                # f"\n上家 (玩家 {status['last_play']['player_id']}) 出牌：{status['last_play']['cards']}")
                pass

            print("\n可選擇的動作：")
            for i, action in enumerate(status["available_actions"], 1):
                print(f"{i}. {self.get_action_description(action)}")

            while True:
                try:
                    choice = int(
                        input(f"請選擇動作 (1-{len(status['available_actions'])}): "))
                    if 1 <= choice <= len(status["available_actions"]):
                        action = status["available_actions"][choice - 1]
                        break
                    print(f"請輸入 1 到 {len(status['available_actions'])} 之間的數字")
                except ValueError:
                    print("請輸入有效的數字")

            if action == ActionType.PLAY:
                cards_input = input("請輸入要出的牌（用空格分隔）：").upper().split()
                result = self.next(action, cards_input)
            else:
                result = self.next(action)

            print(result["message"])

            if result.get("game_over"):
                break

        winner = self.state.get_winner()
        if winner:
            print(f"\n遊戲結束！玩家 {winner.id} 獲勝！")

    def get_ai_decision(self, player_id: int) -> Dict:
        """取得 AI 的決策"""
        available_actions = self.get_available_actions()
        current_player = self.state.players[player_id]

        # 這裡可以加入 AI 的決策邏輯
        # 目前使用簡單的隨機選擇
        action = random.choice(available_actions)

        if action == ActionType.PLAY:
            # 簡單的 AI 出牌邏輯
            hand = current_player.hand
            num_cards = min(random.randint(1, 3), len(hand))
            cards_to_play = random.sample(hand, num_cards)
            return {
                "action": action,
                "cards": cards_to_play
            }
        else:
            return {
                "action": action,
                "cards": None
            }


if __name__ == "__main__":
    # 範例使用方式
    game = Game(debug=True)

    # 開始遊戲
    game.start()

    # 範例：玩家 0 出牌
    result = game.next(ActionType.PLAY, ["Q", "J"])
    print("\n遊戲狀態：")
    print(f"當前玩家：{result['game_status']['current_player']['id']}")
    print(
        f"可用動作：{[a.value for a in result['game_status']['available_actions']]}")

    # 範例：玩家 1 質疑
    result = game.next(ActionType.CHALLENGE)
    print("\n遊戲狀態：")
    print(f"當前玩家：{result['game_status']['current_player']['id']}")
    print(
        f"可用動作：{[a.value for a in result['game_status']['available_actions']]}")

    # 繼續遊戲
    game.run()
