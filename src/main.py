import streamlit as st
import sys
import os
from pathlib import Path

# Thêm thư mục gốc của dự án vào Python path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.chatbot_logic import ChatbotLogic
from src.database_manager import DatabaseManager
from src.database_admin import AdminDatabaseManager
from src.admin_page import admin_page
from src.statistics_page import statistics_page
from src.admin_settings_page import admin_settings_page

# Khởi tạo chatbot logic một lần duy nhất
@st.cache_resource
def get_chatbot_logic():
    db_manager_instance = DatabaseManager()
    
    temp_chatbot_logic_instance = ChatbotLogic()
    log_file_full_path = temp_chatbot_logic_instance.log_filepath

    print("Bắt đầu kiểm tra và tải nhật ký tự động khi ứng dụng khởi động...")
    if db_manager_instance.upload_logs_to_github_on_startup(str(log_file_full_path)):
         print("Tải nhật ký tự động hoàn tất (hoặc không có log để tải).")
    else:
         print("Tải nhật ký tự động thất bại hoặc có lỗi xảy ra.")
    
    return temp_chatbot_logic_instance

# KHỞI TẠO CÁC MANAGER (ĐỂ SỬ DỤNG CHO CẢ CÁC TRANG ADMIN VÀ CÀI ĐẶT)
@st.cache_resource
def get_managers():
    db_instance = DatabaseManager()
    admin_db_instance = AdminDatabaseManager(db_instance)
    return {
        "db_manager": db_instance,
        "admin_db_manager": admin_db_instance
    }
    
def chatbot_page():
    st.set_page_config(page_title="Lab Chatbot - Duy Tan University", layout="centered")
    st.title("🧪 Lab Chatbot - Duy Tan University")
    st.write("Chào bạn! Tôi là trợ lý ảo giúp bạn tra cứu, thống kê vật tư và hóa chất trong phòng thí nghiệm được thiết kế bởi Khoa Môi trường và Khoa học tự nhiên phục vụ công tác nội bộ. Bạn muốn tìm kiếm hóa chất hoặc vật tư? Hãy cho tôi biết! Hoặc nếu bạn muốn tôi hướng dẫn tìm kiếm, hãy gõ Hướng dẫn...")

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

def main_app():
    st.sidebar.title("Điều hướng")
    page_selection = st.sidebar.radio("Chọn trang:", ["Chatbot", "Thống kê", "Theo dõi", "Cài đặt"])

    managers = get_managers()

    if st.sidebar.button("Xóa Cache 🗑️"):
        st.cache_resource.clear()
        st.success("Đã xóa toàn bộ cache!")
        st.rerun()

    if page_selection == "Chatbot":
        chatbot_page()
    elif page_selection == "Thống kê":
        statistics_page()
    elif page_selection == "Theo dõi":
        admin_page()
    elif page_selection == "Cài đặt":
        admin_settings_page(managers['db_manager'], managers['admin_db_manager'])

if __name__ == "__main__":
    main_app()