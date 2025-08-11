# src/data_converter.py

import pandas as pd
import json
import os
import io

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

def convert_csv_to_json(uploaded_file):
    """
    Chuyển đổi dữ liệu từ file CSV đã upload sang định dạng JSON mong muốn.
    Trả về dữ liệu JSON đã xử lý hoặc None nếu có lỗi.
    """
    try:
        # Đọc file CSV đã upload
        df_csv = pd.read_csv(io.BytesIO(uploaded_file.getvalue()))
    except Exception as e:
        raise ValueError(f"Lỗi khi đọc file CSV: {e}")

    transformed_data = []

    # Lặp qua từng dòng trong DataFrame và chuyển đổi sang định dạng JSON
    for index, row in df_csv.iterrows():
        item_id = str(row.get('Code', '')).strip() if pd.notna(row.get('Code')) and str(row.get('Code', '')).strip() != '0' else f"ITEM_{index + 1}"
        
        item_name_iupac = str(row.get('Tên Tiếng Anh/tên theo IUPAC', '')).strip() if pd.notna(row.get('Tên Tiếng Anh/tên theo IUPAC')) and str(row.get('Tên Tiếng Anh/tên theo IUPAC', '')).strip() != '0' else ''
        item_name_vn = str(row.get('Tên hóa chất/Vật tư/Thiết bị', '')).strip() if pd.notna(row.get('Tên hóa chất/Vật tư/Thiết bị')) and str(row.get('Tên hóa chất/Vật tư/Thiết bị', '')).strip().lower() != 'không' else ''

        item_name = item_name_iupac if item_name_iupac else item_name_vn
        if not item_name:
            item_name = f"Item {item_id} (Tên không xác định)"

        item_type_raw = str(row.get('Loại', '')).strip().lower() if pd.notna(row.get('Loại')) else ""
        if item_type_raw == "hóa chất":
            item_type = "Hóa chất"
        elif item_type_raw == "vật tư":
            item_type = "Vật tư"
        elif item_type_raw == "thiết bị":
            item_type = "Thiết bị"
        else:
            item_type = "Không xác định"

        item_quantity = row.get('Số lượng', 1)
        item_unit = str(row.get('Đơn vị', 'đơn vị')).strip() if pd.notna(row.get('Đơn vị')) else "đơn vị"

        item_location = str(row.get('Vị trí', 'Không rõ')).strip() if pd.notna(row.get('Vị trí')) else "Không rõ"
        if item_location.lower() == "không rõ":
            item_location = "Không rõ"

        item_chemical_formula = str(row.get('Công thức hóa chất', '')).strip() if pd.notna(row.get('Công thức hóa chất')) and str(row.get('Công thức hóa chất', '')).strip() != '0' else None
        item_cas_number = str(row.get('CAS', '')).strip() if pd.notna(row.get('CAS')) and str(row.get('CAS', '')).strip() != '0' else None
        
        item_state_or_concentration = str(row.get('Nồng độ/Trạng thái', '')).strip() if pd.notna(row.get('Nồng độ/Trạng thái')) else None
        if item_state_or_concentration:
            item_state_or_concentration = item_state_or_concentration.lower()

        item_status = str(row.get('Tình trạng chai, hộp', '')).strip() if pd.notna(row.get('Tình trạng chai, hộp')) else None
        if item_status:
            item_status = item_status.lower()
            if item_status == "còn nguyên":
                item_status = "còn nguyên"
            elif item_status in ["đã mở", "đã sử dụng", "sử dụng"]:
                item_status = "đã mở"
            elif item_status in ["hết hạn", "hết", "không còn"]:
                item_status = "hết"
            elif item_status in ["đang mượn", "đang sử dụng"]:
                item_status = "đang mượn"
            elif item_status == "thất lạc":
                item_status = "thất lạc"
            elif item_status == "huỷ":
                item_status = "huỷ"
            else:
                item_status = "không xác định"
        
        item_purpose = str(row.get('Mục đích', '')).strip() if pd.notna(row.get('Mục đích')) else None
        
        raw_tracking_from_csv = str(row.get('Theo dõi', 'Không rõ')).strip() if pd.notna(row.get('Theo dõi')) else "Không rõ"
        item_tracking = raw_tracking_from_csv.split(" - Note:")[0].strip()
        if item_tracking not in VALID_TRACKING_STATUSES:
            item_tracking = "Không rõ"
        
        item_note = str(row.get('Ghi chú', '')).strip() if pd.notna(row.get('Ghi chú')) else None
        if item_note == "":
            item_note = None

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
        if item_tracking and item_tracking != "Không rõ":
            description_parts.append(f"Theo dõi: {item_tracking}")
        if item_note:
            description_parts.append(f"Ghi chú: {item_note}")

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