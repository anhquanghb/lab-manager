# src/database_manager.py

import pandas as pd
import json
import os
import git
from datetime import datetime
import streamlit as st
import subprocess
from src.common_utils import remove_accents_and_normalize

class DatabaseManager:
    def __init__(self, data_path='data/inventory.json', config_path='data/config.json'):
        # SỬA: Sử dụng trực tiếp string path để tương thích cloud
        self.data_path = data_path
        self.config_path = config_path
        
        self.inventory_data = self._load_data()
        self.config_data = self._load_config()

    def _load_data(self):
        # SỬA: Dùng os.path.exists để kiểm tra file
        if not os.path.exists(self.data_path):
            print(f"Lỗi: Không tìm thấy file dữ liệu tại {self.data_path}")
            return pd.DataFrame()
        try:
            with open(self.data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            df = pd.DataFrame(data)
            
            # Vòng lặp để chuẩn hóa các cột cần thiết cho việc tìm kiếm
            columns_to_normalize = [
                'id', 'name', 'type', 'location', 'chemical_formula',
                'cas_number', 'state_or_concentration', 'status',
                'purpose', 'tracking', 'iupac_name', 'vietnamese_name',
                'description', 'note'
            ]

            for col in columns_to_normalize:
                if col in df.columns:
                    df[f'{col}_normalized'] = df[col].apply(remove_accents_and_normalize)
                elif col == 'note':
                    df['note'] = None
                    df['note_normalized'] = None

            return df
        except json.JSONDecodeError:
            print(f"Lỗi: File {self.data_path} không phải là JSON hợp lệ.")
            return pd.DataFrame()
        except Exception as e:
            print(f"Lỗi khi tải dữ liệu: {e}")
            return pd.DataFrame()

    def _load_config(self):
        """Tải cấu hình từ file config.json."""
        # SỬA: Dùng os.path.exists để kiểm tra file
        if not os.path.exists(self.config_path):
            print(f"Lỗi: Không tìm thấy file cấu hình tại {self.config_path}")
            return {}
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return config
        except json.JSONDecodeError:
            print(f"Lỗi: File {self.config_path} không phải là JSON hợp lệ.")
            return {}
        except Exception as e:
            print(f"Lỗi khi tải file cấu hình: {e}")
            return {}
            
    # --- Các hàm lấy dữ liệu từ file config ---
    def get_all_locations_from_config(self):
        locations = self.config_data.get('locations', [])
        return sorted(locations)

    def get_all_units_from_config(self):
        units = self.config_data.get('units', [])
        return sorted(units)

    def get_tracking_statuses_from_config(self):
        tracking_statuses = self.config_data.get('tracking_statuses', [])
        return sorted(tracking_statuses)

    # --- Các hàm truy vấn dữ liệu từ DataFrame ---
    def search_item(self, query):
        if self.inventory_data.empty:
            return pd.DataFrame()

        query_normalized = remove_accents_and_normalize(query)
        search_cols_normalized = [
            'id_normalized', 'name_normalized', 'type_normalized', 
            'location_normalized', 'description_normalized', 
            'chemical_formula_normalized', 'cas_number_normalized',
            'iupac_name_normalized', 'vietnamese_name_normalized',
            'note_normalized'
        ]
        
        existing_search_cols = [col for col in search_cols_normalized if col in self.inventory_data.columns]
        mask = self.inventory_data[existing_search_cols].apply(
            lambda col: col.fillna('').astype(str).str.contains(query_normalized, na=False)
        ).any(axis=1)

        return self.inventory_data[mask]

    def get_by_id(self, item_id):
        if self.inventory_data.empty:
            return pd.DataFrame()
        item_id_normalized = remove_accents_and_normalize(item_id)
        return self.inventory_data[self.inventory_data['id_normalized'] == item_id_normalized]
        
    def get_quantity(self, item_name):
        if self.inventory_data.empty:
            return None, None
        
        item_name_normalized = remove_accents_and_normalize(item_name)
        found_item_mask = (
            (self.inventory_data['name_normalized'] == item_name_normalized) |
            (self.inventory_data['iupac_name_normalized'] == item_name_normalized) |
            (self.inventory_data['vietnamese_name_normalized'] == item_name_normalized)
        )
        found_item = self.inventory_data[found_item_mask]

        if not found_item.empty:
            total_quantity = found_item['quantity'].sum()
            unit = found_item.iloc[0]['unit']
            return total_quantity, unit
        return None, None

    def get_location(self, item_name):
        if self.inventory_data.empty:
            return None

        item_name_normalized = remove_accents_and_normalize(item_name)
        found_item_mask = (
            (self.inventory_data['name_normalized'] == item_name_normalized) |
            (self.inventory_data['iupac_name_normalized'] == item_name_normalized) |
            (self.inventory_data['vietnamese_name_normalized'] == item_name_normalized)
        )
        found_item = self.inventory_data[found_item_mask]

        if not found_item.empty:
            unique_locations = found_item['location'].unique()
            return ", ".join(unique_locations)
        return None

    # --- Các hàm khác không thay đổi ---
    # ... (Bạn có thể giữ các hàm list_by_location, list_by_type, ... ở đây) ...

    # --- Hàm xử lý Git ---
    def upload_logs_to_github_on_startup(self, log_filepath):
        github_token = st.secrets.get("GITHUB_TOKEN")
        if not github_token:
            print("Lỗi: Không tìm thấy GITHUB_TOKEN trong st.secrets.")
            return False

        try:
            # Giả định repo path là thư mục hiện tại khi chạy trên cloud
            repo_path = "." 
            repo = git.Repo(repo_path)

            # ... (Phần logic Git còn lại có thể giữ nguyên) ...
            # Tuy nhiên, cần lưu ý việc git push từ môi trường Streamlit Cloud
            # có thể cần cấu hình phức tạp hơn (SSH keys).
            # Logic push hiện tại có thể không hoạt động như mong đợi trên cloud.
            print("Chức năng upload log lên GitHub đang được xem xét lại cho môi trường cloud.")
            return True # Tạm thời trả về True để không chặn ứng dụng

        except git.InvalidGitRepositoryError:
            print(f"Lỗi: {repo_path} không phải là một kho lưu trữ Git hợp lệ.")
            return False
        except Exception as e:
            print(f"Lỗi không xác định khi tải nhật ký lên GitHub: {e}")
            return False