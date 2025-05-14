import os
import json
from datetime import datetime
from dataclasses import dataclass, asdict
import markdown
from typing import List, Optional, Dict
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from string import Template


@dataclass
class PlayerAction:
    """玩家動作記錄"""
    player_id: int
    action_type: str  # 'play' 或 'challenge'
    cards_played: List[str]
    cards_remaining: List[str]
    shots_fired: int
    behavior: str
    strategy: Optional[str] = None
    bullet_pos: Optional[int] = None


@dataclass
class RoundLog:
    """回合記錄"""
    round_number: int
    target_card: str
    actions: List[PlayerAction]
    timestamp: str


@dataclass
class PlayerImpression:
    """玩家印象"""
    observer_id: int
    target_id: int
    impression: str
    confidence: float
    key_observations: List[str]
    impression_changes: str
    timestamp: str


class GameLogger:
    def __init__(self, game_count: int):
        self.game_count = game_count
        self.current_round = 1
        self.round_logs: List[RoundLog] = []
        self.target_card = ""
        # 格式: "p{observer_id}-p{target_id}"
        self.player_impressions: Dict[str, PlayerImpression] = {}

        # 建立必要的目錄
        self._create_directories()

    def _create_directories(self):
        """建立必要的目錄結構"""
        os.makedirs(f"log/game_{self.game_count}", exist_ok=True)

        # 初始化三個主要日誌檔案
        self._init_log_files()

    def _init_log_files(self):
        """初始化三個主要日誌檔案"""
        # 回合內日誌
        with open(f"log/game_{self.game_count}/rounds.md", "w", encoding="utf-8") as f:
            f.write("# 回合內日誌\n\n")

        # 玩家視角日誌
        with open(f"log/game_{self.game_count}/player_perspective.md", "w", encoding="utf-8") as f:
            f.write("# 玩家視角日誌\n\n")

        # 上帝視角日誌
        with open(f"log/game_{self.game_count}/god_perspective.md", "w", encoding="utf-8") as f:
            f.write("# 上帝視角日誌\n\n")

    def log_action(self,
                   player_id: int,
                   action_type: str,
                   cards_played: List[str],
                   cards_remaining: List[str],
                   shots_fired: int,
                   behavior: str,
                   strategy: Optional[str] = None,
                   bullet_pos: Optional[int] = None):
        """記錄玩家動作"""
        action = PlayerAction(
            player_id=player_id,
            action_type=action_type,
            cards_played=cards_played,
            cards_remaining=cards_remaining,
            shots_fired=shots_fired,
            behavior=behavior,
            strategy=strategy,
            bullet_pos=bullet_pos
        )

        # 如果這是新回合的第一個動作，創建新的回合記錄
        if not self.round_logs or self.round_logs[-1].round_number != self.current_round:
            self.round_logs.append(RoundLog(
                round_number=self.current_round,
                target_card="",  # 這個會在之後更新
                actions=[],
                timestamp=datetime.now().isoformat()
            ))

        self.round_logs[-1].actions.append(action)

        # 立即寫入所有視角的日誌
        self._write_all_logs()

    def update_target_card(self, target_card: str):
        """更新當前回合的目標牌"""
        self.target_card = target_card  # 更新 target_card 屬性
        if self.round_logs:
            self.round_logs[-1].target_card = target_card
            self._write_all_logs()

    def generate_player_impressions(self):
        """根據玩家視角日誌生成或更新玩家印象"""
        # 初始化 LLM
        llm = ChatOpenAI(temperature=0.7)

        # 讀取玩家視角日誌，但只讀取最後 5 個回合
        with open(f"log/game_{self.game_count}/player_perspective.md", "r", encoding="utf-8") as f:
            log_content = f.read()

        # 只保留最後 5 個回合的內容
        rounds = log_content.split("## 回合")
        if len(rounds) > 5:
            recent_rounds = rounds[-5:]
            log_content = "## 回合" + "## 回合".join(recent_rounds)

        # 簡化提示模板
        template = """分析以下遊戲日誌，生成玩家 {observer_id} 對玩家 {target_id} 的印象。

遊戲日誌：
{log_content}

{existing_impression}

請以 JSON 格式輸出：
- impression: 印象描述（200字以內）
- confidence: 確信度（0-1）
- key_observations: 關鍵觀察點（最多3點）
- impression_changes: 與之前印象的變化
"""
        prompt = ChatPromptTemplate.from_template(template)

        # 分批處理玩家組合
        player_combinations = []
        for observer_id in range(1, 4):
            for target_id in range(4):
                if observer_id != target_id:
                    player_combinations.append((observer_id, target_id))

        # 每次處理 3 個組合
        batch_size = 3
        for i in range(0, len(player_combinations), batch_size):
            batch = player_combinations[i:i + batch_size]
            for observer_id, target_id in batch:
                # 獲取現有印象
                key = f"p{observer_id}-p{target_id}"
                existing_impression = self.player_impressions.get(key)
                existing_impression_text = ""
                if existing_impression:
                    existing_impression_text = f"""
現有印象：
- 印象：{existing_impression.impression}
- 確信度：{existing_impression.confidence:.2f}
- 關鍵觀察：{', '.join(existing_impression.key_observations)}
- 時間：{existing_impression.timestamp}
"""

                try:
                    # 生成印象
                    response = llm.invoke(prompt.format_messages(
                        log_content=log_content,
                        existing_impression=existing_impression_text,
                        observer_id=observer_id,
                        target_id=target_id
                    ))

                    # 解析回應
                    impression_data = json.loads(response.content)
                    impression = PlayerImpression(
                        observer_id=observer_id,
                        target_id=target_id,
                        impression=impression_data["impression"],
                        confidence=impression_data["confidence"],
                        key_observations=impression_data.get(
                            "key_observations", []),
                        impression_changes=impression_data.get(
                            "impression_changes", ""),
                        timestamp=datetime.now().isoformat()
                    )

                    # 儲存印象
                    self.player_impressions[key] = impression
                    self._write_player_impression(impression)
                except Exception as e:
                    print(f"生成玩家印象時發生錯誤: {e}")

    def _write_player_impression(self, impression: PlayerImpression):
        """寫入玩家印象到日誌"""
        impression_content = f"""
### 玩家 {impression.observer_id} 對玩家 {impression.target_id} 的印象
- 印象: {impression.impression}
- 確信度: {impression.confidence:.2f}
- 關鍵觀察:
{chr(10).join([f"  - {obs}" for obs in impression.key_observations])}
"""
        if impression.impression_changes:
            impression_content += f"- 印象變化: {impression.impression_changes}\n"

        impression_content += f"- 時間: {impression.timestamp}\n"

        # 寫入到玩家視角日誌
        with open(f"log/game_{self.game_count}/player_perspective.md", "a", encoding="utf-8") as f:
            f.write(impression_content)

    def get_player_impressions(self, player_id: int) -> List[PlayerImpression]:
        """獲取指定玩家對其他玩家的印象"""
        impressions = []
        for target_id in range(4):
            if target_id != player_id:
                key = f"p{player_id}-p{target_id}"
                if key in self.player_impressions:
                    impressions.append(self.player_impressions[key])
        return impressions

    def format_impressions_for_ai(self, player_id: int) -> str:
        """格式化指定玩家的印象，用於 AI 決策"""
        impressions = self.get_player_impressions(player_id)
        if not impressions:
            return "目前還沒有對其他玩家的印象。"

        formatted = "對其他玩家的印象：\n"
        for imp in impressions:
            formatted += f"\n對玩家 {imp.target_id} 的印象：\n"
            formatted += f"- 印象：{imp.impression}\n"
            formatted += f"- 確信度：{imp.confidence:.2f}\n"
            formatted += f"- 關鍵觀察：\n"
            for obs in imp.key_observations:
                formatted += f"  * {obs}\n"
            if imp.impression_changes:
                formatted += f"- 印象變化：{imp.impression_changes}\n"

        return formatted

    def next_round(self):
        """進入下一輪"""
        # 在進入下一輪之前，生成當前回合的玩家印象
        self.generate_player_impressions()

        self.current_round += 1
        new_round = RoundLog(
            round_number=self.current_round,
            target_card=self.target_card,
            timestamp=datetime.now().isoformat(),
            actions=[]
        )
        self.round_logs.append(new_round)

        # 寫入新回合的標題和目標牌
        round_header = f"\n## 回合 {self.current_round}\n"
        round_header += f"目標牌: {self.target_card}\n"
        round_header += f"時間: {new_round.timestamp}\n\n"

        # 寫入回合內日誌
        with open(f"log/game_{self.game_count}/rounds.md", "a", encoding="utf-8") as f:
            f.write(round_header)

        # 寫入玩家視角日誌
        with open(f"log/game_{self.game_count}/player_perspective.md", "a", encoding="utf-8") as f:
            f.write(round_header)

        # 寫入上帝視角日誌
        with open(f"log/game_{self.game_count}/god_perspective.md", "a", encoding="utf-8") as f:
            f.write(round_header)

    def _write_all_logs(self):
        """寫入所有視角的日誌"""
        self._write_round_log()
        self._write_player_perspective_log()
        self._write_god_perspective_log()

    def _write_round_log(self):
        """寫入回合內日誌（簡化版）"""
        if not self.round_logs:
            return

        current_round = self.round_logs[-1]
        log_content = [
            f"\n## 回合 {current_round.round_number}",
            f"目標牌: {current_round.target_card}",
            f"時間: {current_round.timestamp}",
            "\n### 玩家動作"
        ]

        for action in current_round.actions:
            log_content.extend([
                f"\n#### 玩家 {action.player_id}",
                f"- 動作: {action.action_type}",
                f"- 出牌: {action.cards_played}",
                f"- 開槍次數: {action.shots_fired}",
                f"- 表現: {action.behavior}"
            ])

        file_path = f"log/game_{self.game_count}/rounds.md"
        with open(file_path, "a", encoding="utf-8") as f:
            f.write("\n".join(log_content))

    def _write_player_perspective_log(self):
        """寫入玩家視角日誌"""
        if not self.round_logs:
            return

        current_round = self.round_logs[-1]
        log_content = [
            f"\n## 回合 {current_round.round_number}",
            f"目標牌: {current_round.target_card}",
            f"時間: {current_round.timestamp}",
            "\n### 玩家動作"
        ]

        for action in current_round.actions:
            log_content.extend([
                f"\n#### 玩家 {action.player_id}",
                f"- 動作: {action.action_type}",
                f"- 出牌: {action.cards_played}",
                f"- 剩餘手牌: {action.cards_remaining}",
                f"- 開槍次數: {action.shots_fired}",
                f"- 表現: {action.behavior}",
                f"- 策略: {action.strategy or '無'}"
            ])

        file_path = f"log/game_{self.game_count}/player_perspective.md"
        with open(file_path, "a", encoding="utf-8") as f:
            f.write("\n".join(log_content))

    def _write_god_perspective_log(self):
        """寫入上帝視角日誌"""
        if not self.round_logs:
            return

        current_round = self.round_logs[-1]
        log_content = [
            f"\n## 回合 {current_round.round_number}",
            f"目標牌: {current_round.target_card}",
            f"時間: {current_round.timestamp}",
            "\n### 玩家動作"
        ]

        for action in current_round.actions:
            log_content.extend([
                f"\n#### 玩家 {action.player_id}",
                f"- 動作: {action.action_type}",
                f"- 出牌: {action.cards_played}",
                f"- 剩餘手牌: {action.cards_remaining}",
                f"- 開槍次數: {action.shots_fired}",
                f"- 表現: {action.behavior}",
                f"- 策略: {action.strategy or '無'}",
                f"- 子彈位置: {action.bullet_pos or '未知'}"
            ])

        file_path = f"log/game_{self.game_count}/god_perspective.md"
        with open(file_path, "a", encoding="utf-8") as f:
            f.write("\n".join(log_content))

    def get_round_context(self, round_number: int) -> str:
        """獲取指定回合的上下文（用於 AI 決策）"""
        if not self.round_logs or round_number > len(self.round_logs):
            return ""

        round_log = self.round_logs[round_number - 1]
        context = [
            f"回合 {round_number}",
            f"目標牌: {round_log.target_card}",
            "\n玩家動作:"
        ]

        for action in round_log.actions:
            context.extend([
                f"\n玩家 {action.player_id}:",
                f"- 動作: {action.action_type}",
                f"- 出牌: {action.cards_played}",
                f"- 表現: {action.behavior}"
            ])

        return "\n".join(context)


def init():
    """初始化記錄環境"""
    # 讀取當前局數
    with open("log/game_info.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    data["game_count"] += 1           # 修改記憶體中的值
    game_count = data["game_count"]  # 保留原始值

    # 寫入更新過的 JSON
    with open("log/game_info.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    # 建立新的遊戲目錄
    os.makedirs(f"log/game_{game_count}", exist_ok=True)

    return game_count


def log_round_summary(game_count: int, round_count: int, players: list, rivew: dict, shooting_count: list, bullet_position: list, question: list, liar: list, target: str, p0_hand_card: list, p1_hand_card: list, p2_hand_card: list, p3_hand_card: list):
    """
    記錄回合資訊
    Input: 局數(int), 回合數(int), 存活者(list), 回顧訊息(dict), 開槍次數(list), 子彈位置(list), 質疑次數(list), 被質疑次數(list), 目標牌(str), 玩家手牌(list)
    Output: 無
    """
    with open("log/example/round_summary.md", "r", encoding="utf-8") as f:
        example = f.read()
    record = Template(example).substitute({
        "game_count": game_count,
        "round_count": round_count,
        "player_list": players,
        "p0_to_p1": rivew["p0"]["p1"],
        "p0_to_p2": rivew["p0"]["p2"],
        "p0_to_p3": rivew["p0"]["p3"],
        "p1_to_p0": rivew["p1"]["p0"],
        "p1_to_p2": rivew["p1"]["p2"],
        "p1_to_p3": rivew["p1"]["p3"],
        "p2_to_p0": rivew["p2"]["p0"],
        "p2_to_p1": rivew["p2"]["p1"],
        "p2_to_p3": rivew["p2"]["p3"],
        "p3_to_p0": rivew["p3"]["p0"],
        "p3_to_p1": rivew["p3"]["p1"],
        "p3_to_p2": rivew["p3"]["p2"],
        "p0_shoot_count": shooting_count[0],
        "p1_shoot_count": shooting_count[1],
        "p2_shoot_count": shooting_count[2],
        "p3_shoot_count": shooting_count[3],
        "p0_bullet_pos": bullet_position[0],
        "p1_bullet_pos": bullet_position[1],
        "p2_bullet_pos": bullet_position[2],
        "p3_bullet_pos": bullet_position[3],
        "p0_question_count": question[0],
        "p1_question_count": question[1],
        "p2_question_count": question[2],
        "p3_question_count": question[3],
        "p0_liar_count": liar[0],
        "p1_liar_count": liar[1],
        "p2_liar_count": liar[2],
        "p3_liar_count": liar[3],
        "target": target,
        "p0_hand": p0_hand_card,
        "p0_shoot_count": shooting_count[0],
        "p1_hand": p1_hand_card,
        "p1_shoot_count": shooting_count[1],
        "p2_hand": p2_hand_card,
        "p2_shoot_count": shooting_count[2],
        "p3_hand": p3_hand_card,
        "p3_shoot_count": shooting_count[3]
    })
    with open(f"log/round_{game_count}/overview.md", "a", encoding="utf-8") as f:
        f.write("\n")
        f.write(record)


def log_player_action(game_count: int, player_number: int, is_play_card: bool, behavior: str, hand_cards: list, shoot_count: int, play_cards: Optional[List[str]] = None, play_reason: Optional[str] = None, challenge_reason: Optional[str] = None):
    """
    紀錄玩家行動
    Input: 局數(int), 玩家編號(int), 是否出牌(bool), 行為(str), 玩家手牌(list), 開槍次數(int), 出牌(list), 出牌原因(str), 質疑原因(str)
    Output: 無
    """
    if is_play_card == True:  # 出牌
        with open("log/example/player_play_step.md", "r", encoding="utf-8") as f:
            example = f.read()
        record = Template(example).substitute({
            "player_number": player_number,
            "play_cards": play_cards,
            "behavior": behavior,
            "play_reason": play_reason,
            "challenge_reason": challenge_reason or "",
            "hand_cards": hand_cards,
            "shoot_count": shoot_count
        })
    else:  # 質疑
        with open("log/example/player_challenge_step.md", "r", encoding="utf-8") as f:
            example = f.read()
        record = Template(example).substitute({
            "player_number": player_number,
            "behavior": behavior,
            "challenge_reason": challenge_reason,
            "hand_cards": hand_cards,
            "shoot_count": shoot_count
        })
    with open(f"log/round_{game_count}/overview.md", "a", encoding="utf-8") as f:
        f.write("\n")
        f.write(record)


def log_system_verdict(game_count: int, liar_state: bool, player: int, bullet_state: bool):
    """
    系統判決質疑
    Input: 局數(int), 質疑是否成功(bool), 玩家編號(int), 是否中彈(bool)
    Output: 無
    """
    with open("log/example/system_verdict.md", "r", encoding="utf-8") as f:
        example = f.read()
    record = Template(example).substitute({
        "liar_state": liar_state,
        "player": player,
        "bullet_state": bullet_state
    })
    with open(f"log/round_{game_count}/overview.md", "a", encoding="utf-8") as f:
        f.write("\n")
        f.write(record)
    with open(f"log/round_{game_count}/game_steps.md", "a", encoding="utf-8") as f:
        f.write("\n")
        f.write(record)
    with open(f"log/round_{game_count}/ai_round_context.md", "a", encoding="utf-8") as f:
        f.write("\n")
        f.write(record)


def log_game_end_summary(game_count: int, winner: str, player_rounds: list, player_challenge: list, player_challenged: list, player_shoot: list):
    """
    紀錄遊戲結束資訊
    Input: 局數(int), 贏家(str), 玩家回合(list), 玩家質疑(list), 玩家被質疑(list), 玩家開槍(list)
    Output: 無
    """
    with open("log/example/game_end_summary.md", "r", encoding="utf-8") as f:
        example = f.read()
    record = Template(example).substitute({
        "winner": winner,
        "p0_rounds": player_rounds[0],
        "p0_challenge": player_challenge[0],
        "p0_challenged": player_challenged[0],
        "p0_shoot": player_shoot[0],
        "p1_rounds": player_rounds[1],
        "p1_challenge": player_challenge[1],
        "p1_challenged": player_challenged[1],
        "p1_shoot": player_shoot[1],
        "p2_rounds": player_rounds[2],
        "p2_challenge": player_challenge[2],
        "p2_challenged": player_challenged[2],
        "p2_shoot": player_shoot[2],
        "p3_rounds": player_rounds[3],
        "p3_challenge": player_challenge[3],
        "p3_challenged": player_challenged[3],
        "p3_shoot": player_shoot[3]
    })
    with open(f"log/round_{game_count}/overview.md", "a", encoding="utf-8") as f:
        f.write("\n")
        f.write(record)


def log_player_perspective(game_count: int, round_count: int, player: int, shoot_count: int, play_card_count: int, behavior: str):
    """
    無上帝視角record
    Input: 局數(int), 回合數(int), 玩家編號(int), 開槍次數(int), 出牌次數(int), 行為(str)
    Output: 無
    """
    with open("log/example/player_perspective.md", "r", encoding="utf-8") as f:
        example = f.read()
    record = Template(example).substitute({
        "game_count": game_count,
        "round_count": round_count,
        "player": player,
        "shoot_count": shoot_count,
        "play_card_count": play_card_count,
        "behavior": behavior
    })
    with open(f"log/round_{game_count}/player_summary.md", "a", encoding="utf-8") as f:
        f.write("\n")
        f.write(record)


def log_next_round_context(game_count: int, sum_round_count: int, player_list: list, p0_shoot_count: int, p1_shoot_count: int, p2_shoot_count: int, p3_shoot_count: int):
    """
    新回合前AI input
    Input: 局數(int), 回合數(int), 玩家編號(list), 開槍次數(int)
    Output: 無
    """
    with open("log/example/next_round_context_template.md", "r", encoding="utf-8") as f:
        example = f.read()
    with open(f"log/round_{game_count}/game_steps.md", "r", encoding="utf-8") as f:
        game_step = f.read()

    record = Template(example).substitute({
        "game_count": game_count,
        "sum_round_count": sum_round_count,
        "player_list": player_list,
        "p0_shoot_count": p0_shoot_count,
        "p1_shoot_count": p1_shoot_count,
        "p2_shoot_count": p2_shoot_count,
        "p3_shoot_count": p3_shoot_count,
        "game_step": game_step
    })
    with open(f"log/round_{game_count}/next_round_context.md", "a", encoding="utf-8") as f:
        f.write("\n")
        f.write(record)


def log_in_game_action(game_count: int, player_number: int, is_play_card: bool, behavior: str, hand_cards: list, shoot_count: int, play_cards: Optional[List[str]] = None, play_reason: Optional[str] = None, challenge_reason: Optional[str] = None):
    """
    紀錄玩家行動
    Input: 局數(int), 玩家編號(int), 是否出牌(bool), 行為(str), 玩家手牌(list), 開槍次數(int), 出牌(list), 出牌原因(str), 質疑原因(str)
    Output: 無
    """
    # 記錄到 game_steps.md
    if is_play_card == True:  # 出牌
        with open("log/example/in_game_play_step.md", "r", encoding="utf-8") as f:
            example = f.read()
        record = Template(example).substitute({
            "player_number": player_number,
            "play_cards": play_cards,
            "behavior": behavior,
            "play_reason": play_reason or "",
            "challenge_reason": challenge_reason or "",
            "shoot_count": shoot_count
        })

        # 同時記錄到 ai_round_context.md
        with open("log/example/round_context_in_game_play_step.md", "r", encoding="utf-8") as f:
            context_example = f.read()
        # 計算出牌數量
        card_count = len(play_cards) if play_cards else 0
        context_record = Template(context_example).substitute({
            "player_number": player_number,
            "card_count": card_count,  # 出牌數量
            "behavior": behavior,
            "challenge_reason": challenge_reason or "",
            "shoot_count": shoot_count
        })
    else:  # 質疑
        with open("log/example/in_game_challenge_step.md", "r", encoding="utf-8") as f:
            example = f.read()
        record = Template(example).substitute({
            "player_number": player_number,
            "behavior": behavior,
            "challenge_reason": challenge_reason or "",
            "shoot_count": shoot_count
        })
        # 質疑時直接使用相同的記錄
        context_record = record

    # 寫入 game_steps.md
    with open(f"log/round_{game_count}/game_steps.md", "a", encoding="utf-8") as f:
        f.write("\n")
        f.write(record)

    # 寫入 ai_round_context.md
    with open(f"log/round_{game_count}/ai_round_context.md", "a", encoding="utf-8") as f:
        f.write("\n")
        f.write(context_record)
