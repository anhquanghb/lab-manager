# src/database_admin.py

import json
import os
import git
import streamlit as st

# Import lớp cha để kế thừa
from src.database_manager import DatabaseManager

class AdminDatabaseManager(DatabaseManager):
    """
    Lớp quản lý các tác vụ admin, kế thừa các phương thức đọc
    từ DatabaseManager và bổ sung các phương thức ghi.
    """
    def __init__(self, data_path='data/inventory.json', config_path='data/config.json'):
        # Gọi hàm __init__ của lớp cha (DatabaseManager) để tải dữ liệu.
        super().__init__(data_path, config_path)

    def save_inventory_to_json(self):
        """Lưu dữ liệu kho hàng hiện tại vào file inventory.json."""
        if self.inventory_data.empty:
            print("Không có dữ liệu trong inventory_data để lưu.")
            return False
        
        original_cols = [
            'id', 'name', 'type', 'quantity', 'unit', 'location', 'description',
            'iupac_name', 'vietnamese_name', 'chemical_formula', 'cas_number',
            'state_or_concentration', 'status', 'purpose', 'tracking', 'note'
        ]
        
        cols_to_save = [col for col in original_cols if col in self.inventory_data.columns]
        data_to_save = self.inventory_data[cols_to_save].to_dict(orient='records')
        
        commit_message = f"feat(admin): Cập nhật thông tin từ giao diện Admin"
        return self.save_and_push_json(self.data_path, data_to_save, commit_message)

    def save_config_to_json(self):
        """Lưu cấu hình hiện tại vào file config.json."""
        commit_message = f"feat(config): Cập nhật cài đặt từ giao diện Admin"
        return self.save_and_push_json(self.config_path, self.config_data, commit_message)

    def save_and_push_json(self, file_path, data, commit_message):
        """Hàm chung để lưu dữ liệu vào file JSON và đẩy lên GitHub."""
        try:
            dir_name = os.path.dirname(file_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            
            print(f"Đã lưu dữ liệu vào {file_path} thành công.")
            
            if self.push_to_github(file_path, commit_message):
                st.success(f"Đã đẩy thay đổi của {file_path} lên GitHub!")
                return True
            else:
                st.error(f"Lỗi: Không thể đẩy thay đổi của {file_path} lên GitHub.")
                return False
        except Exception as e:
            st.error(f"Lỗi khi lưu và đẩy file JSON: {e}")
            print(f"Lỗi khi lưu và đẩy file JSON: {e}")
            return False

    def push_to_github(self, file_path_to_push, commit_message):
        """Thực hiện git add, commit và git push cho một file cụ thể."""
        github_token = st.secrets.get("GITHUB_TOKEN")

        if not github_token:
            st.error("Lỗi: Không tìm thấy GitHub Personal Access Token trong secrets.")
            return False
        
        try:
            # Giả định thư mục hiện tại là gốc của repo khi chạy trên cloud
            repo_path = "."
            repo = git.Repo(repo_path)
            
            # Cấu hình user git
            with repo.config_writer() as cw:
                cw.set_value('user', 'email', 'streamlit.app@email.com').release()
                cw.set_value('user', 'name', 'Streamlit App').release()
            
            # Add và commit
            repo.index.add([file_path_to_push])
            repo.index.commit(commit_message)
            print(f"Đã commit '{file_path_to_push}' với thông báo: {commit_message}")

            # Dùng phương thức push của GitPython thay vì subprocess
            remote = repo.remote(name='origin')
            original_url = remote.url
            
            # Tạo URL với token để xác thực
            if original_url.startswith("https://"):
                repo_url_with_auth = original_url.replace("https://", f"https://oauth2:{github_token}@")
            else:
                st.error(f"Định dạng URL remote không được hỗ trợ: {original_url}")
                return False

            # Tạm thời thay đổi URL của remote để push, sau đó trả về như cũ
            try:
                remote.set_url(repo_url_with_auth)
                remote.push(repo.active_branch.name)
                print(f"Đã đẩy '{file_path_to_push}' lên GitHub thành công.")
            finally:
                remote.set_url(original_url) # Khôi phục URL gốc

            return True

        except git.GitCommandError as e:
            st.error(f"Lỗi Git khi đẩy lên GitHub: {e.stderr or e.stdout}")
            print(f"Lỗi Git khi đẩy lên GitHub: {e.stderr or e.stdout}")
            return False
        except Exception as e:
            st.error(f"Lỗi không xác định khi đẩy lên GitHub: {e}")
            print(f"Lỗi không xác định khi đẩy lên GitHub: {e}")
            return False