# src/convert_data.py

import pandas as pd # Import pandas here
import json
import os
from pathlib import Path
from datetime import datetime

# Danh sách các trạng thái Tracking hợp lệ (trùng khớp với admin_page.py)
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

def convert_csv_to_json_data(df_csv):
    """
    Chuyển đổi dữ liệu từ DataFrame của CSV sang định dạng list of dicts
    để lưu vào file JSON.
    """
    transformed_data = []

    for index, row in df_csv.iterrows():
        # 'id': Sử dụng 'Code' từ CSV, nếu trống thì tạo ID dựa trên số thứ tự dòng
        item_id = str(row.get('Code', '')).strip() if pd.notna(row.get('Code')) and str(row.get('Code', '')).strip() != '0' else f"ITEM_{index + 1}"

        # 'name': Cải thiện logic để tránh tên 'không xác định'
        item_name_iupac = str(row.get('Tên Tiếng Anh/tên theo IUPAC', '')).strip() if pd.notna(row.get('Tên Tiếng Anh/tên theo IUPAC')) and str(row.get('Tên Tiếng Anh/tên theo IUPAC', '')).strip() != '0' else ''
        item_name_vn = str(row.get('Tên hóa chất/Vật tư/Thiết bị', '')).strip() if pd.notna(row.get('Tên hóa chất/Vật tư/Thiết bị')) and str(row.get('Tên hóa chất/Vật tư/Thiết bị', '')).strip().lower() != 'không' else ''
        item_note_for_name = str(row.get('Ghi chú', '')).strip() if pd.notna(row.get('Ghi chú')) else ''
        
        item_name = item_name_iupac if item_name_iupac else item_name_vn
        if not item_name:
            if item_note_for_name:
                item_name = item_note_for_name
            else:
                item_name = f"Item {item_id} (Tên không xác định)"

        # 'type': Lấy trực tiếp từ cột 'Loại'
        item_type_raw = str(row.get('Loại', '')).strip().lower() if pd.notna(row.get('Loại')) else ""
        if item_type_raw == "hóa chất":
            item_type = "Hóa chất"
        elif item_type_raw == "vật tư":
            item_type = "Vật tư"
        elif item_type_raw == "thiết bị":
            item_type = "Thiết bị"
        else:
            item_type = "Không xác định"

        # 'quantity' và 'unit': Giữ nguyên giá trị mặc định đã có (hoặc lấy từ CSV nếu có)
        item_quantity = row.get('Số lượng', 1) if pd.notna(row.get('Số lượng')) else 1
        item_unit = str(row.get('Đơn vị', 'đơn vị')).strip() if pd.notna(row.get('Đơn vị')) else "đơn vị"

        # 'location': Lấy từ 'Vị trí', nếu trống thì là "Không rõ"
        item_location = str(row.get('Vị trí', '')).strip() if pd.notna(row.get('Vị trí')) else "Không rõ"
        if item_location.lower() == "không rõ":
            item_location = "Không rõ"

        # Các trường khác
        item_chemical_formula = str(row.get('Công thức hóa chất', '')).strip() if pd.notna(row.get('Công thức hóa chất')) and str(row.get('Công thức hóa chất', '')).strip() != '0' else None
        item_cas_number = str(row.get('CAS', '')).strip() if pd.notna(row.get('CAS')) and str(row.get('CAS', '')).strip() != '0' else None
        item_state_or_concentration = str(row.get('Nồng độ/Trạng thái', '')).strip() if pd.notna(row.get('Nồng độ/Trạng thái')) else None
        item_purpose = str(row.get('Mục đích', '')).strip() if pd.notna(row.get('Mục đích')) else None

        # Xử lý trường 'Theo dõi' (tracking) và 'Ghi chú' (note)
        item_note = str(row.get('Ghi chú', '')).strip() if pd.notna(row.get('Ghi chú')) else None
        if item_note == "":
            item_note = None

        # Logic chuẩn hóa cho trường 'status'
        item_status_raw = str(row.get('Tình trạng chai, hộp', '')).strip().lower() if pd.notna(row.get('Tình trạng chai, hộp')) else None
        item_status = None
        if item_status_raw:
            if item_status_raw == "còn nguyên":
                item_status = "còn nguyên"
            elif item_status_raw in ["đã mở", "đã sử dụng", "sử dụng"]:
                item_status = "đã mở"
            elif item_status_raw in ["hết hạn", "hết", "không còn"]:
                item_status = "hết"
            elif item_status_raw in ["đang mượn", "đang sử dụng"]:
                item_status = "đang mượn"
            elif item_status_raw == "thất lạc":
                item_status = "thất lạc"
            elif item_status_raw == "huỷ":
                item_status = "huỷ"
            else:
                item_status = "không xác định"
        
        # Logic chuẩn hóa cho trường 'tracking'
        raw_tracking_from_csv = str(row.get('Theo dõi', '')).strip() if pd.notna(row.get('Theo dõi')) else "Không rõ"
        item_tracking = raw_tracking_from_csv.split(" - Note:")[0].strip()
        if item_tracking not in VALID_TRACKING_STATUSES:
            item_tracking = "Không rõ"
        
        # Nếu tracking là "Không rõ", thử lấy giá trị từ status nếu có
        if item_tracking == "Không rõ" and item_status:
            tracking_from_status = item_status.capitalize()
            if tracking_from_status in VALID_TRACKING_STATUSES:
                item_tracking = tracking_from_status

        # Tạo lại trường 'description' để hiển thị đầy đủ
        description_parts = []
        if item_name_iupac and item_name_iupac != item_name:
            description_parts.append(f"Tên IUPAC: {item_name_iupac}")
        if item_name_vn and item_name_vn != item_name:
            description_parts.append(f"Tên Tiếng Việt: {item_name_vn}")
        if item_chemical_formula:
            description_parts.append(f"Công thức: {item_chemical_formula}")
        if item_cas_number:
            description_parts.append(f"CAS: {item_cas_number}")
        if item_state_or_concentration:
            description_parts.append(f"Trạng thái/Nồng độ: {item_state_or_concentration}")
        if item_status:
            description_parts.append(f"Mô tả: {item_status}")
        if item_purpose:
            description_parts.append(f"Mục đích: {item_purpose}")

        item_description_for_display = ", ".join(description_parts) if description_parts else "Không có mô tả."
        
        transformed_data.append({
            "id": item_id,
            "name": item_name,
            "type": item_type,
            "quantity": item_quantity,
            "unit": item_unit,
            "location": item_location,
            "description": item_description_for_display,
            "iupac_name": item_name_iupac if item_name_iupac else None,
            "vietnamese_name": item_name_vn if item_name_vn else None,
            "chemical_formula": item_chemical_formula,
            "cas_number": item_cas_number,
            "state_or_concentration": item_state_or_concentration,
            "status": item_status,
            "purpose": item_purpose,
            "tracking": item_tracking,
            "note": item_note
        })
    
    return transformed_data