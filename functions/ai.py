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

# toggle debug here
DEBUG = True

# OpenAI.api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def ai_selection_langchain(
    player_number: int,
    round_count: int,
    play_history: str,
    self_hand: list,
    opinions_on_others: dict,
    number_of_shots_fired: int,
    target: str,
    debug: bool = False,          # <-- new parameter

):
    # 1. 定義 JSON 回傳的欄位與說明
    response_schemas = [
        ResponseSchema(name="action", description="play 或 challenge"),
        ResponseSchema(name="played_cards", description="出牌清單，若質疑則空陣列"),
        ResponseSchema(name="behavior", description="表現描述，不帶主語"),
        ResponseSchema(name="play_reason", description="出牌策略理由；若質疑則空字串"),
        ResponseSchema(name="challenge_reason", description="質疑或不質疑原因"),
    ]
    parser = StructuredOutputParser.from_response_schemas(response_schemas)
    format_instructions = parser.get_format_instructions()

    # 2. 建立 PromptTemplate
    template = """\
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
    prompt = PromptTemplate(
        input_variables=[
            "game_rules",
            "round_count",
            "player_number",
            "play_history",
            "self_hand",
            "opinions_on_others",
            "number_of_shots_fired",
            "format_instructions",
        ],
        template=template,
    )

    # 3. 建立 LLMChain
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    chain = LLMChain(llm=llm, prompt=prompt)

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
        "game_stepsmd": open(f"log/round_{round_count}/game_steps.md", encoding="utf-8").read(),
        "format_instructions": format_instructions,
    }

    if DEBUG or debug:
        print("=== ai_selection_langchain INPUT ===")
        print(json.dumps(payload, ensure_ascii=False, indent=2))

    # 4. 執行並解析
    raw_response = chain.run(payload)

    if DEBUG or debug:
        print("=== ai_selection_langchain RAW RESPONSE ===")
        print(raw_response)

    result = parser.parse(raw_response)
    return result


def review_players(
    game_count: int,
    initial_review: dict,
    debug: bool = False,          # <-- new parameter
):
    # 1. 預先讀檔
    rules_txt = open("prompt/rules.txt", encoding="utf-8").read()
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
