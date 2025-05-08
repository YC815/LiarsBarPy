import os
from pydantic import BaseModel
from typing import Literal, List
from openai import OpenAI
from string import Template
import json

# OpenAI.api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def ai_selection(player_number: int, round_count: int, play_history: str, self_hand: list, opinions_on_others: str, number_of_shots_fired: int):
    """
    AI遊戲選則
    Input: 玩家設定編號(int), 回合數(int), 過去出牌紀錄(str), 自己手牌(list), 對其他玩家的看法(str), 開槍次數(int)
    Output: AI選擇的行動(json)
    """

    def load_prompt(name):
        """
        載入提示詞
        檔內調用用
        Input: 提示詞名稱(str)
        Output: 提示詞內容(str)
        """
        with open(f"prompt/ai_selection/{name}.txt", "r", encoding="utf-8") as f:
            return f.read()

    # 載入玩家資訊
    with open(f"prompt/player/{player_number}.txt", "r", encoding="utf-8") as f:
        player = f.read()

    # 結構化輸出
    class OutputModel(BaseModel):
        action: Literal["play", "challenge"]
        played_cards: List[str]
        behavior: str
        play_reason: str
        challenge_reason: str

    # 呼叫AI
    completion = client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": load_prompt("system_intro")},
            {"role": "system", "content": load_prompt(
                "json_format_instruction")},
            {"role": "system", "content": load_prompt("field_description")},
            {"role": "system", "content": load_prompt("example_outputs")},
            {"role": "user", "content": Template(load_prompt("game_context_template")).substitute({
                "rules": load_prompt("rules"),
                "player_information": player,
                "round_count": round_count,
                "play_history": play_history,
                "self_hand": json.dumps(self_hand),
                "opinions_on_others": opinions_on_others,
                "number_of_shots_fired": number_of_shots_fired
            })}
        ],
        response_format=OutputModel
    )

    raw = completion.choices[0].message.content
    # 如果是字串，就先 load 成 dict
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"AI 回應 JSON 解析失敗：{e}\n原始回應：{raw}")
    else:
        data = raw

    # 再用 dict 初始化 Pydantic 模型
    result = OutputModel(**data)
    return result
