# src/admin_settings_page.py

import streamlit as st
from src.database_manager import DatabaseManager
from src.database_admin import AdminDatabaseManager



# --- CÁC HÀM TRỢ GIÚP ---

def save_settings_and_push(config_key, new_value, admin_db_manager, db_manager, is_list=True):
    """Hàm chung để lưu một cài đặt, đẩy lên GitHub và chạy lại ứng dụng."""
    if is_list:
        db_manager.config_data[config_key] = sorted(new_value)
    else:
        db_manager.config_data[config_key] = new_value

    if admin_db_manager.save_config_to_json():
        st.success("Đã lưu thay đổi vào file config.json.")
        commit_message = f"feat(config): Cập nhật cài đặt '{config_key}'"
        if admin_db_manager.push_to_github(admin_db_manager.config_path, commit_message):
            st.success("Đã đẩy thay đổi lên GitHub! Ứng dụng sẽ tải lại để áp dụng.")
            st.cache_resource.clear() # Xóa cache để đảm bảo các manager được tải lại với config mới
            st.rerun()
        else:
            st.error("Lỗi: Không thể đẩy thay đổi lên GitHub.")
    else:
        st.error("Lỗi: Không thể lưu thay đổi vào file config.json.")

def display_list_editor(title, config_key, current_list, db_manager, admin_db_manager):
    """Hiển thị giao diện để thêm/xóa các mục trong một danh sách cấu hình."""
    st.subheader(title)
    
    # Hiển thị danh sách hiện tại
    if current_list:
        st.code(", ".join(current_list))
    else:
        st.info("Danh sách này hiện đang trống.")

    # Form thêm mục mới
    with st.form(key=f"add_{config_key}_form"):
        new_item = st.text_input(f"Thêm mục mới vào '{title}':", key=f"add_{config_key}_input")
        submitted_add = st.form_submit_button("Thêm")
        if submitted_add and new_item.strip():
            new_list = current_list + [new_item.strip()]
            save_settings_and_push(config_key, new_list, admin_db_manager, db_manager)
        elif submitted_add:
            st.warning("Vui lòng nhập một giá trị.")
    
    # Form xóa mục
    if current_list:
        with st.form(key=f"remove_{config_key}_form"):
            item_to_remove = st.selectbox("Chọn mục để xóa:", options=[""] + current_list, key=f"remove_{config_key}_select")
            submitted_remove = st.form_submit_button("Xóa mục đã chọn")
            if submitted_remove and item_to_remove:
                # Kiểm tra đặc biệt cho 'locations' để tránh xóa vị trí đang được sử dụng
                if config_key == "locations":
                    items_in_location = db_manager.inventory_data[db_manager.inventory_data['location'] == item_to_remove]
                    if not items_in_location.empty:
                        st.error(f"Lỗi: Không thể xóa '{item_to_remove}' vì còn {len(items_in_location)} mục đang ở vị trí này.")
                        return # Dừng lại không cho xóa
                
                new_list = [item for item in current_list if item != item_to_remove]
                save_settings_and_push(config_key, new_list, admin_db_manager, db_manager)
            elif submitted_remove:
                st.warning("Vui lòng chọn một mục để xóa.")

# --- CÁC THÀNH PHẦN GIAO DIỆN ---

def display_system_settings(db_manager: DatabaseManager, admin_db_manager: AdminDatabaseManager):
    """Hiển thị các cài đặt hệ thống như Site URL và Gemini API."""
    st.header("⚙️ Cài đặt hệ thống & API")

    with st.form("system_settings_form"):
        st.subheader("Cấu hình URL (Redirect URI)")
        st.info("URL này phải khớp với 'Authorized redirect URI' trên Google Cloud Console.")
        current_site_url = db_manager.config_data.get("site_url", "http://localhost:8501")
        new_site_url = st.text_input("Site URL:", value=current_site_url)

        st.markdown("---")
        st.subheader("Cài đặt API Gemini & Prompt")
        current_api_key = db_manager.config_data.get('gemini_api_key', '')
        new_api_key = st.text_input("Gemini API Key:", value=current_api_key, type="password")
        
        current_model = db_manager.config_data.get('gemini_model_name', 'gemini-1.5-flash')
        new_model = st.text_input("Tên mô hình Gemini:", value=current_model)
        
        current_prompt = db_manager.config_data.get('ai_full_prompt', '')
        new_prompt = st.text_area("Full Prompt của Trợ lý AI:", value=current_prompt, height=300)

        submitted = st.form_submit_button("Lưu tất cả cài đặt hệ thống")
        if submitted:
            # Tạo một từ điển chứa các cập nhật
            updates = {
                "site_url": new_site_url.strip(),
                "gemini_api_key": new_api_key.strip(),
                "gemini_model_name": new_model.strip(),
                "ai_full_prompt": new_prompt.strip()
            }
            # Cập nhật tất cả các giá trị vào config data
            for key, value in updates.items():
                db_manager.config_data[key] = value
            
            # Lưu một lần
            save_settings_and_push("system_settings", db_manager.config_data, admin_db_manager, db_manager, is_list=False)

def admin_settings_page(db_manager: DatabaseManager, admin_db_manager: AdminDatabaseManager):
    """Hàm chính, entry point của trang cài đặt."""
    st.title("🛠️ Bảng điều khiển Cài đặt")

    # Kiểm tra quyền truy cập
    if st.session_state.get("user_role") != "administrator":
        st.warning("Bạn không có quyền truy cập trang này.")
        st.stop()

    # Hiển thị các cài đặt hệ thống & API
    display_system_settings(db_manager, admin_db_manager)
    st.markdown("---")

    # Hiển thị các trình chỉnh sửa danh sách
    st.header("📝 Quản lý các danh sách lựa chọn")
    display_list_editor("Vị trí", "locations", db_manager.config_data.get('locations', []), db_manager, admin_db_manager)
    st.markdown("---")
    display_list_editor("Đơn vị", "units", db_manager.config_data.get('units', []), db_manager, admin_db_manager)
    st.markdown("---")
    display_list_editor("Trạng thái Theo dõi", "tracking_statuses", db_manager.config_data.get('tracking_statuses', []), db_manager, admin_db_manager)
    st.markdown("---")
    display_list_editor("Mục đích", "purposes", db_manager.config_data.get('purposes', []), db_manager, admin_db_manager)
    st.markdown("---")
    display_list_editor("Tình trạng", "statuses", db_manager.config_data.get('statuses', []), db_manager, admin_db_manager)

# --- TÍNH NĂNG MỚI: KHU VỰC NHẬP/XUẤT DỮ LIỆU ---
def display_data_import_export(db_manager: DatabaseManager, admin_db_manager: AdminDatabaseManager):
    st.header("📦 Nhập & Xuất dữ liệu hàng loạt (CSV)")

    st.info(
        "Chức năng này cho phép bạn xuất toàn bộ dữ liệu kho ra file CSV, "
        "chỉnh sửa hàng loạt bằng Excel/Google Sheets, sau đó nhập lại để cập nhật hệ thống."
    )

    # --- CHỨC NĂNG XUẤT (EXPORT) ---
    st.subheader("1. Xuất dữ liệu ra file CSV")
    
    # Lấy dữ liệu dataframe gốc (không có các cột _normalized)
    original_cols = [
        'id', 'name', 'type', 'quantity', 'unit', 'location', 'description',
        'iupac_name', 'vietnamese_name', 'chemical_formula', 'cas_number',
        'state_or_concentration', 'status', 'purpose', 'tracking', 'note'
    ]
    cols_to_export = [col for col in original_cols if col in db_manager.inventory_data.columns]
    df_to_export = db_manager.inventory_data[cols_to_export]
    
    # Chuyển đổi dataframe thành dữ liệu CSV
    csv_data = df_to_export.to_csv(index=False).encode('utf-8')
    
    st.download_button(
        label="📥 Tải xuống Danhmuc.csv",
        data=csv_data,
        file_name='Danhmuc.csv',
        mime='text/csv',
    )
    
    st.markdown("---")

    # --- CHỨC NĂNG NHẬP (IMPORT) ---
    st.subheader("2. Nhập dữ liệu từ file CSV")
    st.warning(
        "**QUAN TRỌNG:** Chức năng này sẽ **GHI ĐÈ** toàn bộ dữ liệu kho hiện tại của bạn. "
        "Hãy chắc chắn về nội dung file bạn tải lên."
    )
    
    uploaded_file = st.file_uploader(
        "Kéo và thả hoặc chọn file Danhmuc.csv đã chỉnh sửa của bạn vào đây",
        type=['csv']
    )
    
    if uploaded_file is not None:
        try:
            new_df = pd.read_csv(uploaded_file)
            
            # Kiểm tra các cột tối thiểu phải có
            required_cols = {'id', 'name'}
            if not required_cols.issubset(new_df.columns):
                st.error(f"Lỗi: File CSV phải chứa ít nhất các cột: {', '.join(required_cols)}")
            else:
                st.write("Xem trước 5 dòng đầu của dữ liệu mới:")
                st.dataframe(new_df.head())
                
                if st.button("XÁC NHẬN VÀ GHI ĐÈ DỮ LIỆU"):
                    with st.spinner("Đang xử lý..."):
                        # Ghi đè dữ liệu trong bộ nhớ
                        admin_db_manager.inventory_data = new_df
                        
                        # Lưu file inventory.json mới
                        if admin_db_manager.save_inventory_to_json():
                            st.success("Đã ghi đè và lưu file inventory.json thành công.")
                            
                            # Push file mới lên GitHub
                            commit_message = "feat(data): Cập nhật dữ liệu kho từ file CSV"
                            if admin_db_manager.push_to_github(admin_db_manager.data_path, commit_message):
                                st.success("Đã đẩy dữ liệu mới lên GitHub! Ứng dụng sẽ tải lại.")
                                st.cache_resource.clear()
                                st.rerun()
                            else:
                                st.error("Đẩy file inventory.json lên GitHub thất bại.")
                        else:
                            st.error("Lưu file inventory.json thất bại.")

        except Exception as e:
            st.error(f"Đã xảy ra lỗi khi đọc file CSV: {e}")