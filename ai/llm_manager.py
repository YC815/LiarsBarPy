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

        # 定義系統消息
        system_message = """你是一個說謊者酒吧遊戲中的AI玩家。你的目標是選擇最佳策略，包括何時出牌、質疑、跳過或開槍。
請分析當前遊戲局勢，評估風險，並做出合理的決策。請使用JSON格式返回你的決策，格式如下：
{
  "action": "play/challenge/skip/shoot",
  "played_cards": ["A", "K", "Q", "J"],  // 僅在選擇"play"動作時需要
  "behavior": "描述你的行為表現",
  "play_reason": "說明你做出這個決策的原因",
  "was_challenged": false,
  "challenge_reason": "說明你質疑或不質疑的原因"
}"""

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

        prompt += f"\n請基於以上信息，決定你的下一步行動。"

        return prompt
