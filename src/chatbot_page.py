# src/chatbot_page.py

import streamlit as st
import pandas as pd
from src.chatbot_logic import ChatbotLogic

# Khởi tạo chatbot logic một lần duy nhất và cache lại
@st.cache_resource
def get_chatbot_logic():
    return ChatbotLogic()

def chatbot_page():
    st.title("🧪 Chatbot Lab")
    st.markdown("---")
    st.write("Chào bạn! Tôi là trợ lý ảo giúp bạn tra cứu nhanh thông tin vật tư và hóa chất. Hãy gõ Hướng dẫn để xem cách tôi hoạt động.")

    chatbot = get_chatbot_logic()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Nhập câu hỏi của bạn..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.spinner("Đang xử lý..."):
            response = chatbot.get_response(prompt)
        
        st.session_state.messages.append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.markdown(response)