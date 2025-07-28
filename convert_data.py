import pandas as pd
import json
import os
from pathlib import Path

# Đường dẫn đến file CSV mới của bạn
current_dir = Path(__file__).parent
csv_file_path = current_dir / 'danhmuc.csv'
# Đường dẫn đến file JSON mà chatbot đang sử dụng
json_file_path = current_dir / 'data' / 'inventory.json'

# Đọc file CSV
try:
    df_csv = pd.read_csv(csv_file_path)
    print(f"Đã đọc thành công file CSV: {csv_file_path}")
    print(f"Số lượng dòng trong CSV: {len(df_csv)}")
except FileNotFoundError:
    print(f"Lỗi: Không tìm thấy file CSV tại {csv_file_path}. Vui lòng đảm bảo file nằm trong thư mục gốc của dự án.")
    exit()
except Exception as e:
    print(f"Lỗi khi đọc file CSV: {e}")
    exit()

# Chuẩn bị danh sách để lưu trữ dữ liệu JSON đã chuyển đổi
transformed_data = []

# Lặp qua từng dòng trong DataFrame và chuyển đổi sang định dạng JSON mong muốn
for index, row in df_csv.iterrows():
    # 'id': Sử dụng 'Code' từ CSV, nếu trống thì tạo ID dựa trên số thứ tự dòng
    # Đảm bảo ID là chuỗi và xử lý '0' hoặc giá trị trống
    item_id = str(row['Code']).strip() if pd.notna(row['Code']) and str(row['Code']).strip() != '0' else f"ITEM_{index + 1}"

    # 'name': Ưu tiên 'Tên Tiếng Anh/tên theo IUPAC', nếu trống thì dùng 'Tên hóa chất/Vật tư/Thiết bị'
    # Nếu cả hai đều trống hoặc là 'KHÔNG'/'0', sử dụng một tên mặc định
    # ĐÃ SỬA TÊN CỘT: 'Tên theo IUPAC' -> 'Tên Tiếng Anh/tên theo IUPAC'
    item_name_iupac = str(row['Tên Tiếng Anh/tên theo IUPAC']).strip() if pd.notna(row['Tên Tiếng Anh/tên theo IUPAC']) and str(row['Tên Tiếng Anh/tên theo IUPAC']).strip() != '0' else ''
    # ĐÃ SỬA TÊN CỘT: 'Tên hóa chất/Vật tư' -> 'Tên hóa chất/Vật tư/Thiết bị'
    item_name_vn = str(row['Tên hóa chất/Vật tư/Thiết bị']).strip() if pd.notna(row['Tên hóa chất/Vật tư/Thiết bị']) and str(row['Tên hóa chất/Vật tư/Thiết bị']).strip().lower() != 'không' else ''

    # Tên hiển thị chính: Ưu tiên IUPAC, sau đó là Tiếng Việt, nếu không thì dùng tên mặc định
    item_name = item_name_iupac if item_name_iupac else item_name_vn
    if not item_name:
        item_name = f"Item {item_id} (Tên không xác định)" # Sử dụng item_id trong tên mặc định

    # 'type': Lấy trực tiếp từ cột 'Loại' mới (Hóa chất/Vật tư)
    # Chuẩn hóa giá trị loại
    item_type_raw = str(row['Loại']).strip().lower() if pd.notna(row['Loại']) else ""
    if item_type_raw == "hóa chất":
        item_type = "Hóa chất"
    elif item_type_raw == "vật tư":
        item_type = "Vật tư"
    elif item_type_raw == "thiết bị": # Bổ sung thêm loại "thiết bị" nếu có
        item_type = "Thiết bị"
    else:
        item_type = "Không xác định"

    # 'quantity' và 'unit': Giữ nguyên giá trị mặc định đã có
    item_quantity = 1 # Giá trị mặc định
    item_unit = "đơn vị" # Đơn vị mặc định

    # 'location': Lấy từ 'Vị trí', nếu trống thì là "Không rõ"
    # ĐÃ SỬA TÊN CỘT: 'Vị trí lưu trữ' -> 'Vị trí'
    item_location = str(row['Vị trí']).strip() if pd.notna(row['Vị trí']) else "Không rõ"
    if item_location.lower() == "không rõ": # Chuẩn hóa "Không rõ"
        item_location = "Không rõ"

    # Tách các trường từ description gốc thành các trường JSON riêng biệt để dễ truy vấn
    item_chemical_formula = str(row['Công thức hóa chất']).strip() if pd.notna(row['Công thức hóa chất']) and str(row['Công thức hóa chất']).strip() != '0' else None
    item_cas_number = str(row['CAS']).strip() if pd.notna(row['CAS']) and str(row['CAS']).strip() != '0' else None
    
    # Chuẩn hóa Trạng thái/Nồng độ và Tình trạng
    # ĐÃ SỬA TÊN CỘT: 'Nồng độ' -> 'Nồng độ/Trạng thái'
    item_state_or_concentration = str(row['Nồng độ/Trạng thái']).strip() if pd.notna(row['Nồng độ/Trạng thái']) else None
    if item_state_or_concentration:
        item_state_or_concentration = item_state_or_concentration.lower() # Chuyển về chữ thường để nhất quán

    # ĐÃ SỬA TÊN CỘT: 'Tình trạng' -> 'Tình trạng chai, hộp'
    item_status = str(row['Tình trạng chai, hộp']).strip() if pd.notna(row['Tình trạng chai, hộp']) else None
    if item_status:
        item_status = item_status.lower() # Chuyển về chữ thường để nhất quán
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
        else: # Các trạng thái khác hoặc không rõ
            item_status = "không xác định"


    item_purpose = str(row['Mục đích']).strip() if pd.notna(row['Mục đích']) else None
    item_tracking = str(row['Theo dõi']).strip() if pd.notna(row['Theo dõi']) else None
    if item_tracking:
        item_tracking = item_tracking.lower() # Chuẩn hóa tracking

    # Tạo lại trường 'description' để hiển thị đầy đủ, hoặc có thể bỏ qua nếu UI sử dụng các trường riêng lẻ
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
    if item_tracking:
        description_parts.append(f"Theo dõi: {item_tracking}")

    item_description_for_display = ", ".join(description_parts) if description_parts else "Không có mô tả."

    # Thêm đối tượng vào danh sách với các trường đã tách và chuẩn hóa
    transformed_data.append({
        "id": item_id,
        "name": item_name,
        "type": item_type,
        "quantity": item_quantity,
        "unit": item_unit,
        "location": item_location,
        "description": item_description_for_display, # Giữ lại description để hiển thị
        "iupac_name": item_name_iupac if item_name_iupac else None,
        "vietnamese_name": item_name_vn if item_name_vn else None,
        "chemical_formula": item_chemical_formula,
        "cas_number": item_cas_number,
        "state_or_concentration": item_state_or_concentration,
        "status": item_status, # Trường status đã chuẩn hóa
        "purpose": item_purpose,
        "tracking": item_tracking # Trường tracking đã chuẩn hóa
    })

# Đảm bảo thư mục 'data' tồn tại
os.makedirs(json_file_path.parent, exist_ok=True)

# Lưu dữ liệu đã chuyển đổi vào file JSON
try:
    with open(json_file_path, 'w', encoding='utf-8') as f:
        json.dump(transformed_data, f, ensure_ascii=False, indent=2)
    print(f"\nĐã chuyển đổi thành công '{csv_file_path}' sang '{json_file_path}'.")
    print(f"Tổng số bản ghi đã xử lý: {len(transformed_data)}.")
except Exception as e:
    print(f"Lỗi khi ghi file JSON: {e}")