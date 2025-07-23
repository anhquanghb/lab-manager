import pandas as pd
import json
import os

class DatabaseManager:
    def __init__(self, data_path='data/inventory.json'):
        # Đảm bảo đường dẫn tương đối đúng từ thư mục gốc của dự án
        self.data_path = os.path.join(os.path.dirname(__file__), '..', data_path)
        self.inventory_data = self._load_data()

    def _load_data(self):
        """Tải dữ liệu từ file JSON."""
        if not os.path.exists(self.data_path):
            print(f"Lỗi: Không tìm thấy file dữ liệu tại {self.data_path}")
            return pd.DataFrame() # Trả về DataFrame rỗng nếu file không tồn tại
        try:
            with open(self.data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return pd.DataFrame(data)
        except json.JSONDecodeError:
            print(f"Lỗi: File {self.data_path} không phải là JSON hợp lệ.")
            return pd.DataFrame()
        except Exception as e:
            print(f"Lỗi khi tải dữ liệu: {e}")
            return pd.DataFrame()

    def search_item(self, query):
        """Tìm kiếm vật tư/hóa chất theo tên hoặc mô tả."""
        if self.inventory_data.empty:
            return pd.DataFrame()

        query_lower = query.lower()

        # Tìm kiếm trong cột 'name' hoặc 'description'
        results = self.inventory_data[
            self.inventory_data['name'].str.lower().str.contains(query_lower) |
            self.inventory_data['description'].str.lower().str.contains(query_lower)
        ]
        return results

    def get_quantity(self, item_name):
        """Lấy số lượng của một vật tư/hóa chất cụ thể."""
        if self.inventory_data.empty:
            return None, None

        item_name_lower = item_name.lower()
        # Tìm kiếm chính xác tên
        found_item = self.inventory_data[self.inventory_data['name'].str.lower() == item_name_lower]

        if not found_item.empty:
            return found_item.iloc[0]['quantity'], found_item.iloc[0]['unit']
        return None, None

    def get_location(self, item_name):
        """Lấy vị trí của một vật tư/hóa chất cụ thể."""
        if self.inventory_data.empty:
            return None

        item_name_lower = item_name.lower()
        # Tìm kiếm chính xác tên
        found_item = self.inventory_data[self.inventory_data['name'].str.lower() == item_name_lower]

        if not found_item.empty:
            return found_item.iloc[0]['location']
        return None