from dataclasses import dataclass, field
from typing import List, Dict, Optional
from .player import Player


@dataclass
class GameState:
    """遊戲狀態類別，用於追蹤當前遊戲狀態"""
    players: List[Player]
    current_player_idx: int
    round_count: int
    game_count: int
    target_card: str
    last_play_cards: List[str] = field(default_factory=list)
    last_player_idx: Optional[int] = None
    play_history: List[Dict] = field(default_factory=list)
    game_over: bool = False
    winner: Optional[int] = None

    def to_dict(self) -> Dict:
        """將遊戲狀態轉換為字典形式"""
        return {
            "current_player_idx": self.current_player_idx,
            "round_count": self.round_count,
            "game_count": self.game_count,
            "target_card": self.target_card,
            "last_play_cards": self.last_play_cards,
            "last_player_idx": self.last_player_idx,
            "play_history": self.play_history,
            "players": [
                {
                    "id": player.id,
                    "player_type": player.player_type.value,
                    "hand_count": len(player.hand),
                    "alive": player.alive,
                    "gun_pos": player.gun_pos,
                    "shots_fired": player.shots_fired,
                } for player in self.players
            ],
            "game_over": self.game_over,
            "winner": self.winner
        }

    def get_player_view(self, player_id: int) -> Dict:
        """獲取特定玩家視角的遊戲狀態"""
        base_info = self.to_dict()

        # 只顯示當前玩家自己的手牌
        player_view = base_info.copy()
        player_hand = self.players[player_id].hand if player_id < len(
            self.players) else []
        player_view["hand"] = player_hand

        # 如果是調試模式，也可以添加額外信息
        # player_view["debug_info"] = {...}

        return player_view
