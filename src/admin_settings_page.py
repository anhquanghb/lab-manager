# src/admin_settings_page.py

import streamlit as st
import pandas as pd
from src.database_manager import DatabaseManager
from src.database_admin import AdminDatabaseManager
from src.common_utils import remove_accents_and_normalize
from src.admin_page import admin_login_form
import json

def display_gemini_api_setting(db_manager: DatabaseManager, admin_db_manager: AdminDatabaseManager):
    st.header("🔑 Cài đặt API Gemini")
    
    current_gemini_api_key = db_manager.config_data.get('gemini_api_key', '')
    
    new_gemini_api_key = st.text_input(
        "Nhập Gemini API Key (để trống nếu muốn người dùng tự nhập):", 
        value=current_gemini_api_key, 
        type="password", 
        key="gemini_api_key_input"
    )
    
    if st.button("Lưu API Key Gemini và Đẩy lên GitHub", key="save_gemini_api_button"):
        db_manager.config_data['gemini_api_key'] = new_gemini_api_key.strip()
        if admin_db_manager.save_config_to_json():
            st.success("Đã lưu Gemini API Key vào file config.json.")
            commit_message = f"feat(config): Update Gemini API key"
            if admin_db_manager.push_to_github(admin_db_manager.config_path, commit_message):
                st.success("Đã đẩy thay đổi cấu hình lên GitHub thành công!")
                st.cache_resource.clear()
                st.rerun()
            else:
                st.error("Lỗi: Không thể đẩy thay đổi lên GitHub.")
        else:
            st.error("Lỗi: Không thể lưu thay đổi vào file config.json.")

def sort_options(options):
    if not options:
        return []
    special_values = [v for v in ["Không rõ", "Không xác định"] if v in options]
    other_values = sorted([v for v in options if v not in special_values and v.strip() != ""])
    return special_values + other_values

def display_settings_dashboard(db_manager: DatabaseManager, admin_db_manager: AdminDatabaseManager):
    st.title("🛠️ Cài đặt hệ thống")
    st.write("Quản lý các danh sách cấu hình hệ thống.")

    def save_settings_and_push(config_key, new_list):
        db_manager.config_data[config_key] = new_list
        if admin_db_manager.save_config_to_json():
            st.success("Đã lưu thay đổi vào file config.json.")
            commit_message = f"feat(config): Update list '{config_key}'"
            if admin_db_manager.push_to_github(admin_db_manager.config_path, commit_message):
                st.success("Đã đẩy thay đổi cấu hình lên GitHub thành công!")
                st.cache_resource.clear()
                st.rerun()
            else:
                st.error("Lỗi: Không thể đẩy thay đổi lên GitHub.")
        else:
            st.error("Lỗi: Không thể lưu thay đổi vào file config.json.")

    def display_list_editor(title, config_key, current_list):
        st.subheader(title)
        
        st.code(", ".join(current_list))
        
        col1, col2 = st.columns([0.8, 0.2])
        with col1:
            new_item = st.text_input(f"Thêm mục mới vào danh sách '{title}':", key=f"add_{config_key}_input")
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button(f"Thêm", key=f"add_{config_key}_button"):
                if new_item:
                    new_list = current_list + [new_item.strip()]
                    save_settings_and_push(config_key, sorted(new_list))
                else:
                    st.warning("Vui lòng nhập một giá trị.")
        
        st.markdown("---")
        st.markdown(f"**Xóa mục khỏi danh sách '{title}'**")
        item_to_remove = st.selectbox("Chọn mục để xóa:", options=[""] + current_list, key=f"remove_{config_key}_select")
        if item_to_remove and st.button("Xóa", key=f"remove_{config_key}_button"):
            if config_key == "locations":
                items_in_location = db_manager.inventory_data[db_manager.inventory_data['location'] == item_to_remove]
                if not items_in_location.empty:
                    st.error(f"Lỗi: Không thể xóa vị trí '{item_to_remove}' vì còn {len(items_in_location)} mục đang được gán tại đây. Vui lòng thay đổi vị trí của các mục này trước khi xóa.")
                    return
            
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
    
    st.markdown("---")
    st.header("🔑 Cài đặt API Gemini")
    current_gemini_api_key = db_manager.config_data.get('gemini_api_key', '')

    new_gemini_api_key = st.text_input("Nhập Gemini API Key (để trống nếu muốn người dùng tự nhập):", 
                                    value=current_gemini_api_key, 
                                    type="password", 
                                    key="gemini_api_key_input")

    if st.button("Lưu API Key Gemini và Đẩy lên GitHub", key="save_gemini_api_button"):
        db_manager.config_data['gemini_api_key'] = new_gemini_api_key.strip()
        if admin_db_manager.save_config_to_json():
            st.success("Đã lưu Gemini API Key vào file config.json.")
            commit_message = f"feat(config): Update Gemini API key"
            if admin_db_manager.push_to_github(admin_db_manager.config_path, commit_message):
                st.success("Đã đẩy thay đổi cấu hình lên GitHub thành công!")
                st.cache_resource.clear()
                st.rerun()
            else:
                st.error("Lỗi: Không thể đẩy thay đổi lên GitHub.")
        else:
            st.error("Lỗi: Không thể lưu thay đổi vào file config.json.")

def admin_settings_page(db_manager: DatabaseManager, admin_db_manager: AdminDatabaseManager):
    if "admin_logged_in" not in st.session_state:
        st.session_state["admin_logged_in"] = False

    if not st.session_state["admin_logged_in"]:
        from src.admin_page import admin_login_form
        admin_login_form()
    else:
        display_settings_dashboard(db_manager, admin_db_manager)