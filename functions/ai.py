from dotenv import load_dotenv
import os
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Literal
from enum import Enum
from string import Template
import json
from langchain.chains import LLMChain
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from collections import Counter
import ast
import random
from game.models.player import Player  # 添加 Player 類別的導入

# toggle debug here
DEBUG = False

# 載入環境變數
load_dotenv()

# 檢查 API key
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("請在 .env 檔案中設定 OPENAI_API_KEY")

# 定義提示模板
PROMPT_TEMPLATE = """你是一個在說謊者酒吧遊戲中的 AI 玩家。
你需要根據遊戲規則和當前情況做出決策。
請記住：
1. 不要暴露你的手牌
2. 保持策略性思考
3. 適時質疑其他玩家
4. 注意遊戲節奏和風險管理"""


class ActionEnum(str, Enum):
    play = 'play'
    pass_turn = 'pass'


class PlayerAction(BaseModel):
    player_number: int
    action: ActionEnum
    card_count: int = Field(description="Number of cards played")


class GameState(BaseModel):
    """遊戲狀態模型"""
    game_count: int
    target_card: str
    players: List[Player]
    play_history: List[Dict]
    player_insights: Dict
    last_played_cards: Optional[List[str]] = None

    class Config:
        arbitrary_types_allowed = True

# Example usage of structured output
# llm = ChatOpenAI(model="gpt-4o").with_structured_output(GameState)

# Existing function


def validate_played_cards(played_cards, self_hand, action="play"):
    # 如果是質疑動作，不需要驗證出牌
    if action == "challenge":
        return True, ""

    # 1. 出牌數必須介於 1~3 張
    if not (1 <= len(played_cards) <= 3):
        return False, "出牌張數不在 1~3 張範圍內"

    # 2. 出牌內容是否合法 (A, K, Q, J)
    valid_cards = {"A", "K", "Q", "J"}
    if not all(card in valid_cards for card in played_cards):
        return False, f"出現不合法的卡片: {played_cards}"

    # 3. 檢查是否超出手牌可出張數
    hand_counter = Counter(self_hand)
    play_counter = Counter(played_cards)
    for card, count in play_counter.items():
        if hand_counter[card] < count:
            return False, f"超出手牌數量: 嘗試出 {count} 張 {card}，但手牌中只有 {hand_counter[card]} 張"

    return True, ""


class AIResponse(BaseModel):
    """AI 回應的結構化模型"""
    action: Literal["play", "challenge"]
    played_cards: List[str] = Field(default_factory=list)
    behavior: str
    play_reason: str
    was_challenged: bool
    challenge_reason: str

    @validator('played_cards')
    def validate_played_cards(cls, v, values):
        if values.get('action') == 'play':
            if not 1 <= len(v) <= 3:
                raise ValueError('出牌數量必須在 1-3 張之間')
            if not all(card in ['A', 'K', 'Q', 'J'] for card in v):
                raise ValueError('只能出 A、K、Q、J 這四種牌')
        return v


def ai_selection_langchain(game_state: GameState, player_id: int, round_count: int) -> dict:
    """使用 LangChain 進行 AI 決策"""
    # 初始化 LLM
    llm = ChatOpenAI(
        model="gpt-4",
        temperature=0.7,
        api_key=os.getenv("OPENAI_API_KEY")
    )

    # 讀取遊戲提示模板
    with open("prompt/game_prompt.txt", "r", encoding="utf-8") as f:
        prompt_template = f.read()

    # 讀取當前回合記錄
    round_log = ""
    try:
        with open(f"log/game_{game_state.game_count}/rounds.md", "r", encoding="utf-8") as f:
            round_log = f.read()
    except FileNotFoundError:
        round_log = "尚未有回合記錄"

    # 準備輸入數據
    input_data = {
        "game_state": f"""
        目標牌: {game_state.target_card}
        當前玩家: {player_id}
        玩家手牌數量: {[len(p.hand) for p in game_state.players]}
        存活玩家: {[i for i, p in enumerate(game_state.players) if p.alive]}
        上一輪出牌: {game_state.last_played_cards if game_state.last_played_cards else '無'}
        """,
        "player_insights": f"""
        你對其他玩家的了解：
        {game_state.player_insights.get(player_id, '尚未有對其他玩家的了解')}
        """,
        "round_log": round_log,
        "round_count": round_count,
        "play_history": str(game_state.play_history),
        "self_hand": str(game_state.players[player_id].hand),
        "opinions_on_others": str(game_state.player_insights.get(player_id, {})),
        "number_of_shots_fired": game_state.players[player_id].shots_fired
    }

    # 設置輸出解析器
    output_parser = StructuredOutputParser.from_response_schemas([
        ResponseSchema(
            name="action", description="選擇的動作：'play' 或 'challenge'"),
        ResponseSchema(name="played_cards", description="要出的牌，如果是質疑則為空列表"),
        ResponseSchema(name="behavior", description="出牌或質疑時的表現"),
        ResponseSchema(name="play_reason", description="出牌或質疑的原因"),
        ResponseSchema(name="was_challenged", description="是否質疑上一位玩家"),
        ResponseSchema(name="challenge_reason", description="質疑或不質疑的原因")
    ])

    # 設置提示模板
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=prompt_template),
        HumanMessage(content=json.dumps(
            input_data, ensure_ascii=False, indent=2))
    ])

    # 設置輸出格式
    format_instructions = output_parser.get_format_instructions()

    # 重試機制
    max_retries = 5
    error_messages = []

    for attempt in range(max_retries):
        try:
            # 如果有之前的錯誤，加入提示中
            if error_messages:
                error_context = "\n\n之前的錯誤：\n" + "\n".join(error_messages)
                error_context += "\n請修正這些錯誤並重新做出決策。"
                input_data["error_context"] = error_context

            # 調用 LLM
            response = llm.invoke(prompt.format(
                format_instructions=format_instructions))

            # 解析回應
            result = output_parser.parse(response.content)

            # 使用 Pydantic 模型驗證
            validated_result = AIResponse(**result)

            # 驗證出牌合法性
            if validated_result.action == "play":
                is_valid, msg = validate_played_cards(
                    validated_result.played_cards,
                    game_state.players[player_id].hand,
                    validated_result.action
                )
                if not is_valid:
                    error_messages.append(f"嘗試 {attempt + 1}: {msg}")
                    continue

            return validated_result.dict()

        except Exception as e:
            error_messages.append(f"嘗試 {attempt + 1}: {str(e)}")
            if attempt == max_retries - 1:
                raise ValueError(
                    f"重試 {max_retries} 次後仍未得到有效回應。錯誤記錄：\n" +
                    "\n".join(error_messages)
                )
            continue


def _make_basic_decision(player_number: int, hand: List[str], target: str) -> Dict:
    """基本的 AI 決策邏輯，當 LLM 無法使用時的備用方案"""
    # 計算手牌中目標牌和王牌的數量
    target_count = hand.count(target)
    joker_count = hand.count('J')

    # 決定是否要質疑
    if random.random() < 0.3:  # 30% 機率質疑
        return {
            'action': 'challenge',
            'played_cards': [],
            'behavior': '懷疑地看著對方的出牌',
            'play_reason': '',
            'challenge_reason': '對方的出牌模式可疑'
        }

    # 決定出牌數量（1-3張）
    num_cards = min(random.randint(1, 3), len(hand))
    cards_to_play = []

    # 優先出目標牌和王牌
    for card in hand:
        if len(cards_to_play) >= num_cards:
            break
        if card in [target, 'J']:
            cards_to_play.append(card)

    # 如果還需要更多牌，從剩餘的牌中選擇
    remaining_cards = [card for card in hand if card not in cards_to_play]
    while len(cards_to_play) < num_cards and remaining_cards:
        cards_to_play.append(remaining_cards.pop(0))

    return {
        'action': 'play',
        'played_cards': cards_to_play,
        'behavior': '謹慎地出牌',
        'play_reason': '根據手牌狀況做出合理決策',
        'challenge_reason': ''
    }


def review_players(
    game_count: int,
    initial_review: dict,
    is_end_of_round: bool = False,  # 新增參數，判斷是否為大輪結束
    debug: bool = False
):
    # 1. 預先讀檔
    rules_txt = open("prompt/ai_selection/rules.txt", encoding="utf-8").read()
    template_txt = open("prompt/review.txt", encoding="utf-8").read()

    # 根據是否為大輪結束選擇不同的記錄來源
    if is_end_of_round:
        # 如果是大輪結束，讀取完整的 game_steps.md
        with open(f"log/round_{game_count}/game_steps.md", "r", encoding="utf-8") as f:
            game_log = f.read()
    else:
        # 如果是輪內整理，讀取 ai_round_context.md
        with open(f"log/round_{game_count}/ai_round_context.md", "r", encoding="utf-8") as f:
            game_log = f.read()

    player_txts = [
        open(f"prompt/player/{k}.txt", encoding="utf-8").read()
        for k in range(1, 4)  # 只讀取 AI 玩家 (1-3)
    ]

    # 2. 初始化 LangChain chain（只做一次）
    prompt = PromptTemplate(
        input_variables=[
            "rules",
            "player_information",
            "log",
            "review",
            "player_number",
            "other_player_number",
            "game_stepsmd"
        ],
        template=template_txt,
    )
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    chain = LLMChain(llm=llm, prompt=prompt)

    # 3. 迴圈呼叫
    output = {f"p{i}": {f"p{j}": None for j in range(
        4) if j != i} for i in range(4)}
    for i in range(1, 4):  # 跳過人類玩家 (player 0)
        for j in range(4):
            if i == j:
                continue

            payload = {
                "rules": rules_txt,
                # 調整索引，因為 player_txts 是從 0 開始的
                "player_information": player_txts[i-1],
                "log": game_log,
                "review": initial_review,
                "player_number": i,
                "other_player_number": j,
                "game_stepsmd": game_log  # 將 game_log 同時傳入 game_stepsmd 參數
            }
            if DEBUG or debug:
                print(f"\n>>> review_players INPUT for p{i} vs p{j} >>>")
                # 創建一個不包含 rules 和 player_information 的 payload 副本用於輸出
                debug_payload = payload.copy()
                debug_payload["rules"] = "[內容已省略]"
                debug_payload["player_information"] = "[內容已省略]"
                debug_payload["log"] = "[內容已省略]"
                print(json.dumps(debug_payload, ensure_ascii=False, indent=2))

            response = chain.run(payload)

            if DEBUG or debug:
                print(
                    f"\n<<< review_players RAW RESPONSE for p{i} vs p{j} <<<")
                print(response)

            output[f"p{i}"][f"p{j}"] = response.strip()

    # 將結果寫入檔案
    with open(f"log/round_{game_count}/player_summary.md", "w", encoding="utf-8") as f:
        f.write(json.dumps(output, ensure_ascii=False, indent=2))
    return output
