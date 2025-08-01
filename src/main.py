# src/main.py

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
from src.admin_page import admin_page # Import trang admin
from src.statistics_page import statistics_page # BỔ SUNG: Import trang thống kê mới

# Khởi tạo chatbot logic và database manager một lần duy nhất
@st.cache_resource
def get_chatbot_logic():
    # Khởi tạo DatabaseManager trước để có thể dùng cho việc upload log
    db_manager_instance = DatabaseManager()
    
    # Để có đường dẫn đầy đủ đến file log, chúng ta cần một instance của ChatbotLogic
    # (hoặc ít nhất là biết logic xây dựng đường dẫn của nó).
    # Chúng ta sẽ tạo một instance tạm thời để lấy đường dẫn log đầy đủ.
    # ChatbotLogic sẽ được khởi tạo lại (hoặc trả về instance đã cache) ở dòng return cuối.
    temp_chatbot_logic_instance = ChatbotLogic()
    log_file_full_path = temp_chatbot_logic_instance.log_filepath # Lấy đường dẫn đầy đủ (Path object)

    print("Bắt đầu kiểm tra và tải nhật ký tự động khi ứng dụng khởi động...")
    # Sửa lỗi: Truyền đường dẫn đầy đủ (dưới dạng string) đến hàm upload
    if db_manager_instance.upload_logs_to_github_on_startup(str(log_file_full_path)):
         print("Tải nhật ký tự động hoàn tất (hoặc không có log để tải).")
    else:
         print("Tải nhật nhật ký tự động thất bại hoặc có lỗi xảy ra.")
    
    # Trả về instance của ChatbotLogic để Streamlit cache và sử dụng
    return temp_chatbot_logic_instance

# Hàm chứa logic của trang Chatbot
def chatbot_page():
    st.set_page_config(page_title="Lab Chatbot - Duy Tan University", layout="centered")
    st.title("🧪 Lab Chatbot - Duy Tan University")
    st.write("Chào bạn! Tôi là trợ lý ảo giúp bạn tra cứu, thống kê vật tư và hóa chất trong phòng thí nghiệm được thiết kế bởi Khoa Môi trường và Khoa học tự nhiên phục vụ công tác nội bộ. Bạn muốn tìm kiếm hóa chất hoặc vật tư? Hãy cho tôi biết! Hoặc nếu bạn muốn tôi hướng dẫn tìm kiếm, hãy gõ Hướng dẫn...")

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

# Hàm chính để điều khiển các trang
def main_app():
    st.sidebar.title("Điều hướng")
    # BỔ SUNG/SỬA ĐỔI: Thêm "Thống kê" và đổi tên "Admin" thành "Theo dõi"
    page_selection = st.sidebar.radio("Chọn trang:", ["Chatbot", "Thống kê", "Theo dõi"])

    # BỔ SUNG: Nút để xóa cache toàn cục
    if st.sidebar.button("Xóa Cache 🗑️"):
        st.cache_resource.clear()
        st.success("Đã xóa toàn bộ cache!")
        st.rerun() # Yêu cầu chạy lại ứng dụng để áp dụng việc xóa cache

    if page_selection == "Chatbot":
        chatbot_page()
    elif page_selection == "Thống kê": # BỔ SUNG: Điều kiện cho trang Thống kê
        statistics_page()
    elif page_selection == "Theo dõi": # ĐÃ ĐỔI TÊN: "Theo dõi" thay vì "Admin"
        admin_page()

if __name__ == "__main__":
    main_app()