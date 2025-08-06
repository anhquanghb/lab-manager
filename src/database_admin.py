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
    def __init__(self, db_manager_instance):
        self.db_manager = db_manager_instance
        self.data_path = self.db_manager.data_path
        self.config_path = self.db_manager.config_path

    def save_inventory_to_json(self):
        # (Nội dung của hàm này giữ nguyên)
        if self.db_manager.inventory_data.empty:
            print("Không có dữ liệu trong inventory_data để lưu.")
            return False
        
        original_cols = [
            'id', 'name', 'type', 'quantity', 'unit', 'location', 'description',
            'iupac_name', 'vietnamese_name', 'chemical_formula', 'cas_number',
            'state_or_concentration', 'status', 'purpose', 'tracking', 'note'
        ]
        
        cols_to_save = [col for col in original_cols if col in self.db_manager.inventory_data.columns]
        data_to_save = self.db_manager.inventory_data[cols_to_save].to_dict(orient='records')

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
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.db_manager.config_data, f, ensure_ascii=False, indent=2)
            print(f"Đã lưu cấu hình vào {self.config_path} thành công.")
            return True
        except Exception as e:
            print(f"Lỗi khi lưu cấu hình vào JSON: {e}")
            return False

    def push_to_github(self, file_path_to_push, commit_message):
        """
        Thực hiện git add, git commit và git push cho một file cụ thể.
        """
        github_token = st.secrets.get("GITHUB_TOKEN")

        if not github_token:
            print("Lỗi: Không tìm thấy GitHub Personal Access Token trong st.secrets. Không thể đẩy thay đổi lên GitHub.")
            return False
        
        try:
            repo_path = Path(__file__).parent.parent
            repo = git.Repo(repo_path)
            
            with repo.config_writer() as cw:
                if not cw.has_option('user', 'email') or not cw.get_value('user', 'email'):
                    cw.set_value('user', 'email', 'chatbot@streamlit.app').release()
                if not cw.has_option('user', 'name') or not cw.get_value('user', 'name'):
                    cw.set_value('user', 'name', 'Streamlit Chatbot').release()
            
            repo_relative_path = file_path_to_push.relative_to(repo_path)
            repo.index.add([str(repo_relative_path)])
            repo.index.commit(commit_message)
            print(f"Đã commit '{repo_relative_path}' với thông báo: {commit_message}")

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
            
            print(f"Đang thực thi lệnh push cho {repo_relative_path}: {' '.join(push_command[:2])} *** (ẩn PAT) *** {' '.join(push_command[3:])}")
            process = subprocess.run(push_command, capture_output=True, text=True, check=True)
            print(f"Git Push stdout: {process.stdout}")
            print(f"Git Push stderr: {process.stderr}")

            print(f"Đã đẩy '{repo_relative_path}' lên GitHub thành công.")
            return True

        except git.InvalidGitRepositoryError:
            print("Lỗi: Thư mục dự án không phải là một kho lưu trữ Git hợp lệ.")
            return False
        except git.GitCommandError as e:
            print(f"Lỗi Git khi đẩy lên GitHub: {e.stderr or e.stdout}")
            return False
        except Exception as e:
            print(f"Lỗi không xác định khi đẩy lên GitHub: {e}")
            return False