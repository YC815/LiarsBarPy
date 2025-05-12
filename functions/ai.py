import os
from pydantic import BaseModel
from typing import Literal, List
from openai import OpenAI
from string import Template
import json
from langchain.chains import LLMChain
from langchain_core.prompts import PromptTemplate
from langchain_community.chat_models import ChatOpenAI
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from collections import Counter
import ast

# toggle debug here
DEBUG = True

# OpenAI.api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def validate_played_cards(played_cards, self_hand):
    # 出牌數必須介於 1~3 張
    if not (1 <= len(played_cards) <= 3):
        return False, "出牌張數不在 1~3 張範圍內"

    # 出牌內容是否合法 (A, K, Q, J)
    valid_cards = {"A", "K", "Q", "J"}
    if not all(card in valid_cards for card in played_cards):
        return False, f"出現不合法的卡片: {played_cards}"

    # 檢查是否超出手牌可出張數（例如手上只有 1 張 K 卻出 2 張）
    hand_counter = Counter(self_hand)
    play_counter = Counter(played_cards)
    for card, count in play_counter.items():
        if hand_counter[card] < count:
            return False, f"超出手牌數量: 嘗試出 {count} 張 {card}，但手牌中只有 {hand_counter[card]} 張"

    return True, ""


def ai_selection_langchain(
    player_number: int,
    round_count: int,
    play_history: str,
    self_hand: list,
    opinions_on_others: dict,
    number_of_shots_fired: int,
    target: str,
    debug: bool = False,
):
    # 1. 定義 JSON 回傳欄位與說明
    response_schemas = [
        ResponseSchema(name="action", description="play 或 challenge"),
        ResponseSchema(name="played_cards", description="出牌清單，若質疑則空陣列"),
        ResponseSchema(name="behavior", description="表現描述，不帶主語"),
        ResponseSchema(name="play_reason", description="出牌策略理由；若質疑則空字串"),
        ResponseSchema(name="challenge_reason", description="質疑或不質疑原因"),
    ]
    parser = StructuredOutputParser.from_response_schemas(response_schemas)
    format_instructions = parser.get_format_instructions()

    # 2. 建立 LLMChain
    prompt = PromptTemplate(
        input_variables=[
            "game_rules", "player_info", "round_count", "player_number",
            "play_history", "self_hand", "opinions_on_others",
            "number_of_shots_fired", "target", "format_instructions"
        ],
        template="""\
遊戲規則與背景：  
{game_rules}
{player_info}

Round {round_count}，玩家編號：{player_number}  
過去出牌紀錄：{play_history}  
目前手牌：{self_hand}  
對其他玩家的看法：{opinions_on_others}  
已開槍次數：{number_of_shots_fired}
目標牌: {target}
過去歷史紀錄: {game_stepsmd}

請依照以下格式回傳 JSON：  
{format_instructions}
"""
    )
    chain = LLMChain(
        llm=ChatOpenAI(
            model="gpt-4o",
            temperature=0.3,
            max_tokens=512,    # optional: control your output length
        ),
        prompt=prompt
    )

    # 3. 重試機制
    max_retry = 5
    attempts = 0
    payload = {
        "game_rules": open("prompt/ai_selection/rules.txt", encoding="utf-8").read(),
        "player_info": open(f"prompt/player/{player_number}.txt", encoding="utf-8").read(),
        "round_count": round_count,
        "player_number": player_number,
        "play_history": play_history,
        "self_hand": self_hand,
        "opinions_on_others": opinions_on_others,
        "number_of_shots_fired": number_of_shots_fired,
        "target": target,
        "format_instructions": format_instructions,
        "game_stepsmd": open(f"log/round_{round_count}/game_steps.md", encoding="utf-8").read()

    }

    while True:
        # 呼叫 LLM 並印出完整回應
        raw_response = chain.run(payload)
        print(f"[LLM 原始回應 - 第 {attempts+1} 次]\n{raw_response}\n{'-'*40}")

        # 嘗試解析
        try:
            result = parser.parse(raw_response)
        except Exception as e:
            attempts += 1
            print(f"[解析失敗] 第 {attempts} 次: {e}")
            if attempts >= max_retry:
                raise ValueError(f"解析失敗超過 {max_retry} 次：{e}")
            continue

        # 如果是 challenge 直接回傳
        if result["action"] == "challenge":
            return result

        played = result["played_cards"]
        if isinstance(played, str):
            try:
                played = json.loads(played)
            except json.JSONDecodeError:
                played = ast.literal_eval(played)
        result["played_cards"] = played

        # 驗證 played_cards 的合法性
        is_valid, msg = validate_played_cards(
            result["played_cards"], self_hand)
        if is_valid:
            return result

        # 驗證不通過，重試
        attempts += 1
        print(f"[驗證失敗] 第 {attempts} 次: {msg}")
        if attempts >= max_retry:
            raise ValueError(f"重試 {max_retry} 次後仍未產出合法出牌：{msg}")
        # 迴圈繼續，LLM 再次 run


def review_players(
    game_count: int,
    initial_review: dict,
    debug: bool = False,          # <-- new parameter
):
    # 1. 預先讀檔
    rules_txt = open("prompt/ai_selection/rules.txt", encoding="utf-8").read()
    template_txt = open("prompt/review.txt", encoding="utf-8").read()
    game_log = open(
        f"log/round_{game_count}/game_steps.md", encoding="utf-8").read()
    player_txts = [
        open(f"prompt/player/{k}.txt", encoding="utf-8").read()
        for k in range(4)
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
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3, max_tokens=200)
    chain = LLMChain(llm=llm, prompt=prompt)

    # 3. 迴圈呼叫
    output = {f"p{i}": {f"p{j}": None for j in range(
        4) if j != i} for i in range(4)}
    for i in range(4):
        for j in range(4):
            if i == j:
                continue

            payload = {
                "rules": rules_txt,
                "player_information": player_txts[i],
                "log": game_log,
                "review": initial_review,
                "player_number": i,
                "other_player_number": j,
            }

            if DEBUG or debug:
                print(f"\n>>> review_players INPUT for p{i} vs p{j} >>>")
                print(json.dumps(payload, ensure_ascii=False, indent=2))

            response = chain.run(payload)

            if DEBUG or debug:
                print(
                    f"\n<<< review_players RAW RESPONSE for p{i} vs p{j} <<<")
                print(response)

            output[f"p{i}"][f"p{j}"] = response.strip()

    return output
