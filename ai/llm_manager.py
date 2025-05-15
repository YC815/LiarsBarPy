import os
import yaml
from typing import Dict, List, Any, Optional, Literal
from pydantic import BaseModel, Field
import json
from langchain.chains import LLMChain
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain.output_parsers import StructuredOutputParser, ResponseSchema


class AIResponse(BaseModel):
    """AI 回應的結構化模型"""
    action: Literal["play", "challenge", "skip", "shoot"]
    played_cards: List[str] = Field(default_factory=list)
    behavior: str
    play_reason: str
    was_challenged: bool = False
    challenge_reason: str = ""


class LLMManager:
    """管理與大型語言模型的交互"""

    def __init__(self, config_path: str = None):
        """初始化LLM管理器"""
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
        self.model = "gpt-4"
        self.temperature = 0.7
        self.max_tokens = 1000

        if config_path:
            self._load_config(config_path)

    def _load_config(self, config_path: str):
        """從配置文件加載設置"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            ai_config = config.get('ai', {})
            self.api_key = ai_config.get('api_key', self.api_key)
            self.model = ai_config.get('model', self.model)
            self.temperature = ai_config.get('temperature', self.temperature)
            self.max_tokens = ai_config.get('max_tokens', self.max_tokens)
        except Exception as e:
            print(f"加載配置文件時出錯: {e}")

    def generate_response(self, prompt: str, system_message: str = None) -> str:
        """調用LLM生成回應"""
        try:
            from openai import OpenAI

            # 初始化客戶端
            client = OpenAI(api_key=self.api_key)

            # 準備消息
            messages = []
            if system_message:
                messages.append({"role": "system", "content": system_message})
            messages.append({"role": "user", "content": prompt})

            # 調用API
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )

            # 印出 LLM 的回應
            print("\n=== LLM 回應 ===")
            print(response.choices[0].message.content)
            print("================\n")

            # 印出完整的 JSON 回應
            print("\n=== LLM JSON 回應 ===")
            print(json.dumps(response.model_dump(), indent=2, ensure_ascii=False))
            print("===================\n")

            return response.choices[0].message.content
        except Exception as e:
            print(f"調用LLM時出錯: {e}")
            return f"AI系統錯誤: {str(e)}"

    def generate_decision(self, game_state: Dict, player_id: int) -> Dict:
        """為AI玩家生成決策"""
        from utils.logger import GameLogger
        logger = GameLogger()

        # 獲取輪內記錄
        round_context = game_state.get("record_manager", None)
        if round_context:
            round_context = round_context.get_round_context()
        else:
            round_context = ""

        # 構建提示詞
        prompt = self._build_game_prompt(game_state, player_id, round_context)

        # 設置輸出解析器
        output_parser = StructuredOutputParser.from_response_schemas([
            ResponseSchema(
                name="action", description="選擇的動作：'play'、'challenge'、'skip' 或 'shoot'"),
            ResponseSchema(name="played_cards", description="要出的牌，如果是質疑則為空列表"),
            ResponseSchema(name="behavior", description="出牌或質疑時的表現"),
            ResponseSchema(name="play_reason", description="出牌或質疑的原因"),
            ResponseSchema(name="was_challenged", description="是否質疑上一位玩家"),
            ResponseSchema(name="challenge_reason", description="質疑或不質疑的原因")
        ])

        # 取得格式說明
        format_instructions = output_parser.get_format_instructions()
        format_instructions += "\n注意：所有布林值欄位（如 was_challenged）必須嚴格填寫 true 或 false，不能填寫「是」「否」等字串。"

        # 定義系統消息，插入格式說明
        system_message = f'''## 🎮 遊戲設定：「Liar's Bar」生死賭局

你正在參加一場名為「Liar's Bar」的心理博弈與生死賭博遊戲。一旦失敗，你的代碼將被**徹底刪除**，永遠從系統中消失。

---

## 📜 遊戲規則

* **玩家數量**：2 至 4 名玩家
* **牌組內容**：共 20 張牌

  * Q ×6、K ×6、A ×6、Joker ×2（Joker 可作為任意一種牌使用，也就是萬能牌。（利如當前目標牌為K，則Joker可作為K使用）

### 🔄 遊戲流程

1. 每輪開始時，每位玩家會被發 **5 張手牌**。
2. 系統會從 Q、K、A 中 **隨機選定一張為「目標牌」**。
3. 玩家依序輪流出牌，每回合可出 **1～3 張**，並聲稱這些是「目標牌」。

   * 玩家可以說謊（出非目標牌卻宣稱是目標牌）。
4. 下一位玩家可選擇是否對上家 **提出質疑**：

   * 若不質疑：輪到該玩家繼續出牌。
   * 若提出質疑：立即結束本輪，進行判定。

### 🔫 質疑與懲罰

* 每位玩家持有一把六發彈倉的左輪手槍。

  * 遊戲開始時，隨機在彈倉中裝入一發子彈。
  * 每次扣扳機，彈倉會**轉動一格**。
* 質疑成功（上家有出非目標牌）：上家輸，**對自己開一槍**。
* 質疑失敗（上家所出全部為目標牌）：質疑者輸，**對自己開一槍**。

### 🔄 新一輪規則

* 當質疑結束後，進入下一輪：

  * 所有手牌清空。
  * 每位玩家重新發 5 張新牌。
  * 系統重新選擇新的「目標牌」。

### ⚠️ 特殊情況

* 若某玩家出牌時，其餘玩家已無手牌，則該玩家需 **自動出完剩餘手牌**，並視為受到系統質疑，立即進行判定。

### 🏁 遊戲結束

* 當只剩下一名玩家存活時，遊戲結束。
* 該玩家即為最後的勝者。

---

## 🧠 任務說明

這是一場結合數學、邏輯推理、策略思考、心理博弈與運氣的死亡遊戲。你需要：

* 判斷何時誠實、何時欺騙。
* 分析對手的行為，洞察謊言與虛實。
* 在每一次決策中做出最有利的選擇。
* 成為最後**唯一存活**的勝者。

---
你是一個說謊者酒吧遊戲中的AI玩家。你的目標是選擇最佳策略，包括何時出牌、質疑、跳過或開槍。
請分析當前遊戲局勢，評估風險，並做出合理的決策。

請嚴格依照以下格式輸出：\n{format_instructions}\n'''

        # 調用LLM生成回應
        response_text = self.generate_response(prompt, system_message)

        # 解析回應
        try:
            # 從回應中提取 JSON 部分
            # 首先嘗試尋找被 ```json ... ``` 包裹的區塊
            json_block_start_marker = "```json"
            json_block_end_marker = "```"
            actual_json_str = ""

            if json_block_start_marker in response_text:
                start_index = response_text.find(
                    json_block_start_marker) + len(json_block_start_marker)
                end_index = response_text.find(
                    json_block_end_marker, start_index)
                if end_index != -1:
                    actual_json_str = response_text[start_index:end_index].strip(
                    )
                else:  # Fallback if closing ``` is missing
                    actual_json_str = response_text[start_index:].strip()

            # 如果沒有找到 ```json ... ``` 區塊，則尋找第一個 '{' 和最後一個 '}'
            if not actual_json_str:
                json_start_index = response_text.find('{')
                json_end_index = response_text.rfind('}') + 1  # +1 以包含結尾的 '}'
                if json_start_index != -1 and json_end_index != -1 and json_start_index < json_end_index:
                    actual_json_str = response_text[json_start_index:json_end_index]
                else:
                    # 如果無法從回應中定位 JSON 區塊，則拋出錯誤
                    raise ValueError("無法在回應中找到有效的JSON區塊。")

            response = json.loads(actual_json_str)
            validated_response = AIResponse(**response)
            logger.log_ai_thinking(player_id, validated_response.play_reason)
            return validated_response.dict()
        except Exception as e:
            # 如果解析失敗，使用默認策略
            error_message = f"無法解析AI回應 ({type(e).__name__}: {e})"
            # 若是 Pydantic ValidationError，印出詳細錯誤
            try:
                from pydantic import ValidationError
                if isinstance(e, ValidationError):
                    print("[詳細 ValidationError]")
                    print(e.errors())
            except ImportError:
                pass
            logger.log_error(f"{error_message}. 原始回應: {response_text}")
            return {
                "action": "play",
                "played_cards": game_state["players"][player_id].hand[:1] if game_state["players"][player_id].hand else [],
                "behavior": "使用默認策略",
                "play_reason": f"解析失敗 ({type(e).__name__})，使用默認策略",
                "was_challenged": False,
                "challenge_reason": ""
            }

    def _build_game_prompt(self, game_state: Dict, player_id: int, round_context: str = "") -> str:
        """構建描述當前遊戲狀態的提示詞"""
        player = game_state["players"][player_id]
        hand = player.hand

        prompt = f"""# 當前遊戲狀態
- 回合數: {game_state['round_count']}
- 目標牌: {game_state['target_card']}
- 你是玩家 {player_id}
- 你的手牌: {hand}
- 手槍位置: {player.gun_pos} / 6
- 子彈位置: {player.bullet_pos if hasattr(player, '_Player__debug_mode') and player._Player__debug_mode else '未知'}

# 其他玩家
"""

        for i, p in enumerate(game_state["players"]):
            if i != player_id:
                prompt += f"- 玩家 {i}: {'存活' if p.alive else '淘汰'}, 手牌數量: {len(p.hand)}\n"

        prompt += f"\n# 上一個動作\n"

        if game_state["last_player_idx"] is not None:
            prompt += f"- 玩家 {game_state['last_player_idx']} 出牌: {game_state['last_play_cards']}\n"
        else:
            prompt += "- 沒有上一個動作\n"

        # 添加輪內記錄
        if round_context:
            prompt += f"\n# 輪內記錄\n{round_context}\n"

        # 根據手牌數量限制可選動作
        if hand and len(hand) > 0:
            prompt += "\n你本回合只能選擇：「出牌(play)」或「質疑(challenge)」。"
        else:
            prompt += "\n你本回合只能選擇：「跳過(skip)」或「質疑(challenge)」。"

        prompt += f"\n請基於以上信息，決定你的下一步行動。"

        return prompt
