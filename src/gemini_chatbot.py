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
        self.model = genai.GenerativeModel('gemini-2.0-flash') # Sử dụng mô hình bạn đã chọn
        
        self.db_manager = DatabaseManager()

        self.full_prompt = self.db_manager.config_data.get('ai_full_prompt', '')

    def process_user_query(self, user_query, chat_history):
        # Tạo lại đối tượng chat từ lịch sử đã lưu
        chat_session = self.model.start_chat(history=chat_history)
        
        # Bổ sung prompt đầy đủ vào message đầu tiên
        # Lần đầu tiên chat, lịch sử sẽ trống, ta thêm prompt vào
        if not chat_session.history:
             chat_session.send_message(self.full_prompt)

        # Gửi tin nhắn của người dùng vào phiên chat
        try:
            response = chat_session.send_message(user_query)
            return response.text
        except Exception as e:
            return f"Lỗi khi gọi Gemini API: {e}"