import pandas as pd
import json
import os
import re # Giữ lại nếu cần các hàm regex khác, nếu không có thể xóa
from pathlib import Path
import git
from datetime import datetime
import streamlit as st
from src.common_utils import remove_accents_and_normalize # Import hàm chuẩn hóa

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
            'state_or_concentration', 'status', 'purpose', 'tracking'
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
        """
        Thực hiện git add, git commit và git push cho file data/inventory.json.
        Tái sử dụng logic Git.
        """
        github_token = st.secrets.get("GITHUB_TOKEN")

        if not github_token:
            print("Lỗi: Không tìm thấy GitHub Personal Access Token trong st.secrets. Không thể đẩy inventory lên GitHub.")
            return False
        
        try:
            repo_path = Path(__file__).parent.parent
            repo = git.Repo(repo_path)

            # Cấu hình thông tin người dùng Git nếu chưa có
            with repo.config_writer() as cw:
                if not cw.has_option('user', 'email') or not cw.get_value('user', 'email'):
                    cw.set_value('user', 'email', 'chatbot@streamlit.app').release()
                if not cw.has_option('user', 'name') or not cw.get_value('user', 'name'):
                    cw.set_value('user', 'name', 'Streamlit Chatbot').release()
            
            # Thêm file inventory.json vào staging
            repo_relative_inventory_path = self.data_path.relative_to(repo_path)
            repo.index.add([str(repo_relative_inventory_path)])

            # Commit thay đổi
            repo.index.commit(commit_message)
            print(f"Đã commit '{repo_relative_inventory_path}' với thông báo: {commit_message}")

            # Lấy URL remote và chuẩn bị cho xác thực PAT
            remote_url = repo.remotes.origin.url
            repo_url_with_auth = ""
            if remote_url.startswith("git@github.com:"):
                repo_path_no_git = remote_url.replace("git@github.com:", "").replace(".git", "")
                repo_url_with_auth = f"https://oauth2:{github_token}@github.com/{repo_path_no_git}"
            elif remote_url.startswith("https://github.com/"):
                parts = remote_url.split("https://github.com/")
                repo_url_with_auth = f"https://oauth2:{github_token}@github.com/{parts[1]}"
            else:
                print(f"Lỗi: Định dạng URL remote không được hỗ trợ: {remote_url}")
                return False

            current_branch = repo.active_branch.name
            import subprocess
            push_command = [
                'git', 'push',
                repo_url_with_auth,
                f'{current_branch}:{current_branch}'
            ]
            
            print(f"Đang thực thi lệnh push cho inventory.json: {' '.join(push_command[:2])} *** (ẩn PAT) *** {' '.join(push_command[3:])}")
            process = subprocess.run(push_command, capture_output=True, text=True, check=True)
            print(f"Git Push stdout: {process.stdout}")
            print(f"Git Push stderr: {process.stderr}")

            print(f"Đã đẩy '{repo_relative_inventory_path}' lên GitHub thành công.")
            return True

        except git.InvalidGitRepositoryError:
            print("Lỗi: Thư mục dự án không phải là một kho lưu trữ Git hợp lệ.")
            return False
        except git.GitCommandError as e:
            print(f"Lỗi Git khi đẩy inventory lên GitHub: {e.stderr or e.stdout}")
            return False
        except Exception as e:
            print(f"Lỗi không xác định khi đẩy inventory lên GitHub: {e}")
            return False