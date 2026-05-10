from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import sys
import os
import requests
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.ai_module.model_handler import generate_code_and_explanation

router = APIRouter(prefix="/ai", tags=["AI Generation"])

class AIRequest(BaseModel):
    query: str

class AIResponse(BaseModel):
    explanation: str
    code: str

def call_log_api(entry: dict):
    """Hàm thực hiện HTTP POST gọi sang API Logs"""
    try:
        # Gọi sang endpoint /logs/save ở cổng 8000
        requests.post("http://127.0.0.1:8000/logs/save", json=entry, timeout=3)
    except Exception as e:
        print(f"[Warning] Không thể gọi API Logs: {e}")

@router.post("/generate", response_model=AIResponse)
async def generate_code(request: AIRequest, background_tasks: BackgroundTasks):
    if not request.query:
        raise HTTPException(status_code=400, detail="Query không được để trống")
    
    result = await generate_code_and_explanation(request.query)
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
        
    # Tạo payload dữ liệu log
    log_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": "GENERATE",
        "user_query": request.query,
        "ai_explanation": result["explanation"],
        "generated_code": result["code"]
    }
    
    # Sử dụng BackgroundTasks để gọi API log ngầm, không làm người dùng phải chờ
    background_tasks.add_task(call_log_api, log_entry)
        
    return AIResponse(
        explanation=result["explanation"],
        code=result["code"]
    )