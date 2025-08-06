# src/ai_assistant_page.py

import streamlit as st
from src.database_manager import DatabaseManager
from src.gemini_chatbot import GeminiChatbot
import sys
from pathlib import Path

# Thêm thư mục gốc của dự án vào Python path nếu chưa có
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

@st.cache_resource
def get_gemini_chatbot(api_key):
    try:
        return GeminiChatbot(api_key)
    except ValueError as e:
        st.error(e)
        return None

def ai_assistant_page():
    st.title("🤖 Trợ Lý AI Pha Chế Hóa Chất")
    st.write("Sử dụng Trợ lý AI để thiết kế thí nghiệm, tính toán hóa chất và nhiều hơn nữa. Bạn không thể tìm vị trí hoặc thông tin về vật tư ở đây. Hãy hỏi Chatbot trong menu điều hướng bên trái hoặc mũi tên >> ở trên cùng.")

    # Lấy API Key từ config.json hoặc session state
    db_manager = DatabaseManager()
    gemini_api_key = db_manager.config_data.get('gemini_api_key', '')
    
    if not gemini_api_key:
        st.warning("Admin chưa cung cấp Gemini API Key. Vui lòng nhập API của bạn để sử dụng.")
        user_api_key = st.text_input("Nhập Gemini API Key của bạn:", type="password")
        
        if 'user_gemini_api_key' not in st.session_state and user_api_key:
            st.session_state['user_gemini_api_key'] = user_api_key
            st.success("Đã lưu API Key của bạn. Bây giờ bạn có thể sử dụng Trợ lý AI.")
        elif 'user_gemini_api_key' in st.session_state and not user_api_key:
            user_api_key = st.session_state['user_gemini_api_key']
        
        if not user_api_key:
            return
        else:
            final_api_key = user_api_key
    else:
        final_api_key = gemini_api_key

    gemini_chatbot = get_gemini_chatbot(final_api_key)
    if gemini_chatbot is None:
        return

    # Khởi tạo lịch sử chat trong session state
    if "gemini_messages" not in st.session_state:
        st.session_state.gemini_messages = []
        
        # Thêm lời chào ban đầu để hiển thị cho người dùng
        initial_greeting = "Tôi là Trợ lý Phòng thí nghiệm AI. Hãy cho tôi biết bạn cần gì."
        st.session_state.gemini_messages.append({"role": "assistant", "content": initial_greeting})

    # Hiển thị tất cả tin nhắn từ lịch sử chat
    for message in st.session_state.gemini_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Xử lý input của người dùng
    if prompt := st.chat_input("Nhập yêu cầu của bạn..."):
        # Thêm tin nhắn của người dùng vào lịch sử
        st.session_state.gemini_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Tạo lịch sử chat để gửi cho Gemini
        # Lưu ý: Gemini API cần lịch sử chat ở định dạng riêng
        history_for_gemini = [
            {"role": "user", "parts": [part["content"]]} if part["role"] == "user"
            else {"role": "model", "parts": [part["content"]]} for part in st.session_state.gemini_messages[1:]
        ]
        
        with st.spinner("Đang xử lý..."):
            response = gemini_chatbot.process_user_query(prompt, history_for_gemini)
        
        # Thêm phản hồi của AI vào lịch sử
        st.session_state.gemini_messages.append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.markdown(response)