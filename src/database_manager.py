import pandas as pd
import json
import os
import unicodedata
import git # Import cho GitPython
from datetime import datetime # Import cho timestamp
import streamlit as st # Import để truy cập st.secrets

class DatabaseManager:
    def __init__(self, data_path='data/inventory.json'):
        self.data_path = os.path.join(os.path.dirname(__file__), '..', data_path)
        self.inventory_data = self._load_data()

    def _load_data(self):
        """Tải dữ liệu từ file JSON."""
        if not os.path.exists(self.data_path):
            print(f"Lỗi: Không tìm thấy file dữ liệu tại {self.data_path}")
            return pd.DataFrame()
        try:
            with open(self.data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return pd.DataFrame(data)
        except json.JSONDecodeError:
            print(f"Lỗi: File {self.data_path} không phải là JSON hợp lệ.")
            return pd.DataFrame()
        except Exception as e:
            print(f"Lỗi khi tải dữ liệu: {e}")
            return pd.DataFrame()

    def _remove_accents(self, input_str):
        """Hàm trợ giúp để loại bỏ dấu tiếng Việt và chuẩn hóa chuỗi."""
        if not isinstance(input_str, str):
            return str(input_str)
        nfkd_form = unicodedata.normalize('NFKD', input_str)
        only_ascii = nfkd_form.encode('ascii', 'ignore').decode('utf-8')
        return only_ascii

    def search_item(self, query):
        """
        Tìm kiếm vật tư/hóa chất theo bất kỳ thông tin liên quan nào
        bao gồm: id, name, type, location, và description. (Tìm kiếm chung)
        """
        if self.inventory_data.empty:
            return pd.DataFrame()

        query_normalized = self._remove_accents(query.lower())
        
        searchable_df = self.inventory_data[['id', 'name', 'type', 'location', 'description']].astype(str)
        searchable_df = searchable_df.applymap(self._remove_accents).apply(lambda x: x.str.lower())
        
        mask = searchable_df.apply(lambda col: col.str.contains(query_normalized, na=False)).any(axis=1)
        
        results = self.inventory_data[mask]
        return results

    def get_quantity(self, item_name):
        """Lấy số lượng của một vật tư/hóa chất cụ thể."""
        if self.inventory_data.empty:
            return None, None

        item_name_normalized = self._remove_accents(item_name.lower())
        
        found_item = self.inventory_data[self.inventory_data['name'].apply(self._remove_accents).str.lower() == item_name_normalized]
        
        if not found_item.empty:
            return found_item.iloc[0]['quantity'], found_item.iloc[0]['unit']
        return None, None

    def get_location(self, item_name):
        """Lấy vị trí của một vật tư/hóa chất cụ thể."""
        if self.inventory_data.empty:
            return None

        item_name_normalized = self._remove_accents(item_name.lower())
        found_item = self.inventory_data[self.inventory_data['name'].apply(self._remove_accents).str.lower() == item_name_normalized]
        
        if not found_item.empty:
            return found_item.iloc[0]['location']
        return None

    # --- CÁC HÀM TÌM KIẾM KHÁC (được gọi từ ChatbotLogic) ---

    def get_by_id(self, item_id):
        """Tìm kiếm vật tư/hóa chất theo ID chính xác."""
        if self.inventory_data.empty:
            return pd.DataFrame()
        
        item_id_normalized = self._remove_accents(item_id.lower())
        results = self.inventory_data[self.inventory_data['id'].apply(self._remove_accents).str.lower() == item_id_normalized]
        return results

    def list_by_location(self, location_query):
        """Liệt kê vật tư/hóa chất theo vị trí."""
        if self.inventory_data.empty:
            return pd.DataFrame()
        
        location_query_normalized = self._remove_accents(location_query.lower())
        results = self.inventory_data[self.inventory_data['location'].apply(self._remove_accents).str.lower().str.contains(location_query_normalized, na=False)]
        return results

    def list_by_type(self, item_type):
        """Liệt kê vật tư/hóa chất theo loại."""
        if self.inventory_data.empty:
            return pd.DataFrame()
        
        item_type_normalized = self._remove_accents(item_type.lower())
        results = self.inventory_data[self.inventory_data['type'].apply(self._remove_accents).str.lower() == item_type_normalized]
        return results
    
    def list_by_status(self, status_query):
        """Liệt kê vật tư/hóa chất theo tình trạng trong mô tả."""
        if self.inventory_data.empty:
            return pd.DataFrame()
        
        status_query_normalized = self._remove_accents(status_query.lower())
        results = self.inventory_data[self.inventory_data['description'].apply(self._remove_accents).str.lower().str.contains(status_query_normalized, na=False)]
        return results

    def list_by_location_and_status(self, location_query, status_query):
        """Liệt kê vật tư/hóa chất theo vị trí VÀ tình trạng."""
        if self.inventory_data.empty:
            return pd.DataFrame()
        
        location_query_normalized = self._remove_accents(location_query.lower())
        status_query_normalized = self._remove_accents(status_query.lower())
        
        normalized_location_col = self.inventory_data['location'].apply(self._remove_accents).str.lower()
        normalized_description_col = self.inventory_data['description'].apply(self._remove_accents).str.lower()

        mask_location = normalized_location_col.str.contains(location_query_normalized, na=False)
        mask_status = normalized_description_col.str.contains(status_query_normalized, na=False)
        
        results = self.inventory_data[mask_location & mask_status]
        return results

    def list_by_type_and_status(self, item_type, status_query):
        """Liệt kê vật tư/hóa chất theo loại VÀ tình trạng."""
        if self.inventory_data.empty:
            return pd.DataFrame()
        
        item_type_normalized = self._remove_accents(item_type.lower())
        status_query_normalized = self._remove_accents(status_query.lower())
        
        normalized_type_col = self.inventory_data['type'].apply(self._remove_accents).str.lower()
        normalized_description_col = self.inventory_data['description'].apply(self._remove_accents).str.lower()

        mask_type = normalized_type_col == item_type_normalized
        mask_status = normalized_description_col.str.contains(status_query_normalized, na=False)
        
        results = self.inventory_data[mask_type & mask_status]
        return results
    
    def list_by_type_and_location(self, item_type, location_query):
        """Liệt kê vật tư/hóa chất theo loại VÀ vị trí."""
        if self.inventory_data.empty:
            return pd.DataFrame()
        
        item_type_normalized = self._remove_accents(item_type.lower())
        location_query_normalized = self._remove_accents(location_query.lower())
        
        normalized_type_col = self.inventory_data['type'].apply(self._remove_accents).str.lower()
        normalized_location_col = self.inventory_data['location'].apply(self._remove_accents).str.lower()

        mask_type = normalized_type_col == item_type_normalized
        mask_location = normalized_location_col.str.contains(location_query_normalized, na=False)
        
        results = self.inventory_data[mask_type & mask_location]
        return results

    def search_by_cas(self, cas_number):
        """Tìm kiếm vật tư/hóa chất theo số CAS."""
        if self.inventory_data.empty:
            return pd.DataFrame()
        
        cas_number_normalized = self._remove_accents(cas_number.lower())
        results = self.inventory_data[self.inventory_data['description'].apply(self._remove_accents).str.lower().str.contains(f"cas: {cas_number_normalized}", na=False)]
        return results

    # --- CHỨC NĂNG TẢI LOG LÊN GITHUB TỰ ĐỘNG KHI KHỞI ĐỘNG ỨNG DỤNG ---
    def upload_logs_to_github_on_startup(self, log_filename_from_chatbot_logic):
        """
        Hàm này được gọi khi ứng dụng khởi động (từ main.py).
        Đọc file log hiện tại, tải lên GitHub và làm rỗng file log cục bộ.
        Sử dụng Personal Access Token (PAT) từ Streamlit secrets.
        """
        github_token = st.secrets.get("GITHUB_TOKEN")
        
        if not github_token:
            print("Lỗi: Không tìm thấy GitHub Personal Access Token trong st.secrets. Không thể tải log lên GitHub.")
            return False # Trả về False nếu không có token

        try:
            # Lấy đường dẫn thư mục gốc của repo (ví dụ: /mount/src/lab-manager)
            repo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) 
            
            # Khởi tạo đối tượng Git Repo.
            try:
                repo = git.Repo(repo_path)
            except git.InvalidGitRepositoryError:
                print(f"DEBUG: {repo_path} không phải là kho lưu trữ Git hợp lệ. Bỏ qua tải log.")
                return False

            print(f"Đường dẫn repo đang xét để tải log: {repo_path}")
            
            # Cấu hình thông tin người dùng Git nếu chưa có
            with repo.config_writer() as cw:
                if not cw.has_option('user', 'email') or not cw.get_value('user', 'email'):
                    cw.set_value('user', 'email', 'chatbot@streamlit.app').release()
                if not cw.has_option('user', 'name') or not cw.get_value('user', 'name'):
                    cw.set_value('user', 'name', 'Streamlit Chatbot').release()
            print("Đã cấu hình thông tin người dùng Git.")

            # Đường dẫn đầy đủ đến file log hiện tại
            local_log_filepath = os.path.join(repo_path, 'logs', log_filename_from_chatbot_logic)

            # Đọc nội dung log hiện tại
            if not os.path.exists(local_log_filepath) or os.stat(local_log_filepath).st_size == 0:
                print("Không có dữ liệu nhật ký để tải lên (file log rỗng hoặc không tồn tại).")
                return True # Không có gì để tải lên, coi như thành công
            
            with open(local_log_filepath, 'r', encoding='utf-8') as f:
                log_content = f.read()
            print("Đã đọc nội dung file log cục bộ.")

            # Tạo thư mục archive nếu chưa có
            archive_dir = os.path.join(repo_path, 'logs', 'archive')
            if not os.path.exists(archive_dir):
                os.makedirs(archive_dir)
                print(f"DEBUG: Đã tạo thư mục lưu trữ mới: {archive_dir}")

            # Tạo tên file log lưu trữ với timestamp
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_filename = f"chat_log_archive_{timestamp_str}.jsonl"
            archive_filepath = os.path.join(archive_dir, archive_filename) # Path tuyệt đối
            
            # Ghi nội dung vào file log lưu trữ
            with open(archive_filepath, 'w', encoding='utf-8') as f:
                f.write(log_content)
            print(f"Đã ghi nội dung vào file lưu trữ: {archive_filepath}")

            # Thêm file vào Git và commit
            repo_relative_archive_filepath = os.path.relpath(archive_filepath, repo_path)
            repo.index.add([repo_relative_archive_filepath])
            commit_message = f"feat(logs): Archive chat log {archive_filename}"
            repo.index.commit(commit_message)
            print(f"Đã commit file {archive_filename} với thông báo: {commit_message}")

            # Lấy URL remote và chuẩn bị cho xác thực PAT
            remote_url = repo.remotes.origin.url
            print(f"URL remote gốc: {remote_url}")
            
            repo_url_with_auth = ""
            if remote_url.startswith("git@github.com:"):
                repo_path_no_git = remote_url.replace("git@github.com:", "").replace(".git", "")
                repo_url_with_auth = f"https://oauth2:{github_token}@github.com/{repo_path_no_git}.git"
                print(f"Đã chuyển đổi URL SSH sang HTTPS: {repo_url_with_auth}")
            elif remote_url.startswith("https://github.com/"):
                parts = remote_url.split("https://github.com/")
                repo_url_with_auth = f"https://oauth2:{github_token}@github.com/{parts[1]}"
                print(f"Đã thêm PAT vào URL HTTPS: {repo_url_with_auth}")
            else:
                print(f"Lỗi: Định dạng URL remote không được hỗ trợ: {remote_url}")
                return False # Trả về False nếu không xác định được URL

            current_branch = repo.active_branch.name
            print(f"Nhánh hiện tại: {current_branch}")
            
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

            # Làm rỗng file log cục bộ sau khi tải lên thành công
            with open(local_log_filepath, 'w', encoding='utf-8') as f:
                f.truncate(0)
            print("Đã làm rỗng file log cục bộ.")

            return True # Trả về True nếu thành công

        except git.InvalidGitRepositoryError:
            print("Lỗi: Thư mục dự án không phải là một kho lưu trữ Git hợp lệ.")
            return False
        except git.GitCommandError as e:
            print(f"Lỗi Git khi tải nhật ký lên GitHub: {e.stderr or e.stdout}")
            return False
        except Exception as e:
            print(f"Lỗi không xác định khi tải nhật ký lên GitHub: {e}")
            return False