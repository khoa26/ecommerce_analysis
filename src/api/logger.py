from fastapi import APIRouter, HTTPException
import os
import json
from pathlib import Path

router = APIRouter(prefix="/logs", tags=["System Logging"])

LOG_FILE_PATH = Path(__file__).resolve().parents[2] / "data" / "logs" / "ai_activity.jsonl"

@router.get("/history")
async def get_ai_logs(limit: int = 50):
    """
    API Logs: Đọc và trả về lịch sử các yêu cầu, mã nguồn, giải thích và kết quả.
    """
    if not os.path.exists(LOG_FILE_PATH):
        return {"status": "success", "data": []}
        
    logs = []
    try:
        # Đọc file JSONL từ dưới lên (lấy các log mới nhất)
        with open(LOG_FILE_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
            # Lấy số lượng theo limit
            recent_lines = lines[-limit:] if limit > 0 else lines
            for line in recent_lines:
                logs.append(json.loads(line.strip()))
                
        # Đảo ngược mảng để log mới nhất nằm trên cùng
        logs.reverse()
        return {"status": "success", "count": len(logs), "data": logs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi đọc file log: {str(e)}")