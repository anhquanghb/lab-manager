# src/database_admin.py

import json
from pathlib import Path
import git
import streamlit as st
import subprocess

# Import lớp cha để kế thừa
from src.database_manager import DatabaseManager

class AdminDatabaseManager(DatabaseManager):
    """
    Lớp quản lý các tác vụ admin, kế thừa các phương thức đọc
    từ DatabaseManager và bổ sung các phương thức ghi.
    """
    def __init__(self, data_path='data/inventory.json', config_path='data/config.json'):
        # Gọi hàm __init__ của lớp cha (DatabaseManager) để tải dữ liệu
        # Giờ đây nó không cần nhận db_manager_instance nữa
        super().__init__(data_path, config_path)

    def save_inventory_to_json(self):
        """Lưu dữ liệu kho hàng hiện tại vào file inventory.json."""
        # self.inventory_data và self.data_path được kế thừa từ lớp cha
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

        try:
            self.data_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.data_path, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)
            print(f"Đã lưu inventory_data vào {self.data_path} thành công.")
            return True
        except Exception as e:
            print(f"Lỗi khi lưu inventory_data vào JSON: {e}")
            return False

    def save_config_to_json(self):
        """Lưu cấu hình hiện tại vào file config.json."""
        # self.config_data và self.config_path được kế thừa từ lớp cha
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, ensure_ascii=False, indent=2)
            print(f"Đã lưu cấu hình vào {self.config_path} thành công.")
            return True
        except Exception as e:
            print(f"Lỗi khi lưu cấu hình vào JSON: {e}")
            return False

    def push_to_github(self, file_path_to_push, commit_message):
        """Thực hiện git add, git commit và git push cho một file cụ thể."""
        github_token = st.secrets.get("GITHUB_TOKEN")

        if not github_token:
            st.error("Lỗi: Không tìm thấy GitHub Personal Access Token.")
            return False
        
        try:
            repo_path = Path(__file__).parent.parent
            repo = git.Repo(repo_path)
            
            # Cấu hình user git
            with repo.config_writer() as cw:
                cw.set_value('user', 'email', 'chatbot@streamlit.app').release()
                cw.set_value('user', 'name', 'Streamlit Chatbot').release()
            
            # Add và commit
            repo_relative_path = Path(file_path_to_push).relative_to(repo_path)
            repo.index.add([str(repo_relative_path)])
            repo.index.commit(commit_message)
            print(f"Đã commit '{repo_relative_path}' với thông báo: {commit_message}")

            # Push
            remote_url = repo.remotes.origin.url
            if remote_url.startswith("https://"):
                repo_url_with_auth = remote_url.replace("https://", f"https://oauth2:{github_token}@")
            else:
                st.error(f"Định dạng URL remote không được hỗ trợ: {remote_url}")
                return False
            
            repo.remotes.origin.push(repo.active_branch.name)
            print(f"Đã đẩy '{repo_relative_path}' lên GitHub thành công.")
            return True

        except git.GitCommandError as e:
            st.error(f"Lỗi Git khi đẩy lên GitHub: {e.stderr or e.stdout}")
            return False
        except Exception as e:
            st.error(f"Lỗi không xác định khi đẩy lên GitHub: {e}")
            return False