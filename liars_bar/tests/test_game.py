#!/usr/bin/env python
# tests/test_game.py
import unittest
from liars_bar.core.game import Game
from liars_bar.models.player import Player, PlayerType


class TestGame(unittest.TestCase):
    """測試遊戲核心邏輯"""

    def setUp(self):
        """每個測試前的初始化"""
        self.game = Game(num_players=4, debug=True)
        self.game.start()

    def test_game_initialization(self):
        """測試遊戲初始化"""
        # 測試玩家數量
        self.assertEqual(len(self.game.players), 4)

        # 測試手牌數量
        cards_per_player = 20 // 4  # 總牌數除以玩家數
        for player in self.game.players:
            self.assertEqual(len(player.hand), cards_per_player)

        # 測試遊戲狀態
        self.assertEqual(self.game.current_idx, 0)
        self.assertEqual(self.game.round_count, 1)
        self.assertIn(self.game.target_card, ["A", "K", "Q"])

    def test_play_action(self):
        """測試出牌動作"""
        # 給第一個玩家一些牌
        self.game.players[0].hand = ["A", "A", "K", "Q"]

        # 測試有效出牌
        result = self.game.next("play", ["A"])
        self.assertTrue(result["success"])
        self.assertEqual(len(self.game.players[0].hand), 3)
        self.assertEqual(self.game.last_play_cards, ["A"])

        # 測試無效出牌 (出超過3張)
        self.game.current_idx = 0  # 重置為第一個玩家
        result = self.game.next("play", ["A", "K", "Q", "J"])
        self.assertFalse(result["success"])

    def test_challenge_action(self):
        """測試質疑動作"""
        # 設置上一個玩家的出牌
        self.game.players[0].hand = ["A", "K", "Q"]
        self.game.target_card = "A"

        # 第一個玩家出牌
        self.game.next("play", ["Q"])  # 說謊

        # 第二個玩家質疑
        result = self.game.next("challenge")
        self.assertTrue(result["success"])

        # 確認質疑成功後，第一個玩家應該開槍
        self.assertNotEqual(self.game.current_idx, 1)

    def test_skip_action(self):
        """測試跳過動作"""
        # 設置上一個玩家的出牌
        self.game.players[0].hand = ["A", "K", "Q"]
        self.game.next("play", ["A"])

        # 第二個玩家跳過
        result = self.game.next("skip")
        self.assertTrue(result["success"])
        self.assertEqual(self.game.current_idx, 2)  # 應該到第三個玩家了

    def test_shoot_action(self):
        """測試開槍動作"""
        # 記錄開槍前的子彈位置
        player = self.game.players[self.game.current_idx]
        old_gun_pos = player.gun_pos

        # 執行開槍
        result = self.game.next("shoot")
        self.assertTrue(result["success"])

        # 確認槍已經轉動
        new_gun_pos = player.gun_pos
        self.assertEqual(new_gun_pos, (old_gun_pos % 6) + 1)

    def test_game_over(self):
        """測試遊戲結束條件"""
        # 殺死除了一個玩家以外的所有玩家
        for i in range(1, len(self.game.players)):
            self.game.players[i].alive = False

        # 檢查遊戲是否結束
        self.assertTrue(self.game.is_game_over())

        # 檢查勝利者
        winner = self.game.get_winner()
        self.assertEqual(winner, 0)


if __name__ == "__main__":
    unittest.main()
