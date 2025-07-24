import streamlit as st
import sys
import os

# Thêm thư mục gốc của dự án vào Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.chatbot_logic import ChatbotLogic
from src.database_manager import DatabaseManager # Cần import DatabaseManager để gọi hàm upload

# Khởi tạo chatbot logic một lần duy nhất
@st.cache_resource
def get_chatbot_logic():
    # Gọi hàm tải log tự động khi ứng dụng khởi động
    # DatabaseManager cần được khởi tạo trước để có đường dẫn và hàm upload
    db_manager_instance = DatabaseManager() 
    print("Bắt đầu kiểm tra và tải nhật ký tự động khi ứng dụng khởi động...")
    if db_manager_instance.upload_logs_to_github_on_startup(ChatbotLogic.LOG_FILE): # Gọi hàm từ DatabaseManager
         print("Tải nhật ký tự động hoàn tất (hoặc không có log để tải).")
    else:
         print("Tải nhật ký tự động thất bại hoặc có lỗi xảy ra.")

    return ChatbotLogic() # Trả về instance của ChatbotLogic như cũ

def main():
    st.set_page_config(page_title="Lab AI Chatbot - Duy Tan University", layout="centered")
    st.title("🧪 Lab AI Chatbot - Duy Tan University")
    st.write("Chào bạn! Tôi là trợ lý ảo giúp bạn tra cứu, thống kê vật tư và hóa chất trong phòng thí nghiệm được thiết kế bởi Khoa Môi trường và Khoa học tự nhiên phục vụ công tác nội bộ. Bạn muốn tìm kiếm hóa chất hoặc vật tư? Hãy cho tôi biết! Hoặc nếu bạn muốn tôi hướng dẫn tìm kiếm, hãy gõ Hướng dẫn...")

    chatbot = get_chatbot_logic()

    # ... (phần còn lại của hàm main không thay đổi) ...

    # Xử lý input từ người dùng
    if prompt := st.chat_input("Nhập câu hỏi của bạn..."):
        # ... (phần còn lại của hàm main không thay đổi) ...
        response = chatbot.get_response(prompt)
        # ... (phần còn lại của hàm main không thay đổi) ...

if __name__ == "__main__":
    main()