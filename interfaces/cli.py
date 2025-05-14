import os
import time
from typing import Dict, List, Any
from models.player import PlayerType
from ai.decision import AIDecisionMaker


class GameCLI:
    """命令行遊戲界面"""

    def __init__(self, game, ai_strategy="rule", interactive_pause: bool = True):
        """初始化界面"""
        self.game = game
        self.ai_decision_maker = AIDecisionMaker(strategy_type=ai_strategy)
        self.interactive_pause = interactive_pause

    def display_game_status(self):
        """顯示當前遊戲狀態"""
        # 取得當前玩家
        current_player = self.game.players[self.game.current_idx]
        is_human = current_player.player_type == PlayerType.HUMAN

        # 顯示基本遊戲信息
        print("\n" + "="*20)
        print("說謊者酒吧")
        print("="*20)
        print(f"遊戲回合: {self.game.round_count}")
        print(f"目標牌: {self.game.target_card}")
        print(f"當前玩家: 玩家{self.game.current_idx}" +
              f"({'你' if is_human else 'AI'})")

        # 顯示存活玩家
        alive_players = [p.id for p in self.game.players if p.alive]
        print(f"存活玩家: {alive_players}")

        # 顯示上家出牌
        if self.game.last_player_idx is not None:
            print(
                f"上家(玩家{self.game.last_player_idx})出牌: {self.game.last_play_cards}")
        else:
            print("尚未有玩家出牌")

        # 如果是人類玩家，顯示手牌
        if is_human:
            print(f"\n你的手牌: {current_player.hand}")
            print(f"手槍位置: {current_player.gun_pos}/6")

            # 如果是調試模式，也顯示子彈位置
            if self.game.debug:
                print(f"子彈位置: {current_player.bullet_pos}")

        print("\n可執行動作:")
        actions = self.game._get_available_actions()
        for i, action in enumerate(actions):
            print(f"{i+1}. {self._translate_action(action)}")

        print("\n" + "="*20)

    def _translate_action(self, action: str) -> str:
        """將動作轉換為中文描述"""
        translations = {
            "play": "出牌",
            "challenge": "質疑",
            "skip": "跳過",
            "shoot": "開槍"
        }
        return translations.get(action, action)

    def get_player_action(self) -> Dict:
        """獲取玩家動作"""
        current_player = self.game.players[self.game.current_idx]

        # 如果是AI玩家，使用AI決策
        if current_player.player_type != PlayerType.HUMAN:
            return self._get_ai_action()

        # 如果是人類玩家，獲取用戶輸入
        actions = self.game._get_available_actions()
        valid_input = False

        while not valid_input:
            try:
                choice = int(input("\n請選擇動作 (輸入數字): ")) - 1
                if 0 <= choice < len(actions):
                    action = actions[choice]
                    valid_input = True
                else:
                    print("無效的選擇，請重新輸入")
            except ValueError:
                print("請輸入數字")

        # 根據動作獲取附加參數
        if action == "play":
            cards = self._get_cards_input(current_player.hand)
            return {"action": action, "played_cards": cards}
        else:
            return {"action": action}

    def _get_cards_input(self, hand: List[str]) -> List[str]:
        """獲取玩家要出的牌"""
        valid_input = False
        cards = []

        while not valid_input:
            cards_input = input("請選擇要出的牌 (如A K Q，以空格分隔): ").upper().split()

            # 檢查輸入的牌是否在手牌中
            if all(card in hand for card in cards_input):
                # 檢查數量是否合法
                if 1 <= len(cards_input) <= 3:
                    cards = cards_input
                    valid_input = True
                else:
                    print("出牌數量必須在1到3張之間")
            else:
                print("你沒有這些牌")

        return cards

    def _get_ai_action(self) -> Dict:
        """獲取AI玩家的決策"""
        game_state = self.game.get_game_state()
        player_id = self.game.current_idx

        # 顯示AI思考中
        print("\nAI思考中", end="")
        for _ in range(3):
            time.sleep(0.5)
            print(".", end="", flush=True)
        print("\n")

        # 獲取AI決策
        action, cards = self.ai_decision_maker.make_decision(
            game_state, player_id)

        # 顯示AI行為（非必要，但增加遊戲趣味性）
        if action == "play":
            behavior = self.ai_decision_maker.get_behavior(action, len(cards))
            print(f"AI {behavior}")
            return {"action": action, "played_cards": cards}
        else:
            behavior = self.ai_decision_maker.get_behavior(action)
            print(f"AI {behavior}")
            return {"action": action}

    def display_action_result(self, result: Dict):
        """顯示動作結果"""
        message = result.get('message', '動作執行完成')
        print(f"\n結果: {message}")
        if self.interactive_pause:
            input("\n按Enter繼續...")

    def display_game_result(self):
        """顯示遊戲結果"""
        self.clear_screen()

        print("\n===== 遊戲結束 =====")
        winner = self.game.get_winner()

        if winner is not None:
            print(f"勝利者: 玩家{winner}" +
                  f"({'你' if self.game.players[winner].player_type == PlayerType.HUMAN else 'AI'})")
        else:
            print("遊戲結束，沒有勝利者")

        print("\n" + "="*20)
        input("\n按Enter退出...")
