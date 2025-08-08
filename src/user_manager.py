# src/user_manager.py

import json
import pandas as pd
import os

class UserManager:
    def __init__(self, users_file='data/users.json'):
        # SỬA: Sử dụng trực tiếp string path để tương thích cloud
        self.users_file = users_file
        self.users_data = self._load_users()

    def _load_users(self):
        """
        Tải dữ liệu người dùng từ file JSON. 
        Nếu file không tồn tại, tạo file và thư mục cần thiết.
        """
        # SỬA: Dùng os.path.exists và os.makedirs để kiểm tra và tạo file/thư mục
        if not os.path.exists(self.users_file):
            print(f"Không tìm thấy file người dùng tại {self.users_file}, tạo file mới...")
            
            # Lấy ra tên thư mục từ đường dẫn
            dir_name = os.path.dirname(self.users_file)
            
            # Tạo thư mục nếu nó chưa tồn tại và không phải là thư mục gốc
            if dir_name and not os.path.exists(dir_name):
                os.makedirs(dir_name)
                
            # Tạo file rỗng
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
        # Dùng .get() để tránh lỗi nếu email không tồn tại
        user_data = self.users_data.get(email, {})
        return user_data.get("role", "guest")
        
    def save_users(self):
        """Lưu dữ liệu người dùng hiện tại vào file JSON."""
        try:
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(self.users_data, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"Lỗi khi lưu file người dùng: {e}")
            return False

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