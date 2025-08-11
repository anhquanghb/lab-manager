# src/admin_page.py (Đã sửa)

import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os
import shutil

# Import các lớp quản lý và tiện ích
from src.database_manager import DatabaseManager
from src.database_admin import AdminDatabaseManager
from src.common_utils import remove_accents_and_normalize

# --- CẢI TIẾN KIẾN TRÚC ---
# Khởi tạo các đối tượng manager một lần duy nhất và cache lại.
@st.cache_resource
def get_managers():
    """
    Khởi tạo các đối tượng manager. 
    Vì AdminDatabaseManager kế thừa từ DatabaseManager, chúng ta chỉ cần tạo 
    một đối tượng duy nhất là đủ cho mọi tác vụ.
    """
    admin_instance = AdminDatabaseManager()
    return {
        "db_manager": admin_instance,
        "admin_db_manager": admin_instance
    }

# Lấy các đối tượng manager từ cache
managers = get_managers()
db_manager = managers["db_manager"]
admin_db_manager = managers["admin_db_manager"]

def sort_options(options):
    """Sắp xếp danh sách tùy chọn, giữ các giá trị đặc biệt ở đầu."""
    if not options:
        return []
    special_values = [v for v in ["Không rõ", "Không xác định"] if v in options]
    other_values = sorted([v for v in options if v not in special_values and v.strip() != ""])
    return special_values + other_values

def admin_page():
    """Hàm chính để vẽ giao diện trang quản lý."""
    user_role = st.session_state.get("user_role")
    if user_role not in ["moderator", "administrator"]:
        st.warning("Bạn không có quyền truy cập trang này.")
        st.stop()

    st.title("⚙️ Trang Quản lý & Theo dõi Vật tư")

    if "admin_update_mode" not in st.session_state:
        st.session_state["admin_update_mode"] = "none"

    st.markdown("---")
    st.header("Tìm kiếm và Cập nhật theo ID")

    item_id_to_find = st.text_input(
        "Nhập ID vật tư/hóa chất cần tìm:", 
        key="admin_search_id_input"
    )
    
    if st.button("Tìm kiếm theo ID", key="admin_search_button"):
        st.session_state['admin_current_item_id'] = item_id_to_find
        st.session_state['admin_search_results'] = db_manager.get_by_id(item_id_to_find)
        st.session_state['admin_update_mode'] = "none"
        st.rerun()

    if 'admin_search_results' in st.session_state:
        results = st.session_state['admin_search_results']
        if not results.empty:
            item_data = results.iloc[0]
            display_item_details(item_data)
            display_update_forms(item_data)
        elif 'admin_current_item_id' in st.session_state:
            st.warning(f"Không tìm thấy mục nào với ID: '{st.session_state['admin_current_item_id']}'.")

    st.markdown("---")
    st.header("Cập nhật dữ liệu từ file CSV")
    update_data_section()


def update_data_section():
    """Hiển thị giao diện cho phép admin cập nhật toàn bộ dữ liệu từ file CSV."""
    # Hoãn việc import convert_data để tránh lỗi circular import
    from src.convert_data import convert_csv_to_json_data

    with st.expander("Cập nhật toàn bộ dữ liệu (Import từ CSV)", expanded=False):
        uploaded_file = st.file_uploader("Tải lên file CSV mới:", type=['csv'])

        if uploaded_file is not None:
            if st.button("Xử lý và Cập nhật dữ liệu"):
                with st.spinner("Đang xử lý dữ liệu từ CSV..."):
                    try:
                        # Chuyển đổi dữ liệu từ CSV sang định dạng JSON
                        df_csv = pd.read_csv(uploaded_file)
                        new_data = convert_csv_to_json_data(df_csv)
                        
                        # Backup file inventory.json hiện tại
                        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                        old_file_path = admin_db_manager.data_path
                        backup_file_path = os.path.join(
                            os.path.dirname(old_file_path),
                            f"inventory_{timestamp_str}.json"
                        )
                        
                        if os.path.exists(old_file_path):
                            shutil.copyfile(old_file_path, backup_file_path)
                            st.success(f"Đã sao lưu file cũ thành: `{os.path.basename(backup_file_path)}`")
                        
                        # Lưu dữ liệu mới vào inventory.json và đẩy lên GitHub
                        commit_message = f"feat(data): Cập nhật dữ liệu tồn kho từ CSV ngày {datetime.now().strftime('%d-%m-%Y')}"
                        if admin_db_manager.save_and_push_json(old_file_path, new_data, commit_message):
                            st.session_state['admin_search_results'] = pd.DataFrame()
                            st.session_state['admin_current_item_id'] = None
                            st.cache_resource.clear()
                            st.rerun()
                        else:
                            st.error("Có lỗi xảy ra khi lưu hoặc đẩy dữ liệu mới.")

                    except Exception as e:
                        st.error(f"Lỗi khi xử lý file: {e}")

def display_item_details(item_data):
    """Hiển thị thông tin chi tiết của vật phẩm được tìm thấy."""
    st.subheader(f"Thông tin mục: {item_data['name']} (ID: {item_data['id']})")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Loại:** {item_data.get('type', 'N/A')}")
        st.write(f"**Số lượng:** {item_data.get('quantity', 'N/A')} {item_data.get('unit', '')}")
        st.write(f"**Vị trí:** {item_data.get('location', 'N/A')}")
        st.write(f"**Tình trạng:** {item_data.get('status', 'N/A')}")
    with col2:
        st.write(f"**Số CAS:** {item_data.get('cas_number', 'N/A')}")
        st.write(f"**Công thức:** {item_data.get('chemical_formula', 'N/A')}")
        st.write(f"**Theo dõi:** {item_data.get('tracking', 'N/A')}")
        st.write(f"**Ghi chú:** {item_data.get('note', 'N/A')}")

    st.markdown("---")
    st.subheader("Chọn thông tin cần cập nhật")
    
    b_col1, b_col2, b_col3 = st.columns(3)
    if b_col1.button("Cập nhật Vị trí", key="update_location_button"):
        st.session_state["admin_update_mode"] = "location"
        st.rerun()
    if b_col2.button("Cập nhật Số lượng", key="update_quantity_button"):
        st.session_state["admin_update_mode"] = "quantity"
        st.rerun()
    if b_col3.button("Cập nhật Theo dõi & Ghi chú", key="update_tracking_button_main"):
        st.session_state["admin_update_mode"] = "tracking"
        st.rerun()

def display_update_forms(item_data):
    """Hiển thị form cập nhật tương ứng với lựa chọn của người dùng."""
    update_mode = st.session_state.get("admin_update_mode", "none")
    
    if update_mode == "tracking":
        update_tracking_form(item_data)
    elif update_mode == "location":
        update_location_form(item_data)
    elif update_mode == "quantity":
        update_quantity_form(item_data)

def update_tracking_form(item_data):
    """Form để cập nhật trạng thái theo dõi và ghi chú."""
    with st.form("update_tracking_form"):
        st.markdown("##### Cập nhật trạng thái Theo dõi & Ghi chú")
        
        tracking_statuses = db_manager.get_tracking_statuses_from_config()
        current_status = item_data.get('tracking')
        try:
            default_index = tracking_statuses.index(current_status)
        except (ValueError, TypeError):
            default_index = 0

        selected_status = st.selectbox(
            "Trạng thái Theo dõi mới:",
            options=tracking_statuses,
            index=default_index
        )

        new_note_input = st.text_area("Thêm ghi chú mới (để trống nếu không có):")
        
        submitted = st.form_submit_button("Lưu và Đẩy lên GitHub")
        if submitted:
            handle_update(item_data['id'], {
                "tracking": selected_status, 
                "note": new_note_input
            })

def update_location_form(item_data):
    """Form để cập nhật vị trí."""
    with st.form("update_location_form"):
        st.markdown("##### Cập nhật Vị trí")
        
        locations = db_manager.get_all_locations_from_config()
        current_location = item_data.get('location')
        try:
            default_index = locations.index(current_location)
        except (ValueError, TypeError):
            default_index = 0
            
        selected_location = st.selectbox(
            "Vị trí mới:",
            options=locations,
            index=default_index
        )
        
        submitted = st.form_submit_button("Lưu và Đẩy lên GitHub")
        if submitted:
            handle_update(item_data['id'], {"location": selected_location})

def update_quantity_form(item_data):
    """Form để cập nhật số lượng."""
    with st.form("update_quantity_form"):
        st.markdown("##### Cập nhật Số lượng")

        new_quantity = st.number_input(
            "Số lượng mới:",
            value=float(item_data.get('quantity', 0)),
            min_value=0.0,
            step=1.0
        )
        
        units = db_manager.get_all_units_from_config()
        current_unit = item_data.get('unit')
        try:
            default_index = units.index(current_unit)
        except (ValueError, TypeError):
            default_index = 0

        selected_unit = st.selectbox(
            "Đơn vị mới:",
            options=units,
            index=default_index
        )
        
        submitted = st.form_submit_button("Lưu và Đẩy lên GitHub")
        if submitted:
            handle_update(item_data['id'], {"quantity": new_quantity, "unit": selected_unit})

def handle_update(item_id, updates):
    """Hàm xử lý logic cập nhật chung."""
    with st.spinner("Đang xử lý..."):
        idx_to_update = db_manager.inventory_data[db_manager.inventory_data['id'] == item_id].index
        if idx_to_update.empty:
            st.error("Lỗi: Không tìm thấy ID để cập nhật.")
            return

        if "note" in updates and updates["note"].strip():
            old_note = db_manager.inventory_data.loc[idx_to_update[0], 'note']
            if pd.isna(old_note): old_note = ""
            
            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
            new_dated_note = f"{timestamp}: {updates['note'].strip()}"
            final_note_value = f"{old_note}\n{new_dated_note}".strip()
            
            db_manager.inventory_data.loc[idx_to_update, 'note'] = final_note_value
            db_manager.inventory_data.loc[idx_to_update, 'note_normalized'] = remove_accents_and_normalize(final_note_value)
        
        for key, value in updates.items():
            if key != "note":
                db_manager.inventory_data.loc[idx_to_update, key] = value
                if f"{key}_normalized" in db_manager.inventory_data.columns:
                    db_manager.inventory_data.loc[idx_to_update, f"{key}_normalized"] = remove_accents_and_normalize(value)

        data_to_save = db_manager.inventory_data.to_dict(orient='records')
        commit_message = f"feat(admin): Cập nhật thông tin cho ID {item_id}"
        if admin_db_manager.save_and_push_json(admin_db_manager.data_path, data_to_save, commit_message):
            st.success("Đã đẩy thay đổi lên GitHub thành công!")
            st.session_state['admin_search_results'] = db_manager.get_by_id(item_id)
            st.session_state['admin_update_mode'] = "none"
            st.cache_resource.clear()
            st.rerun()
        else:
            st.error("Lỗi: Không thể đẩy thay đổi lên GitHub.")