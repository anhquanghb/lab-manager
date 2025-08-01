import streamlit as st
import pandas as pd
from src.database_manager import DatabaseManager
from src.database_admin import AdminDatabaseManager
import os
from pathlib import Path
from src.common_utils import remove_accents_and_normalize
from datetime import datetime
import re

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

managers = get_managers()
db_manager = managers["db_manager"]
admin_db_manager = managers["admin_db_manager"]

# --- Lấy mật khẩu từ Streamlit secrets ---
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD")

# Danh sách các trạng thái Tracking hợp lệ
VALID_TRACKING_STATUSES = [
    "Còn nguyên",
    "Đã mở",
    "Đang mượn",
    "Hết",
    "Thất lạc",
    "Hư hỏng",
    "Đang gửi/sửa",
    "Không rõ"
]

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
    st.title("⚙️ Trang Theo dõi - Quản lý Vật tư & Hóa chất")

    if st.button("Đăng xuất Admin"):
        st.session_state["admin_logged_in"] = False
        st.rerun()

    st.markdown("---")
    st.header("Tìm kiếm và Cập nhật Tracking")

    item_id_to_find = st.text_input("Nhập ID vật tư/hóa chất cần tìm (ví dụ: A001A, ITEM_1):", key="admin_search_id_input")
    
    search_button = st.button("Tìm kiếm theo ID", key="admin_search_button")

    if search_button and item_id_to_find:
        st.session_state['admin_current_item_id'] = item_id_to_find
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
        st.write(f"**Theo dõi (Trạng thái):** {item_data['tracking'] if pd.notna(item_data['tracking']) else 'N/A'}")
        st.write(f"**Ghi chú:** {item_data['note'] if pd.notna(item_data['note']) else 'N/A'}")
        
        st.markdown("---")
        st.subheader("Cập nhật Tracking")

        current_tracking_status = item_data['tracking'] if pd.notna(item_data['tracking']) else "Không rõ"
        try:
            default_index_status = VALID_TRACKING_STATUSES.index(current_tracking_status)
        except ValueError:
            default_index_status = VALID_TRACKING_STATUSES.index("Không rõ")

        selected_tracking_status = st.selectbox(
            f"Chọn trạng thái Theo dõi cho ID '{item_data['id']}'",
            options=VALID_TRACKING_STATUSES,
            index=default_index_status,
            key="selected_tracking_status_selectbox"
        )

        current_note_value = item_data['note'] if pd.notna(item_data['note']) else ""
        
        new_note_input = st.text_area(
            "Thêm ghi chú:", # Bỏ chữ "tùy chọn" vì nó sẽ luôn có ngày
            value=current_note_value,
            key="tracking_note_input"
        )
        
        if st.button("Lưu và Đẩy lên GitHub", key="update_tracking_button"):
            current_date = datetime.now().strftime("%d/%m/%Y")
            
            # Thay đổi logic này: note sẽ luôn có ngày tháng, ngay cả khi new_note_input rỗng
            # Nếu new_note_input rỗng, note sẽ chỉ là "- DD/MM/YYYY"
            # Nếu new_note_input có giá trị, note sẽ là "[giá_trị] - DD/MM/YYYY"
            final_note_value = f"{new_note_input.strip()} - {current_date}" if new_note_input.strip() else f"- {current_date}"
            # Bạn có thể cân nhắc nếu muốn ghi chú rỗng hoàn toàn thì không có ngày:
            # final_note_value = f"{new_note_input.strip()} - {current_date}" if new_note_input.strip() else None


            idx_to_update = db_manager.inventory_data[db_manager.inventory_data['id'] == item_data['id']].index
        
            if not idx_to_update.empty:
                db_manager.inventory_data.loc[idx_to_update, 'tracking'] = selected_tracking_status
                db_manager.inventory_data.loc[idx_to_update, 'tracking_normalized'] = remove_accents_and_normalize(selected_tracking_status)
                db_manager.inventory_data.loc[idx_to_update, 'note'] = final_note_value
                db_manager.inventory_data.loc[idx_to_update, 'note_normalized'] = remove_accents_and_normalize(final_note_value)

                st.success(f"Thông tin theo dõi và ghi chú cho ID '{item_data['id']}' đã được cập nhật trên bộ nhớ.")
                
                if admin_db_manager.save_inventory_to_json():
                    st.success("Đã lưu thay đổi vào file inventory.json.")
                    
                    commit_message = f"feat(admin): Update tracking and note for ID {item_data['id']}"
                    if admin_db_manager.push_inventory_to_github(commit_message):
                        st.success("Đã đẩy thay đổi lên GitHub thành công!")
                    else:
                        st.error("Lỗi: Không thể đẩy thay đổi lên GitHub. Vui lòng kiểm tra console log.")
                else:
                    st.error("Lỗi: Không thể lưu thay đổi vào file inventory.json.")
                
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