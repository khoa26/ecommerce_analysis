from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import pandas as pd
import plotly.io as pio
import sys
import json
import os
from datetime import datetime
from pathlib import Path
import io
import contextlib

root_dir = str(Path(__file__).resolve().parents[2])
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

web_app_dir = str(Path(__file__).resolve().parents[1] / "web_app")
if web_app_dir not in sys.path:
    sys.path.insert(0, web_app_dir)

from src.web_app.data_engine import build_product_mart

router = APIRouter(prefix="/execute", tags=["Local Execution"])

class ExecuteRequest(BaseModel):
    code: str

def log_execution_activity(entry: dict):
    """Ghi log chi tiết quá trình thực thi và kết quả"""
    log_dir = Path(__file__).resolve().parents[2] / "data" / "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = log_dir / "ai_activity.jsonl"
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

@router.post("")
async def run_code(request: ExecuteRequest):
    log_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": "EXECUTE",
        "executed_code": request.code,
        "status": "pending",
        "result_type": None,
        "analysis_output": None,
        "execution_logs": None, # Thêm trường lưu log
        "error_detail": None
    }
    
    # Tạo biến để hứng mọi lệnh print() hoặc warning
    stdout_capture = io.StringIO()
    
    try:
        df = build_product_mart()
        local_namespace = {}
        
        # BỌC LỆNH CHẠY CODE VÀO TRONG contextlib
        with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stdout_capture):
            exec(request.code, globals(), local_namespace)
            
            if 'analyze' not in local_namespace:
                raise ValueError("Không tìm thấy hàm analyze(df)")
                
            result = local_namespace['analyze'](df)
            
        # Lấy toàn bộ chữ đã được print ra
        captured_logs = stdout_capture.getvalue()
        
        # Xử lý kết quả trả về và ghi log (NHỚ TRẢ THÊM 'logs' VỀ CHO FRONTEND)
        if result['type'] == 'dataframe':
            data_sample = result['data'].head(10).to_dict(orient='records')
            log_entry.update({
                "status": "success",
                "result_type": "dataframe",
                "analysis_output": data_sample,
                "execution_logs": captured_logs
            })
            log_execution_activity(log_entry)
            
            return {
                "status": "success", 
                "type": "dataframe", 
                "data": result['data'].head(100).to_dict(orient='records'),
                "logs": captured_logs # <-- Trả logs về frontend
            }
            
        elif result['type'] == 'plotly_json':
            fig_json = pio.to_json(result['data'])
            log_entry.update({
                "status": "success",
                "result_type": "plotly_json",
                "analysis_output": json.loads(fig_json),
                "execution_logs": captured_logs
            })
            log_execution_activity(log_entry)
            
            return {
                "status": "success", 
                "type": "plotly_json", 
                "data": fig_json,
                "logs": captured_logs # <-- Trả logs về frontend
            }

    except Exception as e:
        # Nếu có lỗi, cũng lấy luôn những gì đã kịp print ra trước khi chết
        captured_logs = stdout_capture.getvalue()
        log_entry.update({
            "status": "failed",
            "execution_logs": captured_logs,
            "error_detail": str(e)
        })
        log_execution_activity(log_entry)
        raise HTTPException(status_code=400, detail=f"Lỗi: {str(e)}\nLogs: {captured_logs}")