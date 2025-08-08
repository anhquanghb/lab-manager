# src/gemini_chatbot.py

import google.generativeai as genai
import pandas as pd
from src.database_manager import DatabaseManager
from src.common_utils import remove_accents_and_normalize


class GeminiChatbot:
    def __init__(self, api_key):
        if not api_key:
            raise ValueError("Gemini API Key is not provided.")
        
        self.api_key = api_key
        genai.configure(api_key=self.api_key)
        
        self.db_manager = DatabaseManager()
        
        # Lấy tên mô hình từ config, mặc định là 'gemini-1.5-flash'
        model_name = self.db_manager.config_data.get('gemini_model_name', 'gemini-1.5-flash')
        self.model = genai.GenerativeModel(model_name)
        
    def process_user_query(self, user_query, chat_history):
        # Tạo đối tượng chat từ lịch sử đã lưu
        chat_session = self.model.start_chat(history=chat_history)
        
        # Gửi tin nhắn của người dùng vào phiên chat
        try:
            response = chat_session.send_message(user_query)
            return response.text
        except Exception as e:
            return f"Lỗi khi gọi Gemini API: {e}"