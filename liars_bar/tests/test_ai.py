#!/usr/bin/env python
# tests/test_ai.py
import unittest
from unittest.mock import patch, MagicMock
from liars_bar.ai.decision import AIDecisionMaker
from liars_bar.ai.strategy import RandomStrategy, RuleBasedStrategy
from liars_bar.ai.llm_manager import LLMManager
from liars_bar.models.player import Player, PlayerType
from liars_bar.core.game import Game


class TestAIStrategies(unittest.TestCase):
    """測試AI策略類"""

    def setUp(self):
        """每個測試前的初始化"""
        self.game = Game(num_players=4, debug=True)
        self.game_state = self.game.start()
        self.player = self.game.players[0]

    def test_random_strategy(self):
        """測試隨機策略"""
        strategy = RandomStrategy()
        decision = strategy.decide_action(self.game_state, self.player)

        # 檢查決策格式是否正確
        self.assertIn("action", decision)

        # 檢查動作是否是有效動作
        self.assertIn(decision["action"], [
                      "play", "challenge", "skip", "shoot"])

        # 如果是出牌動作，檢查牌
        if decision["action"] == "play":
            self.assertIn("cards", decision)

            # 如果有指定牌，確保這些牌在玩家手中
            if decision["cards"]:
                for card in decision["cards"]:
                    self.assertIn(card, self.player.hand)

    def test_rule_based_strategy(self):
        """測試基於規則的策略"""
        strategy = RuleBasedStrategy()

        # 修改遊戲狀態以測試不同情況
        # 1. 測試有目標牌的情況
        self.game.target_card = "A"
        self.player.hand = ["A", "A", "K", "Q"]
        decision = strategy.decide_action(self.game_state, self.player)

        # 應該選擇出牌，並且優先出目標牌
        self.assertEqual(decision["action"], "play")
        for card in decision["cards"]:
            self.assertEqual(card, "A")

        # 2. 測試只有Joker的情況
        self.player.hand = ["J", "K", "Q"]
        decision = strategy.decide_action(self.game_state, self.player)

        # 應該選擇出牌，出Joker
        self.assertEqual(decision["action"], "play")
        self.assertIn("J", decision["cards"])

        # 3. 測試需要說謊的情況
        self.player.hand = ["K", "Q"]
        decision = strategy.decide_action(self.game_state, self.player)

        # 應該選擇出牌，但會說謊
        self.assertEqual(decision["action"], "play")
        self.assertEqual(len(decision["cards"]), 1)  # 應該只出一張，減少風險


class TestLLMManager(unittest.TestCase):
    """測試LLM管理器"""

    @patch('liars_bar.ai.llm_manager.openai')
    def test_generate_response(self, mock_openai):
        """測試生成回應"""
        # 模擬OpenAI API回應
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '{"action": "play", "cards": ["A"], "reasoning": "測試"}'
        mock_openai.ChatCompletion.create.return_value = mock_response

        # 創建LLM管理器
        llm = LLMManager()

        # 測試生成回應
        response = llm.generate_response("測試提示詞")

        # 確認API被正確調用
        mock_openai.ChatCompletion.create.assert_called_once()

        # 確認回應內容
        self.assertEqual(
            response, '{"action": "play", "cards": ["A"], "reasoning": "測試"}')

    @patch('liars_bar.ai.llm_manager.LLMManager.generate_response')
    def test_generate_decision(self, mock_generate_response):
        """測試生成決策"""
        # 模擬LLM回應
        mock_generate_response.return_value = '{"action": "play", "cards": ["A"], "reasoning": "測試"}'

        # 創建遊戲狀態
        game = Game(num_players=4, debug=True)
        game_state = game.start()

        # 創建LLM管理器
        llm = LLMManager()

        # 測試生成決策
        decision = llm.generate_decision(game_state, 0)

        # 確認決策內容
        self.assertEqual(decision["action"], "play")
        self.assertEqual(decision["cards"], ["A"])
        self.assertEqual(decision["reasoning"], "測試")


class TestAIDecisionMaker(unittest.TestCase):
    """測試AI決策器"""

    def setUp(self):
        """每個測試前的初始化"""
        self.game = Game(num_players=4, debug=True)
        self.game_state = self.game.start()

    @patch('liars_bar.ai.strategy.RandomStrategy.decide_action')
    def test_make_decision_with_random_strategy(self, mock_decide_action):
        """測試使用隨機策略進行決策"""
        # 模擬策略回應
        mock_decide_action.return_value = {"action": "play", "cards": ["A"]}

        # 創建決策器
        decision_maker = AIDecisionMaker(strategy_type="random")

        # 測試決策
        action, cards = decision_maker.make_decision(self.game_state, 0)

        # 確認決策內容
        self.assertEqual(action, "play")
        self.assertEqual(cards, ["A"])


if __name__ == "__main__":
    unittest.main()
