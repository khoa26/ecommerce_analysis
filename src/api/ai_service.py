from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import sys
import json
import os
from datetime import datetime
from pathlib import Path

# Đảm bảo import được module từ thư mục cha
sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.ai_module.model_handler import generate_code_and_explanation

router = APIRouter(prefix="/ai", tags=["AI Generation"])

class AIRequest(BaseModel):
    query: str

class AIResponse(BaseModel):
    explanation: str
    code: str

def log_ai_activity(entry: dict):
    """Hàm dùng chung để ghi log vào file JSONL"""
    log_dir = Path(__file__).resolve().parents[2] / "data" / "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = log_dir / "ai_activity.jsonl"
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

@router.post("/generate", response_model=AIResponse)
async def generate_code(request: AIRequest):
    if not request.query:
        raise HTTPException(status_code=400, detail="Query không được để trống")
    
    result = await generate_code_and_explanation(request.query)
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
        
    # GHI LOG: Giai đoạn sinh mã
    log_ai_activity({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": "GENERATE",
        "user_query": request.query,
        "ai_explanation": result["explanation"],
        "generated_code": result["code"]
    })
        
    return AIResponse(
        explanation=result["explanation"],
        code=result["code"]
    )