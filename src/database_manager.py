import pandas as pd
import json
import os

class DatabaseManager:
    def __init__(self, data_path='data/inventory.json'):
        self.data_path = os.path.join(os.path.dirname(__file__), '..', data_path)
        self.inventory_data = self._load_data()

    def _load_data(self):
        """Tải dữ liệu từ file JSON."""
        if not os.path.exists(self.data_path):
            print(f"Lỗi: Không tìm thấy file dữ liệu tại {self.data_path}")
            return pd.DataFrame()
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
        """
        Tìm kiếm vật tư/hóa chất theo bất kỳ thông tin liên quan nào
        bao gồm: id, name, type, location, và description. (Tìm kiếm chung)
        """
        if self.inventory_data.empty:
            return pd.DataFrame()

        query_lower = query.lower()

        searchable_df = self.inventory_data[['id', 'name', 'type', 'location', 'description']].astype(str).apply(lambda x: x.str.lower())

        mask = searchable_df.apply(lambda col: col.str.contains(query_lower, na=False)).any(axis=1)

        results = self.inventory_data[mask]
        return results

    def get_quantity(self, item_name):
        """Lấy số lượng của một vật tư/hóa chất cụ thể."""
        if self.inventory_data.empty:
            return None, None

        item_name_lower = item_name.lower()
        found_item = self.inventory_data[self.inventory_data['name'].str.lower() == item_name_lower]

        if not found_item.empty:
            return found_item.iloc[0]['quantity'], found_item.iloc[0]['unit']
        return None, None

    def get_location(self, item_name):
        """Lấy vị trí của một vật tư/hóa chất cụ thể."""
        if self.inventory_data.empty:
            return None

        item_name_lower = item_name.lower()
        found_item = self.inventory_data[self.inventory_data['name'].str.lower() == item_name_lower]

        if not found_item.empty:
            return found_item.iloc[0]['location']
        return None

    # --- CÁC HÀM TÌM KIẾM CỤ THỂ ---

    def get_by_id(self, item_id):
        """Tìm kiếm vật tư/hóa chất theo ID chính xác."""
        if self.inventory_data.empty:
            return pd.DataFrame()

        results = self.inventory_data[self.inventory_data['id'].str.lower() == item_id.lower()]
        return results

    def list_by_location(self, location_query):
        """Liệt kê vật tư/hóa chất theo vị trí."""
        if self.inventory_data.empty:
            return pd.DataFrame()

        results = self.inventory_data[self.inventory_data['location'].str.lower().str.contains(location_query.lower(), na=False)]
        return results

    def list_by_type(self, item_type):
        """Liệt kê vật tư/hóa chất theo loại."""
        if self.inventory_data.empty:
            return pd.DataFrame()

        results = self.inventory_data[self.inventory_data['type'].str.lower() == item_type.lower()]
        return results

    def list_by_status(self, status_query):
        """Liệt kê vật tư/hóa chất theo tình trạng trong mô tả."""
        if self.inventory_data.empty:
            return pd.DataFrame()

        results = self.inventory_data[self.inventory_data['description'].str.lower().str.contains(status_query.lower(), na=False)]
        return results

    def list_by_location_and_status(self, location_query, status_query):
        """Liệt kê vật tư/hóa chất theo vị trí VÀ tình trạng."""
        if self.inventory_data.empty:
            return pd.DataFrame()

        mask_location = self.inventory_data['location'].str.lower().str.contains(location_query.lower(), na=False)
        mask_status = self.inventory_data['description'].str.lower().str.contains(status_query.lower(), na=False)

        results = self.inventory_data[mask_location & mask_status]
        return results

    def list_by_type_and_status(self, item_type, status_query):
        """Liệt kê vật tư/hóa chất theo loại VÀ tình trạng."""
        if self.inventory_data.empty:
            return pd.DataFrame()

        mask_type = self.inventory_data['type'].str.lower() == item_type.lower()
        mask_status = self.inventory_data['description'].str.lower().str.contains(status_query.lower(), na=False)

        results = self.inventory_data[mask_type & mask_status]
        return results

    def list_by_type_and_location(self, item_type, location_query):
        """Liệt kê vật tư/hóa chất theo loại VÀ vị trí."""
        if self.inventory_data.empty:
            return pd.DataFrame()

        mask_type = self.inventory_data['type'].str.lower() == item_type.lower()
        mask_location = self.inventory_data['location'].str.lower().str.contains(location_query.lower(), na=False)

        results = self.inventory_data[mask_type & mask_location]
        return results

    def search_by_cas(self, cas_number):
        """Tìm kiếm vật tư/hóa chất theo số CAS."""
        if self.inventory_data.empty:
            return pd.DataFrame()

        results = self.inventory_data[self.inventory_data['description'].str.lower().str.contains(f"cas: {cas_number.lower()}", na=False)]
        return results