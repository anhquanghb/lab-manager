import pandas as pd
import json
import os
import unicodedata # Thêm import này

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

    def _remove_accents(self, input_str):
        """Hàm trợ giúp để loại bỏ dấu tiếng Việt và chuẩn hóa chuỗi."""
        if not isinstance(input_str, str):
            return str(input_str) # Chuyển đổi sang chuỗi nếu không phải
        nfkd_form = unicodedata.normalize('NFKD', input_str)
        only_ascii = nfkd_form.encode('ascii', 'ignore').decode('utf-8')
        return only_ascii

    def search_item(self, query):
        """
        Tìm kiếm vật tư/hóa chất theo bất kỳ thông tin liên quan nào
        bao gồm: id, name, type, location, và description. (Tìm kiếm chung)
        """
        if self.inventory_data.empty:
            return pd.DataFrame()

        # Chuẩn hóa query: chuyển lower và bỏ dấu
        query_normalized = self._remove_accents(query.lower())

        # Chuẩn bị DataFrame tìm kiếm: chuyển lower và bỏ dấu cho các cột
        searchable_df = self.inventory_data[['id', 'name', 'type', 'location', 'description']].astype(str)
        searchable_df = searchable_df.applymap(self._remove_accents).apply(lambda x: x.str.lower())

        mask = searchable_df.apply(lambda col: col.str.contains(query_normalized, na=False)).any(axis=1)

        results = self.inventory_data[mask]
        return results

    def get_quantity(self, item_name):
        """Lấy số lượng của một vật tư/hóa chất cụ thể."""
        if self.inventory_data.empty:
            return None, None

        # Chuẩn hóa item_name và cột name
        item_name_normalized = self._remove_accents(item_name.lower())

        # Áp dụng remove_accents cho cột 'name' của DataFrame trước khi so sánh
        # Dùng applymap trên toàn bộ cột để tạo Series mới, sau đó so sánh
        found_item = self.inventory_data[self.inventory_data['name'].apply(self._remove_accents).str.lower() == item_name_normalized]

        if not found_item.empty:
            return found_item.iloc[0]['quantity'], found_item.iloc[0]['unit']
        return None, None

    def get_location(self, item_name):
        """Lấy vị trí của một vật tư/hóa chất cụ thể."""
        if self.inventory_data.empty:
            return None

        # Chuẩn hóa item_name và cột name
        item_name_normalized = self._remove_accents(item_name.lower())
        found_item = self.inventory_data[self.inventory_data['name'].apply(self._remove_accents).str.lower() == item_name_normalized]

        if not found_item.empty:
            return found_item.iloc[0]['location']
        return None

    # --- CÁC HÀM TÌM KIẾM MỚI ---
    # Áp dụng chuẩn hóa cho query và các cột liên quan

    def get_by_id(self, item_id):
        """Tìm kiếm vật tư/hóa chất theo ID chính xác."""
        if self.inventory_data.empty:
            return pd.DataFrame()

        # ID thường là ký tự La-tinh không dấu, nhưng vẫn chuẩn hóa để nhất quán
        item_id_normalized = self._remove_accents(item_id.lower())
        results = self.inventory_data[self.inventory_data['id'].apply(self._remove_accents).str.lower() == item_id_normalized]
        return results

    def list_by_location(self, location_query):
        """Liệt kê vật tư/hóa chất theo vị trí."""
        if self.inventory_data.empty:
            return pd.DataFrame()

        location_query_normalized = self._remove_accents(location_query.lower())
        results = self.inventory_data[self.inventory_data['location'].apply(self._remove_accents).str.lower().str.contains(location_query_normalized, na=False)]
        return results

    def list_by_type(self, item_type):
        """Liệt kê vật tư/hóa chất theo loại."""
        if self.inventory_data.empty:
            return pd.DataFrame()

        item_type_normalized = self._remove_accents(item_type.lower())
        results = self.inventory_data[self.inventory_data['type'].apply(self._remove_accents).str.lower() == item_type_normalized]
        return results

    def list_by_status(self, status_query):
        """Liệt kê vật tư/hóa chất theo tình trạng trong mô tả."""
        if self.inventory_data.empty:
            return pd.DataFrame()

        status_query_normalized = self._remove_accents(status_query.lower())
        results = self.inventory_data[self.inventory_data['description'].apply(self._remove_accents).str.lower().str.contains(status_query_normalized, na=False)]
        return results

    def list_by_location_and_status(self, location_query, status_query):
        """Liệt kê vật tư/hóa chất theo vị trí VÀ tình trạng."""
        if self.inventory_data.empty:
            return pd.DataFrame()

        location_query_normalized = self._remove_accents(location_query.lower())
        status_query_normalized = self._remove_accents(status_query.lower())

        normalized_location_col = self.inventory_data['location'].apply(self._remove_accents).str.lower()
        normalized_description_col = self.inventory_data['description'].apply(self._remove_accents).str.lower()

        mask_location = normalized_location_col.str.contains(location_query_normalized, na=False)
        mask_status = normalized_description_col.str.contains(status_query_normalized, na=False)

        results = self.inventory_data[mask_location & mask_status]
        return results

    def list_by_type_and_status(self, item_type, status_query):
        """Liệt kê vật tư/hóa chất theo loại VÀ tình trạng."""
        if self.inventory_data.empty:
            return pd.DataFrame()

        item_type_normalized = self._remove_accents(item_type.lower())
        status_query_normalized = self._remove_accents(status_query.lower())

        normalized_type_col = self.inventory_data['type'].apply(self._remove_accents).str.lower()
        normalized_description_col = self.inventory_data['description'].apply(self._remove_accents).str.lower()

        mask_type = normalized_type_col == item_type_normalized
        mask_status = normalized_description_col.str.contains(status_query_normalized, na=False)

        results = self.inventory_data[mask_type & mask_status]
        return results

    def list_by_type_and_location(self, item_type, location_query):
        """Liệt kê vật tư/hóa chất theo loại VÀ vị trí."""
        if self.inventory_data.empty:
            return pd.DataFrame()

        item_type_normalized = self._remove_accents(item_type.lower())
        location_query_normalized = self._remove_accents(location_query.lower())

        normalized_type_col = self.inventory_data['type'].apply(self._remove_accents).str.lower()
        normalized_location_col = self.inventory_data['location'].apply(self._remove_accents).str.lower()

        mask_type = normalized_type_col == item_type_normalized
        mask_location = normalized_location_col.str.contains(location_query_normalized, na=False)

        results = self.inventory_data[mask_type & mask_location]
        return results

    def search_by_cas(self, cas_number):
        """Tìm kiếm vật tư/hóa chất theo số CAS."""
        if self.inventory_data.empty:
            return pd.DataFrame()

        cas_number_normalized = self._remove_accents(cas_number.lower())
        results = self.inventory_data[self.inventory_data['description'].apply(self._remove_accents).str.lower().str.contains(f"cas: {cas_number_normalized}", na=False)]
        return results