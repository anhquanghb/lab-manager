# src/statistics_page.py

import streamlit as st
import pandas as pd
from src.database_manager import DatabaseManager # Import DatabaseManager

# --- Khởi tạo DatabaseManager (chỉ một lần và được cache) ---
@st.cache_resource
def get_db_manager():
    return DatabaseManager()

db_manager = get_db_manager()

def statistics_page():
    st.title("📊 Thống kê Vật tư & Hóa chất")
    st.write("Xem thống kê và lọc dữ liệu tồn kho theo loại, vị trí hoặc trạng thái theo dõi.")

    if db_manager.inventory_data.empty:
        st.warning("Không có dữ liệu tồn kho để hiển thị thống kê.")
        return

    # Lấy danh sách các giá trị duy nhất cho các bộ lọc
    all_types = ['Tất cả'] + db_manager.inventory_data['type'].dropna().unique().tolist()
    all_locations = ['Tất cả'] + db_manager.get_all_locations() # Sử dụng hàm có sẵn
    all_tracking_statuses_raw = db_manager.inventory_data['tracking'].dropna().unique().tolist()
    
    # Trích xuất các trạng thái chính từ cột tracking (trước " - Note: ")
    unique_tracking_statuses = set()
    for status_entry in all_tracking_statuses_raw:
        main_status = status_entry.split(" - Note:")[0].strip()
        unique_tracking_statuses.add(main_status)
    all_tracking_statuses = ['Tất cả'] + sorted(list(unique_tracking_statuses))

    # Bộ lọc
    selected_type = st.selectbox("Lọc theo Loại:", options=all_types)
    selected_location = st.selectbox("Lọc theo Vị trí:", options=all_locations)
    selected_tracking = st.selectbox("Lọc theo Theo dõi:", options=all_tracking_statuses)

    filtered_df = db_manager.inventory_data.copy()

    # Áp dụng bộ lọc
    if selected_type != 'Tất cả':
        filtered_df = filtered_df[filtered_df['type'] == selected_type]

    if selected_location != 'Tất cả':
        filtered_df = filtered_df[filtered_df['location'] == selected_location]

    if selected_tracking != 'Tất cả':
        # Đối với tracking, cần kiểm tra phần đầu của chuỗi (trước " - Note: ")
        filtered_df = filtered_df[
            filtered_df['tracking'].fillna('').apply(lambda x: x.split(" - Note:")[0].strip() == selected_tracking)
        ]

    st.markdown("---")
    st.subheader("Kết quả Thống kê")

    if filtered_df.empty:
        st.info("Không có dữ liệu phù hợp với các tiêu chí lọc đã chọn.")
    else:
        st.write(f"Tìm thấy **{len(filtered_df)}** mục phù hợp:")
        
        # Hiển thị DataFrame
        st.dataframe(filtered_df[[
            'id', 'name', 'type', 'quantity', 'unit', 'location', 
            'status', 'tracking', 'description'
        ]])

        st.markdown("---")
        st.subheader("Tổng quan nhanh")

        # Thống kê số lượng theo loại
        st.write("##### Số lượng theo loại:")
        type_counts = filtered_df['type'].value_counts().reset_index()
        type_counts.columns = ['Loại', 'Số lượng']
        st.table(type_counts)

        # Thống kê số lượng theo trạng thái
        st.write("##### Số lượng theo trạng thái:")
        # Cần chuẩn hóa lại trạng thái cho thống kê nếu cột tracking chứa ghi chú
        temp_status_col = filtered_df['tracking'].fillna('').apply(lambda x: x.split(" - Note:")[0].strip())
        status_counts = temp_status_col.value_counts().reset_index()
        status_counts.columns = ['Trạng thái Theo dõi', 'Số lượng']
        st.table(status_counts)

        # Tổng số lượng vật tư/hóa chất (nếu có trường số lượng và đơn vị)
        if 'quantity' in filtered_df.columns and 'unit' in filtered_df.columns:
            st.write("##### Tổng số lượng:")
            # Group by unit and sum quantities
            total_quantities = filtered_df.groupby('unit')['quantity'].sum().reset_index()
            total_quantities.columns = ['Đơn vị', 'Tổng số lượng']
            st.table(total_quantities)