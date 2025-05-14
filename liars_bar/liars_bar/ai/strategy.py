from typing import List, Dict, Any, Tuple
from ..models.player import Player


class Strategy:
    """AI策略基類"""

    def __init__(self):
        pass

    def decide_action(self, game_state: Dict, player: Player) -> Dict:
        """決定執行什麼動作"""
        raise NotImplementedError("子類必須實現此方法")


class RandomStrategy(Strategy):
    """隨機策略"""

    def decide_action(self, game_state: Dict, player: Player) -> Dict:
        import random

        # 確保 player 具有 hand 屬性
        if player is None or not hasattr(player, 'hand') or player.hand is None:
            return {"action": "skip", "cards": []}

        # 獲取可用的動作列表
        available_actions = self._get_available_actions(game_state, player)

        # 隨機選擇一個動作
        action_type = random.choice(available_actions)

        if action_type == "play":
            # 隨機選擇1-3張手牌
            if not player.hand:
                # 如果沒有手牌，嘗試其他動作
                if len(available_actions) > 1:
                    return self.decide_action(game_state, player)
                else:
                    # 如果只能出牌但沒有手牌，隨便返回一個
                    return {"action": "play", "cards": []}

            num_cards = min(random.randint(1, 3), len(player.hand))
            cards = random.sample(player.hand, num_cards)
            return {"action": "play", "cards": cards}

        # 其他動作不需要額外參數
        return {"action": action_type}

    def _get_available_actions(self, game_state: Dict, player: Player = None) -> List[str]:
        """獲取當前可用的動作列表"""
        actions = []

        # 根據規則，只有在玩家沒有手牌時才能跳過
        if player is not None and hasattr(player, 'hand') and not player.hand:
            actions.append("skip")
        else:
            # 有手牌時必須出牌
            actions.append("play")

        # 只有上家出過牌才能質疑
        last_play = game_state.get("last_play")
        if last_play is not None and last_play.get("player_id") is not None and last_play.get("cards"):
            actions.append("challenge")

        return actions


class RuleBasedStrategy(Strategy):
    """基於規則的策略"""

    def decide_action(self, game_state: Dict, player: Player) -> Dict:
        # 確保 player 具有 hand 屬性
        if player is None or not hasattr(player, 'hand') or player.hand is None:
            return {"action": "skip", "cards": []}

        # 獲取可用的動作列表
        available_actions = self._get_available_actions(game_state, player)

        # 如果沒有可用的動作，直接返回跳過
        if not available_actions:
            return {"action": "skip", "cards": []}

        target_card = game_state["target_card"]

        # 計算手牌中的目標牌和Joker數量
        target_cards = [c for c in player.hand if c == target_card]
        jokers = [c for c in player.hand if c == "J"]

        # 檢查上一個玩家是否出過牌
        last_player_idx = None
        last_play_cards = []

        # 從 last_play 中獲取信息 (新的遊戲狀態格式)
        if "last_play" in game_state and game_state["last_play"] is not None:
            last_player_idx = game_state["last_play"]["player_id"]
            last_play_cards = game_state["last_play"]["cards"]
        # 也支持舊的格式 (直接在 game_state 中的字段)
        elif "last_player_idx" in game_state and game_state["last_player_idx"] is not None:
            last_player_idx = game_state["last_player_idx"]
            last_play_cards = game_state.get("last_play_cards", [])

        # 如果上一個玩家出了牌且質疑在可用動作中
        if last_player_idx is not None and last_play_cards and "challenge" in available_actions:
            # 如果上一個玩家出了很多牌，有較高概率質疑
            if len(last_play_cards) >= 2:
                import random
                if random.random() < 0.7:
                    return {"action": "challenge"}

            # 否則跳過 (只有當跳過是有效動作時)
            if "skip" in available_actions:
                return {"action": "skip"}

        # 如果出牌在可用動作中
        if "play" in available_actions:
            # 如果有目標牌，優先出這個
            if target_cards:
                # 決定出幾張
                num_to_play = min(len(target_cards), 3)
                return {"action": "play", "cards": target_cards[:num_to_play]}

            # 如果有Joker，可以出
            if jokers:
                return {"action": "play", "cards": jokers[:1]}

            # 如果沒有目標牌也沒有Joker，說謊
            if player.hand:
                # 盡量出少一點，減少被質疑的風險
                return {"action": "play", "cards": [player.hand[0]]}

        # 如果到這裡還沒有返回，選擇第一個可用動作
        if available_actions:
            if available_actions[0] == "play" and player.hand:
                return {"action": "play", "cards": [player.hand[0]]}
            return {"action": available_actions[0]}

        # 最後的後備選項
        return {"action": "skip"}

    def _get_available_actions(self, game_state: Dict, player: Player = None) -> List[str]:
        """獲取當前可用的動作列表"""
        actions = []

        # 根據規則，只有在玩家沒有手牌時才能跳過
        if player is not None and hasattr(player, 'hand') and not player.hand:
            actions.append("skip")
        else:
            # 有手牌時必須出牌
            actions.append("play")

        # 只有上家出過牌才能質疑
        last_play = game_state.get("last_play")
        if last_play is not None and last_play.get("player_id") is not None and last_play.get("cards"):
            actions.append("challenge")

        return actions


class LearningStrategy(Strategy):
    """學習型策略"""

    def __init__(self):
        super().__init__()
        self.player_models = {}  # 用於記錄其他玩家的行為模式

    def decide_action(self, game_state: Dict, player: Player) -> Dict:
        # 更新其他玩家的模型
        self._update_player_models(game_state)

        # 獲取可用的動作列表
        available_actions = self._get_available_actions(game_state, player)

        # 如果沒有可用的動作，直接返回跳過
        if not available_actions:
            return {"action": "skip", "cards": []}

        # 分析最佳行動
        action = self._analyze_best_action(
            game_state, player, available_actions)

        return action

    def _update_player_models(self, game_state: Dict):
        """更新其他玩家的行為模型"""
        # 通過分析玩家過去的行為來預測其策略
        # 這裡可以實現更複雜的學習算法
        pass

    def _analyze_best_action(self, game_state: Dict, player: Player, available_actions: List[str] = None) -> Dict:
        """分析最佳行動"""
        # 針對當前局勢，結合對其他玩家的建模，選擇最優的行動
        # 這裡使用簡化版，實際上可以結合更多因素

        # 先使用規則策略作為基礎
        rule_strategy = RuleBasedStrategy()
        return rule_strategy.decide_action(game_state, player)

    def _get_available_actions(self, game_state: Dict, player: Player = None) -> List[str]:
        """獲取當前可用的動作列表"""
        actions = []

        # 根據規則，只有在玩家沒有手牌時才能跳過
        if player is not None and hasattr(player, 'hand') and not player.hand:
            actions.append("skip")
        else:
            # 有手牌時必須出牌
            actions.append("play")

        # 只有上家出過牌才能質疑
        last_play = game_state.get("last_play")
        if last_play is not None and last_play.get("player_id") is not None and last_play.get("cards"):
            actions.append("challenge")

        return actions
