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

    # 2. 建立 PromptTemplate（加入 previous_errors 並明確禁止超出手牌）
    common_inputs = [
        "game_rules", "player_info", "round_count", "player_number",
        "play_history", "self_hand", "opinions_on_others",
        "number_of_shots_fired", "target", "format_instructions",
        "previous_errors", "game_stepsmd"
    ]
    common_template = """\
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

# 錯誤回饋（若為第一次則為「無」）：  
{previous_errors}

**請注意：不要超出手牌中卡片。**  
請依照以下格式回傳 JSON：  
{format_instructions}
"""
    # 若為玩家1，補充人類上家說明
    if player_number == 1:
        common_template = common_template.replace(
            "**請注意：不要超出手牌中卡片。**",
            "**請注意：您是玩家1，上家是玩家0（人類）；不要超出手牌中卡片。**"
        )

    prompt = PromptTemplate(
        input_variables=common_inputs,
        template=common_template
    )
    chain = LLMChain(
        llm=ChatOpenAI(
            model="gpt-4o",  # 溫度設為 0 提升確定性
            temperature=0.0,
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
        "game_stepsmd": open(f"log/round_{round_count}/ai_round_context.md", encoding="utf-8").read(),
        "previous_errors": "無"
    }

    error_messages = []  # 儲存錯誤訊息
    while attempts < max_retry:
        # 準備發送給 LLM 的資料
        llm_input = {
            **payload,
            "previous_errors": "\n".join([f"嘗試 {i+1}: {msg}" for i, msg in enumerate(error_messages)]) or "無"
        }
        if debug:
            print(f"\n[Debug] 第 {attempts+1} 次嘗試，錯誤回饋：{llm_input['previous_errors']}")

        raw_response = chain.run(llm_input)
        if debug:
            print(f"[LLM 原始回應 - 第 {attempts+1} 次]\n{raw_response}\n{'-'*40}")

        # 嘗試解析
        try:
            result = parser.parse(raw_response)
        except Exception as e:
            error_messages.append(f"解析失敗: {e}")
            attempts += 1
            continue

        # 若為 challenge，直接回傳
        if result.get("action") == "challenge":
            return result

        # 處理 played_cards 格式
        played = result.get("played_cards", [])
        if isinstance(played, str):
            # 嘗試解析字串格式
            import ast
            import re
            
            # 嘗試解析 JSON 格式（例如 "[\"K\", \"A\"]"）
            try:
                played = ast.literal_eval(played)
            except (ValueError, SyntaxError):
                # 嘗試解析其他可能的格式（例如 "K, A, A" 或 "K A A"）
                # 移除所有非字母和逗號的字符，然後分割
                cleaned = re.sub(r'[^a-zA-Z,]', '', played.upper())
                played = [card.strip() for card in cleaned.split(',') if card.strip()]
                
                # 如果還是空列表，嘗試按空格分割
                if not played and ' ' in played:
                    played = [card.strip() for card in played.split() if card.strip()]
                    
        # 確保 played 為 list 且每個元素都是字串
        if not isinstance(played, list):
            played = [played] if played else []
            
        # 確保所有卡片都是大寫字母
        played = [str(card).strip().upper() for card in played if str(card).strip()]
        result["played_cards"] = played

        # 驗證合法性
        is_valid, msg = validate_played_cards(played, self_hand)
        if is_valid:
            return result

        # 驗證失敗，加入錯誤回饋並重試
        error_messages.append(f"驗證失敗: {msg}")
        attempts += 1

    # 超過重試次數仍未合法
    raise ValueError(f"重試 {max_retry} 次後仍未產出合法出牌：{error_messages}")



def review_players(
    game_count: int,
    initial_review: dict,
    debug: bool = False,          # <-- new parameter
):
    # 1. 預先讀檔
    rules_txt = open("prompt/ai_selection/rules.txt", encoding="utf-8").read()
    template_txt = open("prompt/review.txt", encoding="utf-8").read()
    game_log = open(
        f"log/round_{game_count}/ai_round_context.md", encoding="utf-8").read()
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
                "player_information": player_txts[i-1],  # 調整索引，因為 player_txts 是從 0 開始的
                "log": game_log,
                "review": initial_review,
                "player_number": i,
                "other_player_number": j,
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
    with open(f"log/round_{game_count}/player_summary.md", "w", encoding="utf-8") as f:
        f.write(json.dumps(output, ensure_ascii=False, indent=2))
    return output
