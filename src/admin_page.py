import streamlit as st
import pandas as pd
from src.database_manager import DatabaseManager # Import DatabaseManager cho các thao tác đọc
from src.database_admin import AdminDatabaseManager # BỔ SUNG: Import AdminDatabaseManager cho các thao tác ghi
import os
from pathlib import Path
from src.common_utils import remove_accents_and_normalize

# --- Khởi tạo các Manager (chỉ một lần và được cache) ---
@st.cache_resource
def get_managers():
    # Khởi tạo DatabaseManager (đọc dữ liệu)
    db_instance = DatabaseManager()
    # Khởi tạo AdminDatabaseManager (ghi dữ liệu), truyền db_instance vào
    admin_db_instance = AdminDatabaseManager(db_instance)
    return {
        "db_manager": db_instance,
        "admin_db_manager": admin_db_instance
    }

# BỔ SUNG: Khởi tạo và gán các manager
managers = get_managers()
db_manager = managers["db_manager"]
admin_db_manager = managers["admin_db_manager"]

# --- Lấy mật khẩu từ Streamlit secrets ---
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD")

def admin_login_form():
    """Hiển thị form đăng nhập Admin."""
    st.title("🔐 Đăng nhập Admin")
    password = st.text_input("Nhập mật khẩu:", type="password")
    if st.button("Đăng nhập"):
        if password == ADMIN_PASSWORD:
            st.session_state["admin_logged_in"] = True
            st.rerun()
        else:
            st.error("Mật khẩu không đúng. Vui lòng thử lại.")

def admin_dashboard():
    """Hiển thị nội dung chính của trang Admin sau khi đăng nhập thành công."""
    st.title("⚙️ Trang Admin - Quản lý Vật tư & Hóa chất")

    if st.button("Đăng xuất Admin"):
        st.session_state["admin_logged_in"] = False
        st.rerun()

    st.markdown("---")
    st.header("Tìm kiếm và Cập nhật Tracking")

    item_id_to_find = st.text_input("Nhập ID vật tư/hóa chất cần tìm (ví dụ: A001A, ITEM_1):", key="admin_search_id_input")
    
    search_button = st.button("Tìm kiếm theo ID", key="admin_search_button")

    if search_button and item_id_to_find:
        st.session_state['admin_current_item_id'] = item_id_to_find
        # Sử dụng db_manager (đọc) cho tìm kiếm
        st.session_state['admin_search_results'] = db_manager.get_by_id(item_id_to_find) 
    
    # Hiển thị kết quả tìm kiếm và form cập nhật
    if 'admin_search_results' in st.session_state and not st.session_state['admin_search_results'].empty:
        item_data = st.session_state['admin_search_results'].iloc[0]
        
        st.subheader(f"Thông tin mục: {item_data['name']} (ID: {item_data['id']})")
        st.write(f"**Loại:** {item_data['type']}")
        st.write(f"**Vị trí:** {item_data['location']}")
        st.write(f"**Số lượng:** {item_data['quantity']} {item_data['unit']}")
        st.write(f"**Công thức:** {item_data['chemical_formula'] if pd.notna(item_data['chemical_formula']) else 'N/A'}")
        st.write(f"**Số CAS:** {item_data['cas_number'] if pd.notna(item_data['cas_number']) else 'N/A'}")
        st.write(f"**Trạng thái/Nồng độ:** {item_data['state_or_concentration'] if pd.notna(item_data['state_or_concentration']) else 'N/A'}")
        st.write(f"**Tình trạng:** {item_data['status'] if pd.notna(item_data['status']) else 'N/A'}")
        st.write(f"**Mục đích:** {item_data['purpose'] if pd.notna(item_data['purpose']) else 'N/A'}")
        st.write(f"**Theo dõi:** {item_data['tracking'] if pd.notna(item_data['tracking']) else 'N/A'}")
        
        st.markdown("---")
        st.subheader("Cập nhật Tracking")

        current_tracking = item_data['tracking'] if pd.notna(item_data['tracking']) else ""
        new_tracking_info = st.text_area(
            f"Cập nhật thông tin Theo dõi cho ID '{item_data['id']}' (hiện tại: '{current_tracking}')",
            value=current_tracking,
            key="new_tracking_info_textarea"
        )
        
        if st.button("Lưu và Đẩy lên GitHub", key="update_tracking_button"):
            # 1. Cập nhật trên bộ nhớ (vẫn qua db_manager vì đó là instance chứa DataFrame chính)
            idx_to_update = db_manager.inventory_data[db_manager.inventory_data['id'] == item_data['id']].index
            if not idx_to_update.empty:
                db_manager.inventory_data.loc[idx_to_update, 'tracking'] = new_tracking_info
                db_manager.inventory_data.loc[idx_to_update, 'tracking_normalized'] = remove_accents_and_normalize(new_tracking_info)

                st.success(f"Thông tin theo dõi cho ID '{item_data['id']}' đã được cập nhật trên bộ nhớ.")
                
                # 2. Lưu vào file JSON (sử dụng admin_db_manager)
                if admin_db_manager.save_inventory_to_json():
                    st.success("Đã lưu thay đổi vào file inventory.json.")
                    
                    # 3. Đẩy lên GitHub (sử dụng admin_db_manager)
                    commit_message = f"feat(admin): Update tracking for ID {item_data['id']} to '{new_tracking_info}'"
                    if admin_db_manager.push_inventory_to_github(commit_message):
                        st.success("Đã đẩy thay đổi lên GitHub thành công!")
                    else:
                        st.error("Lỗi: Không thể đẩy thay đổi lên GitHub. Vui lòng kiểm tra console log.")
                else:
                    st.error("Lỗi: Không thể lưu thay đổi vào file inventory.json.")
                
                # Cập nhật lại kết quả tìm kiếm để hiển thị thông tin mới (và kích hoạt rerun)
                st.session_state['admin_search_results'] = db_manager.get_by_id(item_data['id'])
                st.rerun() 
            else:
                st.error("Không tìm thấy mục để cập nhật.")
    elif 'admin_search_results' in st.session_state and st.session_state['admin_search_results'].empty:
        st.warning(f"Không tìm thấy mục với ID: '{st.session_state['admin_current_item_id']}'.")
        st.session_state.pop('admin_current_item_id', None)
        st.session_state.pop('admin_search_results', None)


# --- Hàm chính của trang Admin (được gọi từ main.py) ---
def admin_page():
    if "admin_logged_in" not in st.session_state:
        st.session_state["admin_logged_in"] = False

    if not st.session_state["admin_logged_in"]:
        admin_login_form()
    else:
        admin_dashboard()