# src/user_manager.py (đã sửa đổi)

import json
import pandas as pd
import os
import streamlit as st
from src.database_admin import AdminDatabaseManager

class UserManager:
    def __init__(self, admin_db_manager: AdminDatabaseManager, users_file='data/users.json'):
        self.admin_db_manager = admin_db_manager
        self.users_file = users_file
        self.users_data = self._load_users()

    def _load_users(self):
        """
        Tải dữ liệu người dùng từ file JSON.
        Nếu file không tồn tại, tạo file và thư mục cần thiết.
        """
        if not os.path.exists(self.users_file):
            print(f"Không tìm thấy file người dùng tại {self.users_file}, tạo file mới...")
            dir_name = os.path.dirname(self.users_file)
            if dir_name and not os.path.exists(dir_name):
                os.makedirs(dir_name)
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)
            return {}
        try:
            with open(self.users_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            st.error(f"Lỗi khi tải file người dùng: {e}")
            return {}

    def get_user_role(self, email):
        """Lấy vai trò của người dùng dựa trên email. Trả về 'guest' nếu không tìm thấy."""
        user_data = self.users_data.get(email, {})
        return user_data.get("role", "guest")
        
    def save_users(self):
        """
        Lưu dữ liệu người dùng hiện tại và đẩy lên GitHub.
        """
        commit_message = "feat(users): Cập nhật dữ liệu người dùng"
        return self.admin_db_manager.save_and_push_json(self.users_file, self.users_data, commit_message)

    def get_all_users_as_df(self):
        """Trả về danh sách tất cả người dùng dưới dạng DataFrame của Pandas."""
        if not self.users_data:
            return pd.DataFrame(columns=["email", "role"])

        users_list = [
            {"email": email, "role": user_data.get("role", "guest")}
            for email, user_data in self.users_data.items()
        ]
        return pd.DataFrame(users_list)
        
    def add_or_update_user(self, email, role):
        """Thêm hoặc cập nhật vai trò của một người dùng."""
        if email:
            self.users_data[email] = {"role": role}
            return self.save_users()
        return False
        
    def delete_user(self, email):
        """Xóa một người dùng khỏi danh sách."""
        if email in self.users_data:
            del self.users_data[email]
            return self.save_users()
        return False