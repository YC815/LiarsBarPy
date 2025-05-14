from typing import List, Dict, Optional, Tuple
from models.player import Player
from .rules import Rules


class Action:
    """遊戲動作的基類"""

    def __init__(self, player_id: int):
        self.player_id = player_id

    def execute(self, game_state: Dict) -> Tuple[bool, str, Dict]:
        """執行動作，返回是否成功、訊息和更新後的遊戲狀態"""
        raise NotImplementedError("子類必須實現此方法")


class PlayCardsAction(Action):
    """出牌動作"""

    def __init__(self, player_id: int, cards: List[str]):
        super().__init__(player_id)
        self.cards = cards

    def execute(self, game_state: Dict) -> Tuple[bool, str, Dict]:
        player = game_state["players"][self.player_id]
        target_card = game_state["target_card"]

        # 驗證動作是否合法
        is_valid, message = Rules.validate_play_action(
            player, self.cards, target_card)
        if not is_valid:
            return False, message, game_state

        # 執行出牌動作
        if player.play_cards(self.cards):
            # 更新遊戲狀態
            new_game_state = game_state.copy()
            new_game_state["last_play_cards"] = self.cards
            new_game_state["last_player_idx"] = self.player_id
            new_game_state["current_player_idx"] = (
                self.player_id + 1) % len(game_state["players"])

            # 記錄玩家動作
            player.record_action("play", self.cards)

            return True, f"玩家 {self.player_id} 出牌：{self.cards}", new_game_state

        return False, "出牌失敗", game_state


class ChallengeAction(Action):
    """質疑動作"""

    def execute(self, game_state: Dict) -> Tuple[bool, str, Dict]:
        last_player_idx = game_state["last_player_idx"]
        last_play_cards = game_state["last_play_cards"]
        target_card = game_state["target_card"]

        # 驗證動作是否合法
        is_valid, message = Rules.validate_challenge_action(
            last_player_idx, last_play_cards)
        if not is_valid:
            return False, message, game_state

        # 檢查上家牌是否合法
        is_cheating = not all(card in [target_card, 'J']
                              for card in last_play_cards)

        # 確定要開槍的玩家
        shooter_idx = last_player_idx if is_cheating else self.player_id
        shooter = game_state["players"][shooter_idx]

        # 記錄質疑結果
        player = game_state["players"][self.player_id]
        if is_cheating:
            player.challenge_success += 1
        else:
            player.challenge_fail += 1

        # 記錄玩家動作
        player.record_action("challenge", success=is_cheating)

        # 進行俄羅斯輪盤
        hit = shooter.shoot()

        # 更新遊戲狀態
        new_game_state = game_state.copy()
        if hit or Rules.is_game_over(new_game_state["players"]):
            # 遊戲重置或結束
            new_game_state["game_over"] = Rules.is_game_over(
                new_game_state["players"])
            new_game_state["winner"] = Rules.get_winner(
                new_game_state["players"])

        # 更新下一位玩家
        if shooter.alive:
            new_game_state["current_player_idx"] = shooter_idx
        else:
            new_game_state["current_player_idx"] = (
                shooter_idx + 1) % len(game_state["players"])
            while not new_game_state["players"][new_game_state["current_player_idx"]].alive:
                new_game_state["current_player_idx"] = (
                    new_game_state["current_player_idx"] + 1) % len(game_state["players"])

        return True, f"質疑{'成功' if is_cheating else '失敗'}，玩家 {shooter_idx} {'中彈' if hit else '倖存'}", new_game_state


class SkipAction(Action):
    """跳過動作"""

    def execute(self, game_state: Dict) -> Tuple[bool, str, Dict]:
        last_play_cards = game_state["last_play_cards"]

        # 驗證動作是否合法
        is_valid, message = Rules.validate_skip_action(last_play_cards)
        if not is_valid:
            return False, message, game_state

        # 更新下一位玩家
        new_game_state = game_state.copy()
        new_game_state["current_player_idx"] = (
            self.player_id + 1) % len(game_state["players"])
        while not new_game_state["players"][new_game_state["current_player_idx"]].alive:
            new_game_state["current_player_idx"] = (
                new_game_state["current_player_idx"] + 1) % len(game_state["players"])

        # 記錄玩家動作
        game_state["players"][self.player_id].record_action("skip")

        return True, f"玩家 {self.player_id} 選擇跳過", new_game_state


class ShootAction(Action):
    """直接開槍動作"""

    def execute(self, game_state: Dict) -> Tuple[bool, str, Dict]:
        player = game_state["players"][self.player_id]

        # 驗證動作是否合法
        is_valid, message = Rules.validate_shoot_action()
        if not is_valid:
            return False, message, game_state

        # 進行俄羅斯輪盤
        hit = player.shoot()

        # 記錄玩家動作
        player.record_action("shoot", success=not hit)

        # 更新遊戲狀態
        new_game_state = game_state.copy()
        if hit or Rules.is_game_over(new_game_state["players"]):
            # 遊戲重置或結束
            new_game_state["game_over"] = Rules.is_game_over(
                new_game_state["players"])
            new_game_state["winner"] = Rules.get_winner(
                new_game_state["players"])

        # 更新下一位玩家
        if player.alive:
            new_game_state["current_player_idx"] = self.player_id
        else:
            new_game_state["current_player_idx"] = (
                self.player_id + 1) % len(game_state["players"])
            while not new_game_state["players"][new_game_state["current_player_idx"]].alive:
                new_game_state["current_player_idx"] = (
                    new_game_state["current_player_idx"] + 1) % len(game_state["players"])

        return True, f"玩家 {self.player_id} {'中彈' if hit else '倖存'}", new_game_state
