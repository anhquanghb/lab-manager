import pandas as pd
import json
import os

# Đường dẫn đến file CSV mới của bạn
csv_file_path = 'danhmuc.csv'
# Đường dẫn đến file JSON mà chatbot đang sử dụng
json_file_path = 'data/inventory.json'

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
    item_id = str(row['Code']) if pd.notna(row['Code']) and str(row['Code']).strip() != '0' else f"ITEM_{index + 1}"

    # 'name': Ưu tiên 'Tên hóa chất (IUPAC)', nếu trống thì dùng 'Tên hóa chất (Tiếng Việt)'
    # Nếu cả hai đều trống hoặc là 'KHÔNG'/'0', sử dụng một tên mặc định
    item_name = ""
    if pd.notna(row['Tên hóa chất (IUPAC)']) and str(row['Tên hóa chất (IUPAC)']).strip() != '0':
        item_name = str(row['Tên hóa chất (IUPAC)']).strip()
    elif pd.notna(row['Tên hóa chất (Tiếng Việt)']) and str(row['Tên hóa chất (Tiếng Việt)']).strip().lower() != 'không':
        item_name = str(row['Tên hóa chất (Tiếng Việt)']).strip()
    else:
        item_name = f"Item {index + 1} (Tên không xác định)"

    # 'type': Phân loại 'Hóa chất' nếu có 'Công thức hóa chất', ngược lại là 'Vật tư'
    item_type = "Vật tư"
    if pd.notna(row['Công thức hóa chất']) and str(row['Công thức hóa chất']).strip() != '0':
        item_type = "Hóa chất"

    # 'quantity' và 'unit': 'Nồng độ' trong CSV của bạn chủ yếu là mô tả (rắn, lỏng),
    # nên chúng ta sẽ dùng giá trị mặc định cho số lượng và đơn vị.
    item_quantity = 1 # Giá trị mặc định
    item_unit = "đơn vị" # Đơn vị mặc định

    # 'location': Lấy từ 'Vị trí lưu trữ', nếu trống thì là "Không rõ"
    item_location = str(row['Vị trí lưu trữ']) if pd.notna(row['Vị trí lưu trữ']) else "Không rõ"

    # 'description': Kết hợp các trường liên quan để tạo mô tả chi tiết
    description_parts = []
    if pd.notna(row['Công thức hóa chất']) and str(row['Công thức hóa chất']).strip() != '0':
        description_parts.append(f"Công thức: {str(row['Công thức hóa chất']).strip()}")
    if pd.notna(row['CAS']) and str(row['CAS']).strip() != '0':
        description_parts.append(f"CAS: {str(row['CAS']).strip()}")
    if pd.notna(row['Nồng độ']):
        description_parts.append(f"Trạng thái/Nồng độ: {str(row['Nồng độ']).strip()}")
    if pd.notna(row['Tình trạng']):
        description_parts.append(f"Tình trạng: {str(row['Tình trạng']).strip()}")
    if pd.notna(row['Mục đích']):
        description_parts.append(f"Mục đích: {str(row['Mục đích']).strip()}")
    if pd.notna(row['Theo dõi']):
        description_parts.append(f"Theo dõi: {str(row['Theo dõi']).strip()}")

    item_description = ", ".join(description_parts) if description_parts else "Không có mô tả."

    # Thêm đối tượng vào danh sách
    transformed_data.append({
        "id": item_id,
        "name": item_name,
        "type": item_type,
        "quantity": item_quantity,
        "unit": item_unit,
        "location": item_location,
        "description": item_description
    })

# Lưu dữ liệu đã chuyển đổi vào file JSON
try:
    with open(json_file_path, 'w', encoding='utf-8') as f:
        json.dump(transformed_data, f, ensure_ascii=False, indent=2)
    print(f"\nĐã chuyển đổi thành công '{csv_file_path}' sang '{json_file_path}'.")
    print(f"Tổng số bản ghi đã xử lý: {len(transformed_data)}.")
except Exception as e:
    print(f"Lỗi khi ghi file JSON: {e}")