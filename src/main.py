# src/main.py

import streamlit as st
import sys
from pathlib import Path

# Thêm thư mục gốc của dự án vào Python path nếu chưa có
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import các module và trang của ứng dụng
from src.auth import get_user_info, logout
from src.user_manager import UserManager
from src.database_manager import DatabaseManager
from src.database_admin import AdminDatabaseManager
from src.home_page import home_page
from src.admin_page import admin_page
from src.admin_settings_page import admin_settings_page
from src.ai_assistant_page import ai_assistant_page
from src.statistics_page import statistics_page
from src.user_management_page import user_management_page
from src.chatbot_page import chatbot_page

# Cấu hình trang
st.set_page_config(page_title="Hệ thống Quản lý Lab", layout="wide", initial_sidebar_state="expanded")

# Khởi tạo các manager
db_manager = DatabaseManager()
admin_db_manager = AdminDatabaseManager()
user_manager = UserManager(admin_db_manager)

def setup_sidebar(user_info):
    """Thiết lập và hiển thị thanh bên (sidebar) dựa trên trạng thái đăng nhập."""
    st.sidebar.title("Menu")
    
    if user_info:
        # Nếu đã đăng nhập, hiển thị thông tin người dùng và nút đăng xuất
        user_role = st.session_state.get('user_role', 'guest')
        st.sidebar.write(f"**Xin chào, {user_info.get('given_name', user_info.get('name', 'bạn'))}!**")
        st.sidebar.write(f"Vai trò: {user_role.capitalize()}")
        st.sidebar.button("Đăng xuất", on_click=logout, key="sidebar_logout")
    else:
        # Nếu chưa đăng nhập, hiển thị thông báo
        st.sidebar.info("Vui lòng đăng nhập để sử dụng các tính năng.")

def show_pages_by_role(user_role):
    """
    Hiển thị các trang chức năng trong sidebar dựa trên vai trò của người dùng.
    """
    page_dependencies = {
        "user_manager": user_manager,
        "db_manager": db_manager,
        "admin_db_manager": admin_db_manager
    }

    PAGES = {
        "Trang chủ": {"func": home_page, "roles": ["guest", "user", "registered", "moderator", "administrator"], "args": {}},
        "Chatbot": {"func": chatbot_page, "roles": ["guest", "user", "registered", "moderator", "administrator"], "args": {}},
        "Trợ lý AI": {"func": ai_assistant_page, "roles": ["user", "registered", "moderator", "administrator"], "args": {}},
        "Quản lý": {"func": admin_page, "roles": ["moderator", "administrator"], "args": {}},
        "Thống kê": {"func": statistics_page, "roles": ["moderator", "administrator"], "args": {}},
        "Quản lý người dùng": {"func": user_management_page, "roles": ["administrator"], "args": {"user_manager": page_dependencies["user_manager"]}},
        "Cài đặt Admin": {
            "func": admin_settings_page,
            "roles": ["administrator"],
            "args": {
                "db_manager": page_dependencies["db_manager"],
                "admin_db_manager": page_dependencies["admin_db_manager"]
            }
        },
    }

    allowed_pages = [name for name, details in PAGES.items() if user_role in details["roles"]]

    if not allowed_pages:
        st.warning("Bạn không có quyền truy cập vào bất kỳ trang nào.")
        return

    selected_page_name = st.sidebar.radio(
        "Điều hướng",
        options=allowed_pages,
    )

    page_details = PAGES[selected_page_name]
    page_function = page_details["func"]
    page_args = page_details["args"]
    page_function(**page_args)


def main():
    """Hàm chính điều khiển luồng của ứng dụng."""
    
    redirect_uri = db_manager.config_data.get("site_url", "http://localhost:8501")
    user_info = get_user_info(redirect_uri)
    
    if user_info:
        user_email = user_info.get('email')
        
        current_role = user_manager.get_user_role(user_email)
        
        if current_role == "guest":
            user_manager.add_or_update_user(user_email, "registered")
            st.session_state.user_role = "registered"
            print(f"Người dùng mới '{user_email}' đã được tự động đăng ký.")
        else:
            if 'user_role' not in st.session_state or st.session_state.get('user_email') != user_email:
                st.session_state.user_role = current_role

        st.session_state.user_email = user_email
        setup_sidebar(user_info)
        show_pages_by_role(st.session_state.user_role)
    else:
        setup_sidebar(None)
        
        st.title("Chào mừng đến với Hệ thống Quản lý Lab")
        st.write("Vui lòng chọn 'Đăng nhập bằng Google' ở thanh bên để bắt đầu.")
        st.info("Chức năng Chatbot có thể sử dụng mà không cần đăng nhập. Vui lòng chọn trên thanh điều hướng.")

if __name__ == "__main__":
    main()