import pandas as pd
import json
import os
import unicodedata 
import re 
from pathlib import Path
import git 
from datetime import datetime 
import streamlit as st 
from src.common_utils import remove_accents_and_normalize 

class DatabaseManager:
    def __init__(self, data_path='data/inventory.json'):
        project_root = Path(__file__).parent.parent
        self.data_path = project_root / data_path
        self.inventory_data = self._load_data()

    def _load_data(self):
        """
        Tải dữ liệu từ file JSON và chuẩn hóa các cột cần thiết.
        Dữ liệu JSON giờ đây đã có cấu trúc tách biệt rõ ràng hơn.
        """
        if not self.data_path.exists():
            print(f"Lỗi: Không tìm thấy file dữ liệu tại {self.data_path}")
            return pd.DataFrame()
        try:
            with open(self.data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            df = pd.DataFrame(data)

            # --- BẮT ĐẦU CHUẨN HÓA DỮ LIỆU SAU KHI TẢI (Sử dụng hàm từ common_utils) ---
            df['id_normalized'] = df['id'].apply(remove_accents_and_normalize)
            df['name_normalized'] = df['name'].apply(remove_accents_and_normalize)
            df['type_normalized'] = df['type'].apply(remove_accents_and_normalize)
            df['location_normalized'] = df['location'].apply(remove_accents_and_normalize)
            
            df['chemical_formula_normalized'] = df['chemical_formula'].apply(remove_accents_and_normalize)
            df['cas_number_normalized'] = df['cas_number'].apply(remove_accents_and_normalize)
            df['state_or_concentration_normalized'] = df['state_or_concentration'].apply(remove_accents_and_normalize)
            df['status_normalized'] = df['status'].apply(remove_accents_and_normalize)
            df['purpose_normalized'] = df['purpose'].apply(remove_accents_and_normalize)
            df['tracking_normalized'] = df['tracking'].apply(remove_accents_and_normalize)
            df['iupac_name_normalized'] = df['iupac_name'].apply(remove_accents_and_normalize)
            df['vietnamese_name_normalized'] = df['vietnamese_name'].apply(remove_accents_and_normalize)
            
            df['description_normalized'] = df['description'].apply(remove_accents_and_normalize)
            # BỔ SUNG: Chuẩn hóa cột 'note' mới
            # Cần đảm bảo cột 'note' tồn tại trước khi áp dụng .apply()
            if 'note' in df.columns: 
                df['note_normalized'] = df['note'].apply(remove_accents_and_normalize)
            else:
                df['note'] = None # Tạo cột 'note' nếu nó chưa tồn tại (cho dữ liệu cũ)
                df['note_normalized'] = None # Và cột normalized của nó

            return df
        except json.JSONDecodeError:
            print(f"Lỗi: File {self.data_path} không phải là JSON hợp lệ.")
            return pd.DataFrame()
        except Exception as e:
            print(f"Lỗi khi tải dữ liệu: {e}")
            return pd.DataFrame()

    def search_item(self, query):
        if self.inventory_data.empty:
            return pd.DataFrame()

        query_normalized = remove_accents_and_normalize(query)

        search_cols = [
            'id_normalized', 'name_normalized', 'type_normalized', 
            'location_normalized', 'description_normalized', 
            'chemical_formula_normalized', 'cas_number_normalized',
            'iupac_name_normalized', 'vietnamese_name_normalized',
            'note_normalized' # BỔ SUNG: Thêm cột note vào tìm kiếm
        ]
        
        # Lọc ra chỉ các cột thực sự tồn tại trong DataFrame
        existing_search_cols = [col for col in search_cols if col in self.inventory_data.columns]

        mask = self.inventory_data[existing_search_cols].apply(
            lambda col: col.fillna('').astype(str).str.contains(query_normalized, na=False)
        ).any(axis=1)

        results = self.inventory_data[mask]
        return results
    
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

    def get_all_locations(self):
        """
        Lấy danh sách tất cả các vị trí lưu trữ duy nhất từ cơ sở dữ liệu.
        Trả về một list các chuỗi vị trí.
        """
        if self.inventory_data.empty or 'location' not in self.inventory_data.columns:
            return []
        
        locations = self.inventory_data['location'].dropna().unique().tolist()
        if "Không rõ" in locations:
            locations.remove("Không rõ")
        return sorted(locations)

    def get_by_id(self, item_id):
        if self.inventory_data.empty:
            return pd.DataFrame()

        item_id_normalized = remove_accents_and_normalize(item_id)
        results = self.inventory_data[self.inventory_data['id_normalized'] == item_id_normalized]
        return results

    def list_by_location(self, location_query):
        if self.inventory_data.empty:
            return pd.DataFrame()

        location_query_normalized = remove_accents_and_normalize(location_query)
        results = self.inventory_data[self.inventory_data['location_normalized'].str.contains(location_query_normalized, na=False)]
        return results

    def list_by_type(self, item_type):
        if self.inventory_data.empty:
            return pd.DataFrame()

        item_type_normalized = remove_accents_and_normalize(item_type)
        results = self.inventory_data[self.inventory_data['type_normalized'] == item_type_normalized]
        return results

    def list_by_status(self, status_query):
        if self.inventory_data.empty:
            return pd.DataFrame()

        status_query_normalized = remove_accents_and_normalize(status_query)
        results = self.inventory_data[self.inventory_data['status_normalized'] == status_query_normalized]
        return results

    def list_by_location_and_status(self, location_query, status_query):
        if self.inventory_data.empty:
            return pd.DataFrame()

        location_query_normalized = remove_accents_and_normalize(location_query)
        status_query_normalized = remove_accents_and_normalize(status_query)

        mask_location = self.inventory_data['location_normalized'].str.contains(location_query_normalized, na=False)
        mask_status = self.inventory_data['status_normalized'] == status_query_normalized

        results = self.inventory_data[mask_location & mask_status]
        return results

    def list_by_type_and_status(self, item_type, status_query):
        if self.inventory_data.empty:
            return pd.DataFrame()

        item_type_normalized = remove_accents_and_normalize(item_type)
        status_query_normalized = remove_accents_and_normalize(status_query)

        mask_type = self.inventory_data['type_normalized'] == item_type_normalized
        mask_status = self.inventory_data['status_normalized'] == status_query_normalized

        results = self.inventory_data[mask_type & mask_status]
        return results

    def list_by_type_and_location(self, item_type, location_query):
        if self.inventory_data.empty:
            return pd.DataFrame()

        item_type_normalized = remove_accents_and_normalize(item_type)
        location_query_normalized = remove_accents_and_normalize(location_query)

        mask_type = self.inventory_data['type_normalized'] == item_type_normalized
        mask_location = self.inventory_data['location_normalized'].str.contains(location_query_normalized, na=False)

        results = self.inventory_data[mask_type & mask_location]
        return results
 
    def search_by_cas(self, cas_number):
        if self.inventory_data.empty:
            return pd.DataFrame()

        cas_number_normalized = remove_accents_and_normalize(cas_number)
        results = self.inventory_data[self.inventory_data['cas_number_normalized'] == cas_number_normalized]
        return results

    def upload_logs_to_github_on_startup(self, log_filepath):
        github_token = st.secrets.get("GITHUB_TOKEN")

        if not github_token:
            print("Lỗi: Không tìm thấy GitHub Personal Access Token trong st.secrets. Không thể tải log lên GitHub.")
            return False

        try:
            repo_path = Path(__file__).parent.parent

            try:
                repo = git.Repo(repo_path)
            except git.InvalidGitRepositoryError:
                print(f"DEBUG: {repo_path} không phải là kho lưu trữ Git hợp lệ. Bỏ qua tải log.")
                return False

            print(f"Đường dẫn repo đang xét để tải log: {repo_path}")

            with repo.config_writer() as cw:
                if not cw.has_option('user', 'email') or not cw.get_value('user', 'email'):
                    cw.set_value('user', 'email', 'chatbot@streamlit.app').release()
                if not cw.has_option('user', 'name') or not cw.get_value('user', 'name'):
                    cw.set_value('user', 'name', 'Streamlit Chatbot').release()
            print("Đã cấu hình thông tin người dùng Git.")

            if not Path(log_filepath).exists() or Path(log_filepath).stat().st_size == 0:
                print("Không có dữ liệu nhật ký để tải lên (file log rỗng hoặc không tồn tại).")
                return True

            with open(log_filepath, 'r', encoding='utf-8') as f:
                log_content = f.read()
            print("Đã đọc nội dung file log cục bộ.")

            archive_dir = repo_path / 'logs' / 'archive'
            archive_dir.mkdir(parents=True, exist_ok=True)
            print(f"DEBUG: Đã tạo thư mục lưu trữ mới: {archive_dir}")

            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_filename = f"chat_log_archive_{timestamp_str}.jsonl"
            archive_filepath = archive_dir / archive_filename

            with open(archive_filepath, 'w', encoding='utf-8') as f:
                f.write(log_content)
            print(f"Đã ghi nội dung vào file lưu trữ: {archive_filepath}")

            repo_relative_archive_filepath = archive_filepath.relative_to(repo_path)
            repo.index.add([str(repo_relative_archive_filepath)])
            commit_message = f"feat(logs): Archive chat log {archive_filename}"
            repo.index.commit(commit_message)
            print(f"Đã commit file {archive_filename} với thông báo: {commit_message}")

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
            
            print(f"Đang thực thi lệnh push: {' '.join(push_command[:2])} *** (ẩn PAT) *** {' '.join(push_command[3:])}")
            process = subprocess.run(push_command, capture_output=True, text=True, check=True)
            print(f"Git Push stdout: {process.stdout}")
            print(f"Git Push stderr: {process.stderr}")

            print("Đã làm rỗng file log cục bộ.")
            with open(log_filepath, 'w', encoding='utf-8') as f:
                f.truncate(0)

            return True

        except git.InvalidGitRepositoryError:
            print("Lỗi: Thư mục dự án không phải là một kho lưu trữ Git hợp lệ.")
            return False
        except git.GitCommandError as e:
            print(f"Lỗi Git khi tải nhật ký lên GitHub: {e.stderr or e.stdout}")
            return False
        except Exception as e:
            print(f"Lỗi không xác định khi tải nhật ký lên GitHub: {e}")
            return False