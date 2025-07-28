import pandas as pd
import json
import os
import unicodedata # Thêm import này cho chuẩn hóa

# Đường dẫn đến file CSV của bạn
csv_file_path = 'danhmuc.csv'
# Đường dẫn đến file JSON đầu ra
json_file_path = 'data/inventory.json'

# Hàm trợ giúp loại bỏ dấu và chuẩn hóa chuỗi
def _remove_accents_and_lower(input_str):
    if pd.isna(input_str):
        return ""
    s = str(input_str).lower().strip()
    nfkd_form = unicodedata.normalize('NFKD', s)
    only_ascii = nfkd_form.encode('ascii', 'ignore').decode('utf-8')
    return only_ascii

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

# Chuẩn bị danh sách để lưu trữ các bản ghi JSON đã chuyển đổi
transformed_data = []

# Lặp qua từng dòng trong DataFrame và chuyển đổi sang định dạng JSON mong muốn
for index, row in df_csv.iterrows():
    # 'id': Sử dụng 'Code' từ CSV, nếu trống thì tạo ID dựa trên số thứ tự dòng
    item_id = str(row['Code']).strip() if pd.notna(row['Code']) and str(row['Code']).strip() != '0' else f"ITEM_{index + 1}"

    # 'name': Ưu tiên 'Tên theo IUPAC', nếu trống thì dùng 'Tên hóa chất/Vật tư' (Tiếng Việt)
    item_name_iupac = str(row['Tên theo IUPAC']).strip() if pd.notna(row['Tên theo IUPAC']) and str(row['Tên theo IUPAC']).strip() != '0' else ''
    item_name_vn = str(row['Tên hóa chất/Vật tư']).strip() if pd.notna(row['Tên hóa chất/Vật tư']) and str(row['Tên hóa chất/Vật tư']).strip().lower() != 'không' else ''

    item_name = item_name_iupac if item_name_iupac else item_name_vn
    if not item_name:
        item_name = f"Item {index + 1} (Tên không xác định)"

    # 'type': Lấy trực tiếp từ cột 'Loại' mới
    item_type_raw = str(row['Loại']).strip().lower() if pd.notna(row['Loại']) else ""
    if item_type_raw == "hóa chất":
        item_type = "Hóa chất"
    elif item_type_raw == "vật tư":
        item_type = "Vật tư"
    elif item_type_raw == "thiết bị": # Thêm loại thiết bị
        item_type = "Thiết bị"
    else:
        item_type = "Không xác định" # Giá trị mặc định nếu cột Loại không hợp lệ

    # 'quantity' và 'unit': Giữ nguyên giá trị mặc định (Nồng độ thường là text)
    item_quantity = 1 # Giá trị mặc định
    item_unit = "đơn vị" # Đơn vị mặc định

    # 'location': Lấy từ 'Vị trí lưu trữ', nếu trống thì là "Không rõ"
    item_location = str(row['Vị trí lưu trữ']).strip() if pd.notna(row['Vị trí lưu trữ']) else "Không rõ"

    # TÁCH CÁC TRƯỜNG DỮ LIỆU TỪ DESCRIPTION/CÁC CỘT RIÊNG BIỆT
    # Chuẩn hóa luôn giá trị
    item_formula = str(row['Công thức hóa chất']).strip() if pd.notna(row['Công thức hóa chất']) and str(row['Công thức hóa chất']).strip() != '0' else ''
    item_cas = str(row['CAS']).strip() if pd.notna(row['CAS']) and str(row['CAS']).strip() != '0' else ''
    item_state_conc = str(row['Nồng độ']).strip() if pd.notna(row['Nồng độ']) else '' # Trạng thái/Nồng độ
    item_status_text = str(row['Tình trạng']).strip() if pd.notna(row['Tình trạng']) else '' # Tình trạng
    item_tracking = str(row['Theo dõi']).strip() if pd.notna(row['Theo dõi']) else '' # Theo dõi
    item_purpose = str(row['Mục đích']).strip() if pd.notna(row['Mục đích']) else '' # Mục đích

    # Tạo description (chung) từ các thông tin phụ trợ
    general_description_parts = []
    if item_name_iupac and item_name_iupac != item_name:
        general_description_parts.append(f"Tên IUPAC: {item_name_iupac}")
    if item_name_vn and item_name_vn != item_name:
        general_description_parts.append(f"Tên Tiếng Việt: {item_name_vn}")
    if item_formula:
        general_description_parts.append(f"Công thức: {item_formula}")
    if item_cas:
        general_description_parts.append(f"CAS: {item_cas}")
    if item_state_conc:
        general_description_parts.append(f"Trạng thái/Nồng độ: {item_state_conc}")
    if item_status_text:
        general_description_parts.append(f"Tình trạng: {item_status_text}")
    if item_tracking:
        general_description_parts.append(f"Theo dõi: {item_tracking}")
    if item_purpose:
        general_description_parts.append(f"Mục đích: {item_purpose}")
    
    item_description = ", ".join(general_description_parts) if general_description_parts else "Không có mô tả chi tiết."

    # Thêm đối tượng vào danh sách
    transformed_data.append({
        "id": item_id,
        "name": item_name,
        "type": item_type,
        "quantity": item_quantity,
        "unit": item_unit,
        "location": item_location,
        # Thêm các trường mới được tách ra
        "formula": item_formula, # Công thức hóa chất
        "cas_number": item_cas, # Số CAS
        "state_or_concentration": item_state_conc, # Trạng thái/Nồng độ
        "status_text": item_status_text, # Tình trạng (từ cột Tình trạng)
        "tracking": item_tracking, # Theo dõi
        "purpose": item_purpose, # Mục đích
        "description": item_description # Mô tả tổng hợp
    })

# Lưu dữ liệu đã chuyển đổi vào file JSON
try:
    with open(json_file_path, 'w', encoding='utf-8') as f:
        json.dump(transformed_data, f, ensure_ascii=False, indent=2)
    print(f"\nĐã chuyển đổi thành công '{csv_file_path}' sang '{json_file_path}' với cấu trúc dữ liệu mới.")
    print(f"Tổng số bản ghi đã xử lý: {len(transformed_data)}.")
except Exception as e:
    print(f"Lỗi khi ghi file JSON: {e}")