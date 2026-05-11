from __future__ import annotations

import json
import streamlit as st
import pandas as pd
import plotly.io as pio
import requests
from dataclasses import dataclass
from typing import Any, Literal, Optional

from config import *
import os

from dotenv import load_dotenv
load_dotenv()

API_URL = os.getenv("API_URL")

@dataclass
class ChatEvent:
    role: Literal["user", "assistant"]
    type: Literal["text", "pending_code", "result_df", "result_plotly", "error"]
    content: str
    code: Optional[str] = None
    data: Optional[Any] = None
    is_executed: bool = False  # Đánh dấu xem đoạn code này đã được người dùng duyệt/chạy chưa

def call_ai_generate(query: str) -> dict:
    """Gọi API sinh code của AI"""
    response = requests.post(f"{API_URL}/ai/generate", json={"query": query})

    if response.status_code != 200:
        try:
            error_detail = response.json().get("detail", response.text)
        except Exception:
            error_detail = response.text
        raise Exception(f"Chi tiết lỗi từ Backend: {error_detail}")
        
    return response.json()

def call_executor(code: str) -> dict:
    """Gửi code đã duyệt xuống API Thực thi Local"""
    response = requests.post(f"{API_URL}/execute", json={"code": code})
    
    if response.status_code != 200:
        # Giúp debug lỗi tốt hơn
        try:
            error_detail = response.json().get("detail", "Lỗi thực thi không xác định")
        except:
            error_detail = response.text
        raise Exception(error_detail)
    return response.json()

def execute_and_append(code: str, index: int):
    # Đánh dấu đã thực thi để ẩn nút bấm
    st.session_state.chat_events[index].is_executed = True
    st.session_state.chat_events[index].code = code 

    try:
        res = call_executor(code)
        if res["status"] == "success":
            if res["type"] == "dataframe":
                st.session_state.chat_events.append(
                    ChatEvent(role="assistant", type="result_df", content="📊 **Kết quả dữ liệu:**", data=res["data"])
                )
            elif res["type"] == "plotly_json":
                st.session_state.chat_events.append(
                    ChatEvent(role="assistant", type="result_plotly", content="📈 **Biểu đồ phân tích:**", data=res["data"])
                )
            st.rerun() 
    except Exception as e:
        st.session_state.chat_events.append(
            ChatEvent(role="assistant", type="error", content=f"❌ **Lỗi thực thi:**\n{str(e)}")
        )
        st.rerun()

def chatbot_area(mart_filtered: pd.DataFrame) -> None:
    st.markdown("### 🤖 Trợ lý AI Phân tích")
    # st.caption("Nhập yêu cầu bằng ngôn ngữ tự nhiên. AI sẽ sinh mã Python và chờ bạn duyệt/chỉnh sửa trước khi thực thi.")

    # Hiển thị lịch sử chat
    for i, ev in enumerate(st.session_state.chat_events):
        with st.chat_message(ev.role):
            if ev.type == "text":
                st.markdown(ev.content)
            
            elif ev.type == "pending_code":
                st.markdown(f"**💡 Giải thích:** {ev.content}")
                
                if not ev.is_executed:
                    st.info("Trạng thái: Đang chờ duyệt. Bạn có thể chỉnh sửa mã nguồn bên dưới trước khi chạy.")
                    # Cho phép chỉnh sửa code
                    edited_code = st.text_area("Mã nguồn (Python):", value=ev.code, height=250, key=f"code_{i}")
                    
                    col1, col2 = st.columns([1.5, 5])
                    with col1:
                        if st.button("🚀 Duyệt & Chạy", key=f"btn_{i}", type="primary"):
                            execute_and_append(edited_code, i)
                    with col2:
                        if st.button("❌ Hủy bỏ", key=f"reject_{i}"):
                            st.session_state.chat_events[i].is_executed = True
                            st.session_state.chat_events.append(
                                ChatEvent(role="assistant", type="text", content="Đã hủy bỏ việc thực thi đoạn mã trên.")
                            )
                            st.rerun()
                else:
                    st.markdown("**Đoạn mã đã chốt & thực thi:**")
                    st.code(ev.code, language="python")

            elif ev.type == "result_df":
                st.markdown(ev.content)
                st.dataframe(pd.DataFrame(ev.data))
            
            elif ev.type == "result_plotly":
                st.markdown(ev.content)
                fig = pio.from_json(ev.data)
                st.plotly_chart(fig, use_container_width=True)
            
            elif ev.type == "error":
                st.error(ev.content)

    # Khung nhập liệu
    prompt = st.chat_input("Ví dụ: Vẽ biểu đồ top 5 ngành hàng có doanh thu ước tính cao nhất")
    
    if prompt:
        # Thêm câu hỏi của user vào log và tải lại UI để hiển thị ngay lập tức
        st.session_state.chat_events.append(ChatEvent(role="user", type="text", content=prompt))
        st.rerun()

    # Luồng xử lý gọi API: Kích hoạt nếu tin nhắn cuối cùng là của người dùng
    if st.session_state.chat_events and st.session_state.chat_events[-1].role == "user":
        with st.chat_message("assistant"):
            with st.spinner("AI đang phân tích dữ liệu và sinh mã nguồn..."):
                try:
                    ai_response = call_ai_generate(st.session_state.chat_events[-1].content)
                    st.session_state.chat_events.append(
                        ChatEvent(
                            role="assistant", 
                            type="pending_code", 
                            content=ai_response["explanation"],
                            code=ai_response["code"]
                        )
                    )
                    st.rerun() # Tải lại UI để hiển thị khung code chờ duyệt
                except Exception as e:
                    st.error(f"Lỗi kết nối đến API AI: {str(e)}\n\nHãy đảm bảo bạn đã khởi động Backend FastAPI ở cổng 8000.")
                    # Ghi nhận lỗi và thoát luồng chờ
                    st.session_state.chat_events.append(ChatEvent(role="assistant", type="error", content=f"API Error: {str(e)}"))

def load_chat_history() -> list[ChatEvent]:
    """Gọi API Logs, xử lý dữ liệu và tái tạo lại 2 phiên chat gần nhất"""
    try:
        response = requests.get(f"{API_URL}/logs/history?limit=15", timeout=3)
        if response.status_code == 200:
            history_data = response.json().get("data", [])
            new_events = []
            
            # Duyệt từ cũ đến mới
            for entry in reversed(history_data):
                # 1. Tái tạo câu hỏi và đoạn code của AI
                if entry.get("action") == "CHAT_SESSION":
                    user_q, ai_exp, ai_code = "", "", ""
                    for ev in entry.get("events", []):
                        if ev.get("role") == "user":
                            user_q = ev.get("content")
                        elif ev.get("type") == "text":
                            ai_exp = ev.get("content")
                        elif ev.get("type") == "code":
                            ai_code = ev.get("content")
                            
                    # Thêm câu hỏi User
                    if user_q:
                        new_events.append(ChatEvent(role="user", type="text", content=user_q))
                    # Thêm Code AI (đánh dấu is_executed=True để web hiện dạng đã chốt)
                    if ai_exp or ai_code:
                        new_events.append(ChatEvent(
                            role="assistant", 
                            type="pending_code", 
                            content=ai_exp, 
                            code=ai_code,
                            is_executed=True 
                        ))
                        
                # 2. Tái tạo Kết quả biểu đồ/bảng dữ liệu
                elif entry.get("action") == "EXECUTE" and entry.get("status") == "success":
                    ev_type = entry.get("type", "result_df")
                    data_to_pass = entry.get("analysis_output")
                    
                    # QUAN TRỌNG: Xử lý bẫy lỗi Plotly (Ép kiểu dict về string)
                    if ev_type == "result_plotly" and isinstance(data_to_pass, dict):
                        data_to_pass = json.dumps(data_to_pass)

                    new_events.append(ChatEvent(
                        role=entry.get("role", "assistant"),
                        type=ev_type,
                        content=entry.get("content", "📊 Kết quả lịch sử:"),
                        data=data_to_pass,
                        is_executed=True
                    ))
            
            # Trả về 8 sự kiện cuối cùng (tương đương 2 lần hỏi đáp + biểu đồ)
            return new_events[-8:]
    except Exception as e:
        print(f"Lỗi load lịch sử: {e}")
        return []
    return []