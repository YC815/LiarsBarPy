import os
from pydantic import BaseModel
from typing import Literal, List
from openai import OpenAI
from string import Template
import json
from langchain import LLMChain, PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.output_parsers import StructuredOutputParser, ResponseSchema

# OpenAI.api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def ai_selection_langchain(
    player_number: int,
    round_count: int,
    play_history: str,
    self_hand: list,
    opinions_on_others: str,
    number_of_shots_fired: int,
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

        Round {round_count}，玩家編號：{player_number}  
        過去出牌紀錄：{play_history}  
        目前手牌：{self_hand}  
        對其他玩家的看法：{opinions_on_others}  
        已開槍次數：{number_of_shots_fired}

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
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)  # 依需求調整
    chain = LLMChain(llm=llm, prompt=prompt)

    # 4. 執行並解析
    response = chain.run({
        "game_rules": open("prompt/rules.txt", encoding="utf-8").read(),
        "round_count": round_count,
        "player_number": player_number,
        "play_history": play_history,
        "self_hand": self_hand,
        "opinions_on_others": opinions_on_others,
        "number_of_shots_fired": number_of_shots_fired,
        "format_instructions": format_instructions,
    })
    result = parser.parse(response)
    return result


def rivew():
    review = {
        "p0": {"p1": "還不了解此名玩家。", "p2": "還不了解此名玩家。", "p3": "還不了解此名玩家。"},
        "p1": {"p0": "還不了解此名玩家。", "p2": "還不了解此名玩家。", "p3": "還不了解此名玩家。"},
        "p2": {"p0": "還不了解此名玩家。", "p1": "還不了解此名玩家。", "p3": "還不了解此名玩家。"},
        "p3": {"p0": "還不了解此名玩家。", "p1": "還不了解此名玩家。", "p2": "還不了解此名玩家。"}
    }
    with open("prompt/rivew.txt", "r", encoding="utf-8") as f:
        example = f.read()

    with open("prompt/ai_selection/rules.txt", "r", encoding="utf-8") as f:
        rules = f.read()

    for i in range(4):
        for j in range(4):
            if i == j:
                continue
            template = """\
                {rules}
                {player_information}

                這是上一輪遊戲的過程紀錄：
                {log}

                您作為玩家 {player_number}，
                請**以一個完整的中文段落**（不要分行、不要列點）回答，分析玩家 {other_player_number} 的人格特質、出牌想法、優缺點等，讓自己在下一輪能拿到最有用的情報。
                """
            prompt = PromptTemplate(
                input_variables=[
                    "rules",
                    "player_information",
                    "log",
                    "player_number",
                    "other_player_number"
                ],
                template=template,
            )

            llm = ChatOpenAI(
                model="gpt-4o",
                temperature=0.3,
                max_tokens=200,          # 最多 200 個 token，視需求調整
                # 或者：max_new_tokens=150
            )

            chain = LLMChain(llm=llm, prompt=prompt)

            response = chain.run({
                "rules": open("prompt/rules.txt", encoding="utf-8").read(),
                "player_information": open(f"prompt/player/{i}.txt", encoding="utf-8").read(),
                "log": game_log,
                "player_number": player_number,
                "other_player_number": other_player_number,
            })
            print(response)

            review[f"p{i}"][f"p{j}"] =
