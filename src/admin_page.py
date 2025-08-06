import streamlit as st
import pandas as pd
from src.database_manager import DatabaseManager
from src.database_admin import AdminDatabaseManager
import os
from pathlib import Path
from src.common_utils import remove_accents_and_normalize
from datetime import datetime
import re

@st.cache_resource
def get_managers():
    db_instance = DatabaseManager()
    admin_db_instance = AdminDatabaseManager(db_instance)
    return {
        "db_manager": db_instance,
        "admin_db_manager": admin_db_instance
    }

managers = get_managers()
db_manager = managers["db_manager"]
admin_db_manager = managers["admin_db_manager"]

ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD")

# BỎ DÒNG NÀY: VALID_TRACKING_STATUSES = [...] và lấy từ db_manager.config_data

def admin_login_form():
    st.title("🔐 Đăng nhập Admin")
    password = st.text_input("Nhập mật khẩu:", type="password")
    if st.button("Đăng nhập"):
        if password == ADMIN_PASSWORD:
            st.session_state["admin_logged_in"] = True
            st.rerun()
        else:
            st.error("Mật khẩu không đúng. Vui lòng thử lại.")

def admin_dashboard():
    st.title("⚙️ Trang Theo dõi - Quản lý Vật tư & Hóa chất")

    if "admin_update_mode" not in st.session_state:
        st.session_state["admin_update_mode"] = "none"

    if st.button("Đăng xuất Admin"):
        st.session_state["admin_logged_in"] = False
        st.rerun()

    st.markdown("---")
    st.header("Tìm kiếm và Cập nhật")

    item_id_to_find = st.text_input("Nhập ID vật tư/hóa chất cần tìm (ví dụ: A001A, ITEM_1):", key="admin_search_id_input")
    
    search_button = st.button("Tìm kiếm theo ID", key="admin_search_button")

    if search_button and item_id_to_find:
        st.session_state['admin_current_item_id'] = item_id_to_find
        st.session_state['admin_search_results'] = db_manager.get_by_id(item_id_to_find)
        st.session_state['admin_update_mode'] = "none"

    if 'admin_search_results' in st.session_state and not st.session_state['admin_search_results'].empty:
        item_data = st.session_state['admin_search_results'].iloc[0]
        
        st.subheader(f"Thông tin mục: {item_data['name']} (ID: {item_data['id']})")
        st.write(f"**Loại:** {item_data['type']}")
        
        col1, col2 = st.columns([0.4, 0.6])
        with col1:
            st.markdown(f"**Vị trí:** {item_data['location'] if pd.notna(item_data['location']) else 'N/A'}")
        with col2:
            if st.button("Cập nhật Vị trí", key="update_location_button"):
                st.session_state["admin_update_mode"] = "location"
                st.rerun()

        col3, col4 = st.columns([0.4, 0.6])
        with col3:
            st.markdown(f"**Số lượng:** {item_data['quantity'] if pd.notna(item_data['quantity']) else 'N/A'} {item_data['unit'] if pd.notna(item_data['unit']) else ''}")
        with col4:
            if st.button("Cập nhật Số lượng", key="update_quantity_button"):
                st.session_state["admin_update_mode"] = "quantity"
                st.rerun()

        st.write(f"**Công thức:** {item_data['chemical_formula'] if pd.notna(item_data['chemical_formula']) else 'N/A'}")
        st.write(f"**Số CAS:** {item_data['cas_number'] if pd.notna(item_data['cas_number']) else 'N/A'}")
        st.write(f"**Trạng thái/Nồng độ:** {item_data['state_or_concentration'] if pd.notna(item_data['state_or_concentration']) else 'N/A'}")
        st.write(f"**Tình trạng:** {item_data['status'] if pd.notna(item_data['status']) else 'N/A'}")
        st.write(f"**Mục đích:** {item_data['purpose'] if pd.notna(item_data['purpose']) else 'N/A'}")
        
        st.write(f"**Theo dõi (Trạng thái):** {item_data['tracking'] if pd.notna(item_data['tracking']) else 'N/A'}")
        st.write(f"**Ghi chú:** {item_data['note'] if pd.notna(item_data['note']) else 'N/A'}")
        if st.button("Cập nhật Theo dõi", key="update_tracking_button_main"):
            st.session_state["admin_update_mode"] = "tracking"
            st.rerun()

        st.markdown("---")
        st.subheader("Form Cập nhật")

        if st.session_state["admin_update_mode"] == "tracking":
            update_tracking_form(item_data)
        elif st.session_state["admin_update_mode"] == "location":
            update_location_form(item_data)
        elif st.session_state["admin_update_mode"] == "quantity":
            update_quantity_form(item_data)
        else:
            st.info("Chọn một mục để cập nhật.")
            
    elif 'admin_search_results' in st.session_state and st.session_state['admin_search_results'].empty:
        st.warning(f"Không tìm thấy mục với ID: '{st.session_state['admin_current_item_id']}'.")
        st.session_state.pop('admin_current_item_id', None)
        st.session_state.pop('admin_search_results', None)
        st.session_state['admin_update_mode'] = "none"

def update_tracking_form(item_data):
    st.markdown("##### Cập nhật trạng thái Theo dõi")
    
    tracking_statuses = db_manager.config_data.get('tracking_statuses', [])
    current_tracking_status = item_data['tracking'] if pd.notna(item_data['tracking']) else "Không rõ"
    
    try:
        default_index_status = tracking_statuses.index(current_tracking_status)
    except ValueError:
        default_index_status = tracking_statuses.index("Không rõ")

    selected_tracking_status = st.selectbox(
        f"Chọn trạng thái Theo dõi cho ID '{item_data['id']}'",
        options=tracking_statuses,
        index=default_index_status,
        key="selected_tracking_status_selectbox"
    )

    current_note_value = item_data['note'] if pd.notna(item_data['note']) else ""
    
    new_note_input = st.text_area(
        "Thêm ghi chú mới:",
        value="",
        key="tracking_note_input"
    )
    
    if st.button("Lưu và Đẩy lên GitHub", key="update_tracking_button_form"):
        old_note = item_data['note'] if pd.notna(item_data['note']) else ""
        if new_note_input.strip():
            current_date = datetime.now().strftime("%d/%m/%Y")
            new_dated_note = f"{current_date}: {new_note_input.strip()}."
            final_note_value = f"{old_note}\n{new_dated_note}".strip()
        else:
            final_note_value = old_note if old_note else None
        
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
                if admin_db_manager.push_to_github(admin_db_manager.data_path, commit_message):
                    st.success("Đã đẩy thay đổi lên GitHub thành công!")
                else:
                    st.error("Lỗi: Không thể đẩy thay đổi lên GitHub.")
            else:
                st.error("Lỗi: Không thể lưu thay đổi vào file inventory.json.")
            
            st.session_state['admin_search_results'] = db_manager.get_by_id(item_data['id'])
            st.session_state['admin_update_mode'] = "none"
            st.rerun()
        else:
            st.error("Không tìm thấy mục để cập nhật.")

def update_location_form(item_data):
    st.markdown("##### Cập nhật Vị trí")
    
    locations = db_manager.config_data.get('locations', [])
    current_location = item_data['location'] if pd.notna(item_data['location']) else ""
    
    selected_location = st.selectbox(
        f"Chọn Vị trí mới cho ID '{item_data['id']}'",
        options=locations,
        index=locations.index(current_location) if current_location in locations else 0, # Sửa lỗi nếu location không có trong list
        key="new_location_select"
    )

    current_note_value = item_data['note'] if pd.notna(item_data['note']) else ""
    new_note_input = st.text_area(
        "Thêm ghi chú mới:",
        value="",
        key="location_note_input"
    )

    if st.button("Lưu và Đẩy lên GitHub", key="update_location_button_form"):
        if not selected_location:
            st.error("Vị trí không được để trống.")
        else:
            old_note = item_data['note'] if pd.notna(item_data['note']) else ""
            default_note = f"{datetime.now().strftime('%d/%m/%Y')}: Vị trí thay đổi từ '{current_location}' sang '{selected_location}'."
            
            if new_note_input.strip():
                new_dated_note = f"{datetime.now().strftime('%d/%m/%Y')}: {new_note_input.strip()}."
                final_note_value = f"{old_note}\n{new_dated_note}".strip()
            else:
                final_note_value = f"{old_note}\n{default_note}".strip() if old_note else default_note
            
            idx_to_update = db_manager.inventory_data[db_manager.inventory_data['id'] == item_data['id']].index
            if not idx_to_update.empty:
                db_manager.inventory_data.loc[idx_to_update, 'location'] = selected_location
                db_manager.inventory_data.loc[idx_to_update, 'location_normalized'] = remove_accents_and_normalize(selected_location)
                db_manager.inventory_data.loc[idx_to_update, 'note'] = final_note_value
                db_manager.inventory_data.loc[idx_to_update, 'note_normalized'] = remove_accents_and_normalize(final_note_value)
                
                st.success(f"Vị trí và ghi chú cho ID '{item_data['id']}' đã được cập nhật trên bộ nhớ.")
                if admin_db_manager.save_inventory_to_json():
                    st.success("Đã lưu thay đổi vào file inventory.json.")
                    commit_message = f"feat(admin): Update location and note for ID {item_data['id']} to '{selected_location}'"
                    if admin_db_manager.push_to_github(admin_db_manager.data_path, commit_message):
                        st.success("Đã đẩy thay đổi lên GitHub thành công!")
                    else:
                        st.error("Lỗi: Không thể đẩy thay đổi lên GitHub.")
                else:
                    st.error("Lỗi: Không thể lưu thay đổi vào file inventory.json.")
                
                st.session_state['admin_search_results'] = db_manager.get_by_id(item_data['id'])
                st.session_state['admin_update_mode'] = "none"
                st.rerun()
            else:
                st.error("Không tìm thấy mục để cập nhật.")

def update_quantity_form(item_data):
    st.markdown("##### Cập nhật Số lượng")
    
    units = db_manager.config_data.get('units', [])
    current_quantity = item_data['quantity'] if pd.notna(item_data['quantity']) else 0
    current_unit = item_data['unit'] if pd.notna(item_data['unit']) else ""

    new_quantity = st.number_input(
        f"Nhập Số lượng mới cho ID '{item_data['id']}'",
        value=float(current_quantity),
        min_value=0.0,
        step=1.0,
        key="new_quantity_input"
    )

    selected_unit = st.selectbox(
        f"Chọn Đơn vị mới cho ID '{item_data['id']}'",
        options=units,
        index=units.index(current_unit) if current_unit in units else 0, # Sửa lỗi nếu unit không có trong list
        key="new_unit_select"
    )

    current_note_value = item_data['note'] if pd.notna(item_data['note']) else ""
    new_note_input = st.text_area(
        "Thêm ghi chú mới:",
        value="",
        key="quantity_note_input"
    )

    if st.button("Lưu và Đẩy lên GitHub", key="update_quantity_button_form"):
        if new_quantity < 0:
            st.error("Số lượng không được âm.")
        else:
            old_note = item_data['note'] if pd.notna(item_data['note']) else ""
            default_note = f"{datetime.now().strftime('%d/%m/%Y')}: Cập nhật số lượng mới."

            if new_note_input.strip():
                new_dated_note = f"{datetime.now().strftime('%d/%m/%Y')}: {new_note_input.strip()}."
                final_note_value = f"{old_note}\n{new_dated_note}".strip()
            else:
                final_note_value = f"{old_note}\n{default_note}".strip() if old_note else default_note
            
            idx_to_update = db_manager.inventory_data[db_manager.inventory_data['id'] == item_data['id']].index
            if not idx_to_update.empty:
                db_manager.inventory_data.loc[idx_to_update, 'quantity'] = new_quantity
                db_manager.inventory_data.loc[idx_to_update, 'unit'] = selected_unit
                db_manager.inventory_data.loc[idx_to_update, 'note'] = final_note_value
                db_manager.inventory_data.loc[idx_to_update, 'note_normalized'] = remove_accents_and_normalize(final_note_value)
                
                st.success(f"Số lượng, đơn vị và ghi chú cho ID '{item_data['id']}' đã được cập nhật trên bộ nhớ.")
                if admin_db_manager.save_inventory_to_json():
                    st.success("Đã lưu thay đổi vào file inventory.json.")
                    commit_message = f"feat(admin): Update quantity and note for ID {item_data['id']} to '{new_quantity} {selected_unit}'"
                    if admin_db_manager.push_to_github(admin_db_manager.data_path, commit_message):
                        st.success("Đã đẩy thay đổi lên GitHub thành công!")
                    else:
                        st.error("Lỗi: Không thể đẩy thay đổi lên GitHub.")
                else:
                    st.error("Lỗi: Không thể lưu thay đổi vào file inventory.json.")
                
                st.session_state['admin_search_results'] = db_manager.get_by_id(item_data['id'])
                st.session_state['admin_update_mode'] = "none"
                st.rerun()
            else:
                st.error("Không tìm thấy mục để cập nhật.")


def admin_page():
    if "admin_logged_in" not in st.session_state:
        st.session_state["admin_logged_in"] = False

    if not st.session_state["admin_logged_in"]:
        admin_login_form()
    else:
        admin_dashboard()