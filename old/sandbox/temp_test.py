from dotenv import load_dotenv
import os
from openai import OpenAI

# 載入 .env 並從環境變數讀取金鑰
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 送出 Chat 完成請求
response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "user", "content": "我最喜歡的動物是"}
    ],
    max_tokens=200,
    temperature=1.4
)

# 取回並印出回覆內容
print(response.choices[0].message.content)
