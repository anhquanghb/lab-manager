import streamlit as st
import sys
import os

# Thêm thư mục gốc của dự án vào Python path
# Điều này giúp các import như 'from src.chatbot_logic' hoạt động khi chạy Streamlit
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.chatbot_logic import ChatbotLogic


# Khởi tạo chatbot logic một lần duy nhất
@st.cache_resource
def get_chatbot_logic():
    return ChatbotLogic()

def main():
    st.set_page_config(page_title="Lab Manager Chatbot", layout="centered")
    st.title("Trợ Lý Lab Manager AI Chatbot")
    st.write("Chào bạn! Tôi là trợ lý ảo giúp bạn tra cứu, thống kê vật tư và hóa chất trong phòng thí nghiệm. Bạn muốn hỏi gì?")

    chatbot = get_chatbot_logic()

    # Khởi tạo lịch sử chat trong session_state
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Hiển thị các tin nhắn cũ từ lịch sử
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Xử lý input từ người dùng
    if prompt := st.chat_input("Nhập câu hỏi của bạn..."):
        # Thêm tin nhắn người dùng vào lịch sử chat
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Lấy phản hồi từ chatbot
        with st.spinner("Đang xử lý..."):
            response = chatbot.get_response(prompt)

        # Thêm tin nhắn của chatbot vào lịch sử chat
        st.session_state.messages.append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.markdown(response)

if __name__ == "__main__":
    main()