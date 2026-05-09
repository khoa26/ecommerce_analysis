from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import sys
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

@router.post("/generate", response_model=AIResponse)
async def generate_code(request: AIRequest):
    """
    Nhận câu hỏi từ người dùng, gọi AI Model và trả về Code + Giải thích.
    Đoạn code này sẽ nằm ở trạng thái PENDING chờ người dùng duyệt trên Frontend.
    """
    if not request.query:
        raise HTTPException(status_code=400, detail="Query không được để trống")
    
    result = await generate_code_and_explanation(request.query)
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
        
    return AIResponse(
        explanation=result["explanation"],
        code=result["code"]
    )