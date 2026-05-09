from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import pandas as pd
import plotly.io as pio
import sys
import traceback
from pathlib import Path

# Thêm thư mục gốc vào hệ thống path
root_dir = str(Path(__file__).resolve().parents[2])
if root_dir not in sys.path:
    sys.path.append(root_dir)

# BỔ SUNG: Thêm thư mục web_app vào hệ thống path
web_app_dir = str(Path(__file__).resolve().parents[1] / "web_app")
if web_app_dir not in sys.path:
    sys.path.append(web_app_dir)

from src.web_app.data_engine import build_product_mart

router = APIRouter(prefix="/execute", tags=["Local Execution"])

class ExecuteRequest(BaseModel):
    code: str

@router.post("/")
async def run_code(request: ExecuteRequest):
    """
    Thực thi mã Python do AI tạo ra (hoặc đã qua chỉnh sửa của con người) 
    trực tiếp trên DataFrame local.
    """
    try:
        # 1. Load dữ liệu
        df = build_product_mart()
        if df.empty:
            raise ValueError("Data mart đang rỗng, không thể phân tích.")

        # 2. Chuẩn bị không gian thực thi (Sandboxing cơ bản)
        local_namespace = {}
        
        # 3. Compile và chạy code để định nghĩa hàm analyze(df)
        exec(request.code, globals(), local_namespace)
        
        if 'analyze' not in local_namespace:
            raise ValueError("Đoạn mã không chứa hàm 'analyze(df)' theo chuẩn.")
            
        analyze_func = local_namespace['analyze']
        
        # 4. Thực thi hàm với dữ liệu
        result = analyze_func(df)
        
        # 5. Xử lý kết quả trả về Frontend
        if result['type'] == 'dataframe':
            # Chuyển DataFrame thành list of dicts (JSON)
            data_json = result['data'].head(100).to_dict(orient='records')
            return {"status": "success", "type": "dataframe", "data": data_json}
            
        elif result['type'] == 'plotly_json':
            # Convert Plotly Figure thành JSON để Streamlit vẽ lại
            fig_json = pio.to_json(result['data'])
            return {"status": "success", "type": "plotly_json", "data": fig_json}
            
        else:
            raise ValueError(f"Loại trả về không hợp lệ: {result.get('type')}")

    except Exception as e:
        error_trace = traceback.format_exc()
        raise HTTPException(status_code=400, detail=f"Lỗi thực thi code:\n{str(e)}\n\nChi tiết:\n{error_trace}")