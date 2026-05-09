import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types
from .prompts import get_gemini_prompt

# Chỉ định rõ đường dẫn file .env để tránh trỏ nhầm chỗ
from pathlib import Path
env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=env_path)

API_KEY = os.getenv("GEMINI_API_KEY")

# In ra để kiểm tra (chỉ in 4 ký tự đầu để bảo mật)
if API_KEY:
    print(f"--- [DEBUG] Đã nạp API Key: {API_KEY[:4]}... ---")
else:
    print("--- [DEBUG] KHÔNG tìm thấy API Key trong file .env! ---")

if not API_KEY:
    raise ValueError("Vui lòng cung cấp GEMINI_API_KEY trong file .env")

client = genai.Client(api_key=API_KEY)

async def generate_code_and_explanation(user_query: str) -> dict:
    prompt = get_gemini_prompt(user_query)
    try:
        response = await client.aio.models.generate_content(
            model='gemini-3-flash-preview',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
            ),
        )
        return json.loads(response.text)
    except Exception as e:
        # Trả về lỗi chi tiết để Streamlit hiển thị
        return {"error": str(e), "explanation": "Lỗi gọi AI API", "code": ""}