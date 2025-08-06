# src/statistics_page.py

import streamlit as st
import pandas as pd
from src.database_manager import DatabaseManager

# Khởi tạo DatabaseManager (chỉ một lần và được cache)
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

    # Lấy danh sách các giá trị duy nhất từ file config.json
    all_types = db_manager.config_data.get('types', [])
    all_locations = db_manager.config_data.get('locations', [])
    all_purposes = db_manager.config_data.get('purposes', [])
    all_statuses = db_manager.config_data.get('statuses', [])
    all_tracking_statuses = db_manager.config_data.get('tracking_statuses', [])

    # Bổ sung các giá trị từ inventory_data nếu chúng chưa có trong config
    all_types_from_data = db_manager.inventory_data['type'].fillna('').unique().tolist()
    all_types.extend([t for t in all_types_from_data if t not in all_types and t])
    all_locations_from_data = db_manager.inventory_data['location'].fillna('').unique().tolist()
    all_locations.extend([l for l in all_locations_from_data if l not in all_locations and l])

    # Sắp xếp và đặt "Tất cả" và "Không rõ" ở đầu
    def sort_options(options):
        if not options:
            return ["Tất cả"]
        special_values = [v for v in ["Không rõ", "Không xác định"] if v in options]
        other_values = sorted([v for v in options if v not in special_values and v.strip() != ""])
        return ["Tất cả"] + special_values + other_values

    # Bộ lọc
    selected_type = st.selectbox("Lọc theo Loại:", options=sort_options(all_types))
    selected_location = st.selectbox("Lọc theo Vị trí:", options=sort_options(all_locations))
    selected_purpose = st.selectbox("Lọc theo Mục đích:", options=sort_options(all_purposes))
    selected_status = st.selectbox("Lọc theo Trạng thái ban đầu:", options=sort_options(all_statuses))
    selected_tracking = st.selectbox("Lọc theo Trạng thái theo dõi:", options=sort_options(all_tracking_statuses))

    filtered_df = db_manager.inventory_data.copy()

    # Áp dụng bộ lọc
    if selected_type != 'Tất cả':
        filtered_df = filtered_df[filtered_df['type'] == selected_type]

    if selected_location != 'Tất cả':
        filtered_df = filtered_df[filtered_df['location'] == selected_location]

    if selected_purpose != 'Tất cả':
        filtered_df = filtered_df[filtered_df['purpose'] == selected_purpose]
        
    if selected_status != 'Tất cả':
        filtered_df = filtered_df[filtered_df['status'] == selected_status]

    if selected_tracking != 'Tất cả':
        filtered_df = filtered_df[
            filtered_df['tracking'].fillna('').apply(lambda x: x.split(" - Note:")[0].strip() == selected_tracking)
        ]

    st.markdown("---")
    st.subheader("Kết quả Thống kê")

    if filtered_df.empty:
        st.info("Không có dữ liệu phù hợp với các tiêu chí lọc đã chọn.")
    else:
        st.write(f"Tìm thấy **{len(filtered_df)}** mục phù hợp:")
        
        st.dataframe(filtered_df[[
            'id', 'name', 'type', 'quantity', 'unit', 'location', 
            'status', 'tracking', 'note', 'description'
        ]])

        st.markdown("---")
        st.subheader("Tổng quan nhanh")

        st.write("##### Số lượng theo loại:")
        type_counts = filtered_df['type'].value_counts().reset_index()
        type_counts.columns = ['Loại', 'Số lượng']
        st.table(type_counts)

        st.write("##### Số lượng theo trạng thái theo dõi:")
        temp_tracking_status_col = filtered_df['tracking'].fillna('').apply(lambda x: x.split(" - Note:")[0].strip())
        tracking_status_counts = temp_tracking_status_col.value_counts().reset_index()
        tracking_status_counts.columns = ['Trạng thái Theo dõi', 'Số lượng']
        st.table(tracking_status_counts)

        st.write("##### Số lượng theo vị trí:")
        location_counts = filtered_df['location'].value_counts().reset_index()
        location_counts.columns = ['Vị trí', 'Số lượng']
        st.table(location_counts)

        if 'quantity' in filtered_df.columns and 'unit' in filtered_df.columns:
            st.write("##### Tổng số lượng:")
            total_quantities = filtered_df.groupby('unit')['quantity'].sum().reset_index()
            total_quantities.columns = ['Đơn vị', 'Tổng số lượng']
            st.table(total_quantities)