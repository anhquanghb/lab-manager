# src/user_manager.py
import json
import pandas as pd
from pathlib import Path
import streamlit as st

class UserManager:
    def __init__(self, users_file='data/users.json'):
        project_root = Path(__file__).parent.parent
        self.users_file = project_root / users_file
        self.users_data = self._load_users()

    def _load_users(self):
        """Tải dữ liệu người dùng từ file JSON. Nếu file không tồn tại, tạo file rỗng."""
        if not self.users_file.exists():
            print(f"Không tìm thấy file người dùng tại {self.users_file}, tạo file mới...")
            self.users_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)
            return {}
        try:
            with open(self.users_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Lỗi khi tải file người dùng: {e}")
            return {}

    def get_user_role(self, email):
        """Lấy vai trò của người dùng dựa trên email. Trả về 'guest' nếu không tìm thấy."""
        return self.users_data.get(email, {}).get("role", "guest")
        
    def save_users(self):
        """Lưu dữ liệu người dùng vào file JSON."""
        try:
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(self.users_data, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"Lỗi khi lưu file người dùng: {e}")
            return False

    def get_all_users_as_df(self):
        """Trả về danh sách người dùng dưới dạng DataFrame."""
        users_list = []
        for email, user_data in self.users_data.items():
            users_list.append({
                "email": email,
                "role": user_data.get("role", "guest")
            })
        return pd.DataFrame(users_list)
        
    def add_or_update_user(self, email, role):
        """Thêm hoặc cập nhật vai trò của người dùng."""
        if email:
            self.users_data[email] = {"role": role}
            return self.save_users()
        return False
        
    def delete_user(self, email):
        """Xóa người dùng khỏi danh sách."""
        if email in self.users_data:
            del self.users_data[email]
            return self.save_users()
        return False