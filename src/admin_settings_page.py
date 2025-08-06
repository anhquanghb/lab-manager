import streamlit as st
import pandas as pd
from src.database_manager import DatabaseManager
from src.database_admin import AdminDatabaseManager
from src.common_utils import remove_accents_and_normalize
import json

def admin_settings_page(db_manager: DatabaseManager, admin_db_manager: AdminDatabaseManager):
    st.title("🛠️ Cài đặt hệ thống")
    st.write("Quản lý các danh sách cấu hình hệ thống.")

    def save_settings_and_push(config_key, new_list):
        """Hàm trợ giúp để lưu và đẩy cấu hình."""
        # 1. Cập nhật trên bộ nhớ
        db_manager.config_data[config_key] = new_list
        # 2. Lưu vào file JSON
        if admin_db_manager.save_config_to_json():
            st.success("Đã lưu thay đổi vào file config.json.")
            # 3. Đẩy lên GitHub
            commit_message = f"feat(config): Update list '{config_key}'"
            if admin_db_manager.push_to_github(admin_db_manager.config_path, commit_message):
                st.success("Đã đẩy thay đổi cấu hình lên GitHub thành công!")
                # Xóa cache để các trang khác tải lại cấu hình mới
                st.cache_resource.clear()
                st.rerun()
            else:
                st.error("Lỗi: Không thể đẩy thay đổi lên GitHub.")
        else:
            st.error("Lỗi: Không thể lưu thay đổi vào file config.json.")

    def display_list_editor(title, config_key, current_list):
        st.subheader(title)
        
        # Hiển thị danh sách hiện tại
        st.code(", ".join(current_list))
        
        col1, col2 = st.columns([0.8, 0.2])
        with col1:
            new_item = st.text_input(f"Thêm mục mới vào danh sách '{title}':", key=f"add_{config_key}_input")
        with col2:
            st.markdown("<br>", unsafe_allow_html=True) # Tạo khoảng trống
            if st.button(f"Thêm", key=f"add_{config_key}_button"):
                if new_item:
                    new_list = current_list + [new_item.strip()]
                    save_settings_and_push(config_key, sorted(new_list))
                else:
                    st.warning("Vui lòng nhập một giá trị.")
        
        # Tùy chọn để xóa các mục hiện có (đơn giản hóa bằng cách xóa)
        st.markdown("---")
        st.markdown(f"**Xóa mục khỏi danh sách '{title}'**")
        item_to_remove = st.selectbox("Chọn mục để xóa:", options=[""] + current_list, key=f"remove_{config_key}_select")
        if item_to_remove and st.button("Xóa", key=f"remove_{config_key}_button"):
            new_list = [item for item in current_list if item != item_to_remove]
            save_settings_and_push(config_key, sorted(new_list))

    st.markdown("---")
    display_list_editor("Vị trí", "locations", db_manager.config_data.get('locations', []))
    st.markdown("---")
    display_list_editor("Đơn vị", "units", db_manager.config_data.get('units', []))
    st.markdown("---")
    display_list_editor("Trạng thái (tracking)", "tracking_statuses", db_manager.config_data.get('tracking_statuses', []))
    st.markdown("---")
    display_list_editor("Mục đích", "purposes", db_manager.config_data.get('purposes', []))
    st.markdown("---")
    display_list_editor("Tình trạng", "statuses", db_manager.config_data.get('statuses', []))