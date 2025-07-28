import pandas as pd
import json
import os
import unicodedata
import git 
from datetime import datetime
import streamlit as st

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
            df = pd.DataFrame(data)
            # Tạo các cột đã chuẩn hóa (lower, bỏ dấu) ngay khi tải dữ liệu
            for col in ['id', 'name', 'type', 'location', 'description', 
                        'formula', 'cas_number', 'state_or_concentration', 
                        'status_text', 'tracking', 'purpose']:
                if col in df.columns:
                    # Thay thế applymap bằng map
                    df[f'{col}_normalized'] = df[col].apply(self._remove_accents).str.lower()
                else:
                    df[f'{col}_normalized'] = "" 

            return df
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
        s = input_str.lower().strip()
        nfkd_form = unicodedata.normalize('NFKD', s)
        only_ascii = nfkd_form.encode('ascii', 'ignore').decode('utf-8')
        return only_ascii

    def search_item(self, query):
        """
        Tìm kiếm vật tư/hóa chất theo bất kỳ thông tin liên quan nào
        bao gồm: id, name, type, location, formula, cas_number, status_text, description.
        """
        if self.inventory_data.empty:
            return pd.DataFrame()

        query_normalized = self._remove_accents(query)

        search_cols = [
            'id_normalized', 'name_normalized', 'type_normalized', 
            'location_normalized', 'description_normalized', 'formula_normalized', 
            'cas_number_normalized', 'state_or_concentration_normalized', 
            'status_text_normalized', 'tracking_normalized', 'purpose_normalized'
        ]

        valid_search_cols = [col for col in search_cols if col in self.inventory_data.columns]

        # Thay thế applymap bằng map
        mask = self.inventory_data[valid_search_cols].map(
            lambda x: x.str.contains(query_normalized, na=False) if isinstance(x, pd.Series) else False # Thêm kiểm tra isinstance(x, pd.Series)
        ).any(axis=1) # The apply().any(axis=1) is already correct. This is complicated.

        # Simpler replacement for applymap: direct map if the function applies element-wise
        # For applying a function element-wise across *all* columns of a DataFrame in this context:
        # We already create _normalized columns on load. So searchable_df contains normalized data.
        # We only need to check contains.

        # Revert to a simpler search logic that uses already normalized data.
        # The issue was in searchable_df = searchable_df.applymap(self._remove_accents).apply(lambda x: x.str.lower())
        # This line is in load_data already. So here we just need to use the _normalized columns.

        # Let's adjust the original search_item to work with the pre-normalized columns.
        # The error means the `DataFrame.applymap` on line 49 is problematic.
        # Line 49 in my current `database_manager.py` is `searchable_df = searchable_df.applymap(self._remove_accents).apply(lambda x: x.str.lower())`
        # This line IS the problem. It's redundant and causing the warning.
        # `_load_data` already creates `_normalized` columns. So `search_item` should use them directly.

        # Removing the problematic line 49 and adjust search_cols if necessary
        # The current `search_item` does this:
        # searchable_df = self.inventory_data[['id', 'name', 'type', 'location', 'description', 'formula', 'cas_number', 'state_or_concentration', 'status_text', 'tracking', 'purpose']].astype(str)
        # searchable_df = searchable_df.applymap(self._remove_accents).apply(lambda x: x.str.lower())
        # This is the line creating the problem. It re-normalizes already normalized data.

        # Remove line 49 and adjust `search_cols` directly.

        search_cols_to_use = [
            'id_normalized', 'name_normalized', 'type_normalized', 
            'location_normalized', 'description_normalized', 'formula_normalized', 
            'cas_number_normalized', 'state_or_concentration_normalized', 
            'status_text_normalized', 'tracking_normalized', 'purpose_normalized'
        ]

        # Filter for columns that actually exist in the DataFrame
        valid_search_cols = [col for col in search_cols_to_use if col in self.inventory_data.columns]

        # Perform the search on the already normalized columns
        mask = self.inventory_data[valid_search_cols].apply(
            lambda col: col.str.contains(query_normalized, na=False)
        ).any(axis=1)

        results = self.inventory_data[mask]
        return results

def get_quantity(self, item_name):
    """Lấy số lượng của một vật tư/hóa chất cụ thể."""
    if self.inventory_data.empty:
        return None, None

    item_name_normalized = self._remove_accents(item_name)

    # Sử dụng cột đã chuẩn hóa
    found_item = self.inventory_data[self.inventory_data['name_normalized'] == item_name_normalized]

    if not found_item.empty:
        return found_item.iloc[0]['quantity'], found_item.iloc[0]['unit']
    return None, None

def get_location(self, item_name):
    """Lấy vị trí của một vật tư/hóa chất cụ thể."""
    if self.inventory_data.empty:
        return None

    item_name_normalized = self._remove_accents(item_name)
    # Sử dụng cột đã chuẩn hóa
    found_item = self.inventory_data[self.inventory_data['name_normalized'] == item_name_normalized]

    if not found_item.empty:
        return found_item.iloc[0]['location']
    return None

# --- CÁC HÀM TÌM KIẾM KHÁC (được gọi từ ChatbotLogic) ---

def get_by_id(self, item_id):
    """Tìm kiếm vật tư/hóa chất theo ID chính xác."""
    if self.inventory_data.empty:
        return pd.DataFrame()

    item_id_normalized = self._remove_accents(item_id)
    # Sử dụng cột đã chuẩn hóa
    results = self.inventory_data[self.inventory_data['id_normalized'] == item_id_normalized]
    return results

def list_by_location(self, location_query):
    """Liệt kê vật tư/hóa chất theo vị trí."""
    if self.inventory_data.empty:
        return pd.DataFrame()

    location_query_normalized = self._remove_accents(location_query)
    # Sử dụng cột đã chuẩn hóa
    results = self.inventory_data[self.inventory_data['location_normalized'].str.contains(location_query_normalized, na=False)]
    return results

def list_by_type(self, item_type):
    """Liệt kê vật tư/hóa chất theo loại."""
    if self.inventory_data.empty:
        return pd.DataFrame()

    item_type_normalized = self._remove_accents(item_type)
    # Sử dụng cột đã chuẩn hóa
    results = self.inventory_data[self.inventory_data['type_normalized'] == item_type_normalized]
    return results

def list_by_status(self, status_query):
    """Liệt kê vật tư/hóa chất theo tình trạng trong cột 'status_text' hoặc 'description'."""
    if self.inventory_data.empty:
        return pd.DataFrame()

    status_query_normalized = self._remove_accents(status_query)

    # Sử dụng cột đã chuẩn hóa
    mask_status_text = self.inventory_data['status_text_normalized'].str.contains(status_query_normalized, na=False)
    mask_description = self.inventory_data['description_normalized'].str.contains(status_query_normalized, na=False)

    results = self.inventory_data[mask_status_text | mask_description]
    return results

def list_by_location_and_status(self, location_query, status_query):
    """Liệt kê vật tư/hóa chất theo vị trí VÀ tình trạng."""
    if self.inventory_data.empty:
        return pd.DataFrame()

    location_query_normalized = self._remove_accents(location_query)
    status_query_normalized = self._remove_accents(status_query)

    # Sử dụng cột đã chuẩn hóa
    normalized_location_col = self.inventory_data['location_normalized']
    normalized_status_text_col = self.inventory_data['status_text_normalized']
    normalized_description_col = self.inventory_data['description_normalized']

    mask_location = normalized_location_col.str.contains(location_query_normalized, na=False)
    mask_status = normalized_status_text_col.str.contains(status_query_normalized, na=False) | \
                  normalized_description_col.str.contains(status_query_normalized, na=False)

    results = self.inventory_data[mask_location & mask_status]
    return results

def list_by_type_and_status(self, item_type, status_query):
    """Liệt kê vật tư/hóa chất theo loại VÀ tình trạng."""
    if self.inventory_data.empty:
        return pd.DataFrame()

    item_type_normalized = self._remove_accents(item_type)
    status_query_normalized = self._remove_accents(status_query)

    # Sử dụng cột đã chuẩn hóa
    normalized_type_col = self.inventory_data['type_normalized']
    normalized_status_text_col = self.inventory_data['status_text_normalized']
    normalized_description_col = self.inventory_data['description_normalized']

    mask_type = normalized_type_col == item_type_normalized
    mask_status = normalized_status_text_col.str.contains(status_query_normalized, na=False) | \
                  normalized_description_col.str.contains(status_query_normalized, na=False)

    results = self.inventory_data[mask_type & mask_status]
    return results

def list_by_type_and_location(self, item_type, location_query):
    """Liệt kê vật tư/hóa chất theo loại VÀ vị trí."""
    if self.inventory_data.empty:
        return pd.DataFrame()

    item_type_normalized = self._remove_accents(item_type)
    location_query_normalized = self._remove_accents(location_query)

    # Sử dụng cột đã chuẩn hóa
    normalized_type_col = self.inventory_data['type_normalized']
    normalized_location_col = self.inventory_data['location_normalized']

    mask_type = normalized_type_col == item_type_normalized
    mask_location = normalized_location_col.str.contains(location_query_normalized, na=False)

    results = self.inventory_data[mask_type & mask_location]
    return results

def search_by_cas(self, cas_number):
    """Tìm kiếm vật tư/hóa chất theo số CAS."""
    if self.inventory_data.empty:
        return pd.DataFrame()

    cas_number_normalized = self._remove_accents(cas_number)
    # Sử dụng cột đã chuẩn hóa
    results = self.inventory_data[self.inventory_data['cas_number_normalized'].str.contains(cas_number_normalized, na=False)]
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
        return False

    try:
        repo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) 

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

        local_log_filepath = os.path.join(repo_path, 'logs', log_filename_from_chatbot_logic)

        if not os.path.exists(local_log_filepath) or os.stat(local_log_filepath).st_size == 0:
            print("Không có dữ liệu nhật ký để tải lên (file log rỗng hoặc không tồn tại).")
            return True

        with open(local_log_filepath, 'r', encoding='utf-8') as f:
            log_content = f.read()
        print("Đã đọc nội dung file log cục bộ.")

        archive_dir = os.path.join(repo_path, 'logs', 'archive')
        if not os.path.exists(archive_dir):
            os.makedirs(archive_dir)
            print(f"DEBUG: Đã tạo thư mục lưu trữ mới: {archive_dir}")

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_filename = f"chat_log_archive_{timestamp_str}.jsonl"
        archive_filepath = os.path.join(archive_dir, archive_filename)

        with open(archive_filepath, 'w', encoding='utf-8') as f:
            f.write(log_content)
        print(f"Đã ghi nội dung vào file lưu trữ: {archive_filepath}")

        repo_relative_archive_filepath = os.path.relpath(archive_filepath, repo_path)
        repo.index.add([repo_relative_archive_filepath])
        commit_message = f"feat(logs): Archive chat log {archive_filename}"
        repo.index.commit(commit_message)
        print(f"Đã commit file {archive_filename} với thông báo: {commit_message}")

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
            return False

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

        with open(local_log_filepath, 'w', encoding='utf-8') as f:
            f.truncate(0)
        print("Đã làm rỗng file log cục bộ.")

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