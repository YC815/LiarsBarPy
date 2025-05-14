# liars_bar/ai/decision.py
from typing import Dict, List, Tuple
from ..models.player import Player
from .strategy import RandomStrategy, RuleBasedStrategy, LearningStrategy
from .llm_manager import LLMManager, AIResponse


class AIDecisionMaker:
    """AI 決策器，可以使用不同的策略"""

    def __init__(self, strategy_type: str = "rule"):
        """
        初始化 AI 決策器
        strategy_type: 策略類型，可選值: "random", "rule", "llm", "learning"
        """
        self.strategy_type = strategy_type

        # 選擇策略
        if strategy_type == "random":
            self.strategy = RandomStrategy()
        elif strategy_type == "learning":
            self.strategy = LearningStrategy()
        elif strategy_type == "llm":
            self.llm_manager = LLMManager()
        else:  # 默認使用規則策略
            self.strategy = RuleBasedStrategy()

    def make_decision(self, game_state: Dict, player_id: int) -> Tuple[str, List[str]]:
        """
        根據遊戲狀態做出決策
        返回: (action, cards)，其中 action 是要執行的動作，cards 是要出的牌（僅當 action 為 "play" 時有值）
        """
        # 嘗試從 players_stats 中獲取基本玩家信息
        player_stats = None
        for p in game_state["players_stats"]:
            if p["id"] == player_id:
                player_stats = p
                break

        # 嘗試獲取完整的玩家對象
        player_obj = None
        if "players" in game_state:
            # 確保 player_id 在有效範圍內
            if 0 <= player_id < len(game_state["players"]):
                player_obj = game_state["players"][player_id]

        # 如果無法獲取玩家對象，則使用當前玩家信息
        if player_obj is None and "current_player" in game_state and game_state["current_player"]["id"] == player_id:
            # 從當前玩家信息創建一個臨時的玩家對象
            from ..models.player import Player, PlayerType
            player_obj = Player(id=player_id, player_type=PlayerType.AI)
            player_obj.hand = game_state["current_player"]["hand"]
            player_obj.gun_pos = game_state["current_player"]["gun_pos"]
            player_obj.bullet_pos = game_state["current_player"].get(
                "bullet_pos", 0)
            player_obj.shots_fired = game_state["current_player"]["shots_fired"]

        # 根據策略類型選擇決策方法
        if self.strategy_type == "llm":
            # 使用 LLM 策略
            decision = self.llm_manager.generate_decision(
                game_state, player_id)
            # 顯示 AI 的行為和原因
            print(f"\nAI {decision['behavior']}")
            print(f"原因: {decision['play_reason']}")
            if decision['was_challenged']:
                print(f"質疑原因: {decision['challenge_reason']}")
        else:
            # 使用其他策略
            if player_obj is None:
                # 如果仍然無法獲取玩家對象，創建一個默認的空手牌玩家
                from ..models.player import Player, PlayerType
                player_obj = Player(id=player_id, player_type=PlayerType.AI)
                # 如果 player_stats 存在，設置基本屬性
                if player_stats is not None:
                    player_obj.alive = player_stats["alive"]
                    player_obj.shots_fired = player_stats["shots_fired"]

            # 使用策略進行決策
            decision = self.strategy.decide_action(game_state, player_obj)

        # 提取動作和牌
        action = decision.get("action", "skip")  # 默認為跳過
        cards = decision.get(
            "played_cards", []) if "played_cards" in decision else decision.get("cards", [])

        return action, cards

    def get_behavior(self, action_type: str, num_cards: int = 0) -> str:
        """生成 AI 行為描述"""
        import random

        behaviors = {
            "play": [
                "慢慢地放下牌，眼神堅定",
                "迅速出牌，臉上掛著輕微的笑容",
                "猶豫了一下，然後出牌",
                f"自信地宣布：「{num_cards}張目標牌」"
            ],
            "challenge": [
                "懷疑地看著上家，質疑其出牌",
                "果斷指出：「我不信！」",
                "皺眉思考後，決定質疑",
                "挑釁地看著上家：「你確定嗎？」"
            ],
            "skip": [
                "輕輕揮手，示意跳過",
                "點頭表示接受上家出牌",
                "思考片刻，決定不質疑",
                "放鬆地靠在椅背上，選擇跳過"
            ],
            "shoot": [
                "果斷地拿起槍，對準自己",
                "深吸一口氣，決定賭一把",
                "眼神堅定，開始俄羅斯輪盤",
                "露出瘋狂的笑容，直接開槍"
            ]
        }

        return random.choice(behaviors.get(action_type, ["面無表情"]))
