import pandas as pd
import json
import os
import re
from pathlib import Path
import git
from datetime import datetime
import streamlit as st
from src.common_utils import remove_accents_and_normalize

class AdminDatabaseManager:
    """
    Lớp quản lý các thao tác ghi dữ liệu vào cơ sở dữ liệu và đẩy lên GitHub.
    Lớp này nhận một instance của DatabaseManager để truy cập DataFrame trong bộ nhớ.
    """
    def __init__(self, db_manager_instance):
        self.db_manager = db_manager_instance # Instance của DatabaseManager (chứa inventory_data)
        self.data_path = self.db_manager.data_path # Đường dẫn đến file inventory.json

    def save_inventory_to_json(self):
        """
        Lưu DataFrame inventory_data hiện tại (chỉ các cột gốc) vào file data/inventory.json.
        """
        if self.db_manager.inventory_data.empty:
            print("Không có dữ liệu trong inventory_data để lưu.")
            return False
        
        # Chỉ lấy các cột gốc để lưu vào JSON, loại bỏ các cột _normalized
        original_cols = [
            'id', 'name', 'type', 'quantity', 'unit', 'location', 'description',
            'iupac_name', 'vietnamese_name', 'chemical_formula', 'cas_number',
            'state_or_concentration', 'status', 'purpose', 'tracking', 'note' # BỔ SUNG: Thêm cột 'note'
        ]
        
        # Lọc DataFrame để chỉ giữ lại các cột gốc có tồn tại
        cols_to_save = [col for col in original_cols if col in self.db_manager.inventory_data.columns]
        data_to_save = self.db_manager.inventory_data[cols_to_save].to_dict(orient='records')

        try:
            # Đảm bảo thư mục tồn tại trước khi ghi
            self.data_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.data_path, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)
            print(f"Đã lưu inventory_data vào {self.data_path} thành công.")
            return True
        except Exception as e:
            print(f"Lỗi khi lưu inventory_data vào JSON: {e}")
            return False

    def push_inventory_to_github(self, commit_message):
        # ... (hàm này không thay đổi)
        pass # Placeholder for existing function, as it's quite long