from fastapi import APIRouter, HTTPException, Body
import os
import json
from pathlib import Path
from typing import Dict, Any

router = APIRouter(prefix="/logs", tags=["System Logging"])

LOG_FILE_PATH = Path(__file__).resolve().parents[2] / "data" / "logs" / "ai_activity.jsonl"

@router.post("/save")
async def save_log(entry: Dict[str, Any] = Body(...)):
    """
    API Logs (Ghi): Nhận dữ liệu log từ các API khác thông qua HTTP POST và lưu vào file.
    """
    try:
        os.makedirs(LOG_FILE_PATH.parent, exist_ok=True)
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return {"status": "success", "message": "Đã lưu log thành công"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi ghi file log: {str(e)}")

@router.get("/history")
async def get_ai_logs(limit: int = 50):
    """
    API Logs (Đọc): Đọc và trả về lịch sử các yêu cầu, mã nguồn, giải thích và kết quả.
    """
    if not os.path.exists(LOG_FILE_PATH):
        return {"status": "success", "data": []}
        
    logs = []
    try:
        with open(LOG_FILE_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
            recent_lines = lines[-limit:] if limit > 0 else lines
            for line in recent_lines:
                logs.append(json.loads(line.strip()))
                
        logs.reverse()
        return {"status": "success", "count": len(logs), "data": logs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi đọc file log: {str(e)}")