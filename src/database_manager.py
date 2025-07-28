import pandas as pd
import json
import os
import unicodedata
import re # Import re for parsing CAS from description if needed, though now less
from pathlib import Path # Sử dụng pathlib
import git
from datetime import datetime
import streamlit as st

class DatabaseManager:
    def __init__(self, data_path='data/inventory.json'):
        # Sử dụng pathlib để xây dựng đường dẫn đến file dữ liệu
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

            # --- BẮT ĐẦU CHUẨN HÓA DỮ LIỆU SAU KHI TẢI ---
            # Hàm trợ giúp để loại bỏ dấu tiếng Việt và chuẩn hóa chuỗi.
            # Đã đưa vào đây để đảm bảo logic chuẩn hóa tập trung.
            def _remove_accents_and_normalize(input_str):
                if pd.isna(input_str): # Xử lý NaN
                    return ''
                input_str = str(input_str)
                nfkd_form = unicodedata.normalize('NFKD', input_str)
                only_ascii = nfkd_form.encode('ascii', 'ignore').decode('utf-8')
                return only_ascii.lower() # Luôn chuyển về chữ thường

            # Tạo các cột đã được chuẩn hóa để tăng tốc tìm kiếm
            # Các cột này được tạo 1 lần khi load dữ liệu, thay vì mỗi lần tìm kiếm
            df['id_normalized'] = df['id'].apply(_remove_accents_and_normalize)
            df['name_normalized'] = df['name'].apply(_remove_accents_and_normalize)
            df['type_normalized'] = df['type'].apply(_remove_accents_and_normalize)
            df['location_normalized'] = df['location'].apply(_remove_accents_and_normalize)
            
            # Các cột mới được tách ra từ description trong convert_data.py
            df['chemical_formula_normalized'] = df['chemical_formula'].apply(_remove_accents_and_normalize)
            df['cas_number_normalized'] = df['cas_number'].apply(_remove_accents_and_normalize)
            df['state_or_concentration_normalized'] = df['state_or_concentration'].apply(_remove_accents_and_normalize)
            df['status_normalized'] = df['status'].apply(_remove_accents_and_normalize)
            df['purpose_normalized'] = df['purpose'].apply(_remove_accents_and_normalize)
            df['tracking_normalized'] = df['tracking'].apply(_remove_accents_and_normalize)
            df['iupac_name_normalized'] = df['iupac_name'].apply(_remove_accents_and_normalize)
            df['vietnamese_name_normalized'] = df['vietnamese_name'].apply(_remove_accents_and_normalize)
            
            # Cột description gốc vẫn giữ để tìm kiếm từ khóa chung (nếu người dùng gõ cụm từ dài)
            df['description_normalized'] = df['description'].apply(_remove_accents_and_normalize)


            # --- KẾT THÚC CHUẨN HÓA DỮ LIỆU ---

            return df
        except json.JSONDecodeError:
            print(f"Lỗi: File {self.data_path} không phải là JSON hợp lệ.")
            return pd.DataFrame()
        except Exception as e:
            print(f"Lỗi khi tải dữ liệu: {e}")
            return pd.DataFrame()

    # Hàm _remove_accents đã được tích hợp trực tiếp vào _load_data khi tạo các cột _normalized
    # và sẽ không cần gọi riêng nữa.
    # def _remove_accents(self, input_str):
    #     """Hàm trợ giúp để loại bỏ dấu tiếng Việt và chuẩn hóa chuỗi."""
    #     if not isinstance(input_str, str):
    #         return str(input_str)
    #     nfkd_form = unicodedata.normalize('NFKD', input_str)
    #     only_ascii = nfkd_form.encode('ascii', 'ignore').decode('utf-8')
    #     return only_ascii # Giữ nguyên như cũ nếu muốn chỉ loại bỏ dấu không chuyển lower

    def search_item(self, query):
        """
        Tìm kiếm vật tư/hóa chất theo bất kỳ thông tin liên quan nào
        bao gồm: id, name, type, location, description, chemical_formula, cas_number, iupac_name, vietnamese_name.
        Sử dụng các cột đã chuẩn hóa để tìm kiếm.
        """
        if self.inventory_data.empty:
            return pd.DataFrame()

        # Query cũng cần được chuẩn hóa tương tự dữ liệu
        query_normalized = unicodedata.normalize('NFKD', query).encode('ascii', 'ignore').decode('utf-8').lower()

        # Định nghĩa các cột sẽ tìm kiếm trên phiên bản đã chuẩn hóa
        search_cols = [
            'id_normalized', 'name_normalized', 'type_normalized', 
            'location_normalized', 'description_normalized', 
            'chemical_formula_normalized', 'cas_number_normalized',
            'iupac_name_normalized', 'vietnamese_name_normalized'
        ]

        # Áp dụng hàm str.contains trên các cột đã chuẩn hóa
        # .fillna('') để xử lý NaN một cách an toàn trước khi gọi .str.contains
        mask = self.inventory_data[search_cols].apply(
            lambda col: col.fillna('').str.contains(query_normalized, na=False)
        ).any(axis=1)

        results = self.inventory_data[mask]
        return results

    def get_quantity(self, item_name):
        """Lấy số lượng của một vật tư/hóa chất cụ thể dựa trên tên đã chuẩn hóa."""
        if self.inventory_data.empty:
            return None, None
        
        item_name_normalized = unicodedata.normalize('NFKD', item_name).encode('ascii', 'ignore').decode('utf-8').lower()

        # Tìm kiếm trên cả name_normalized, iupac_name_normalized, vietnamese_name_normalized để khớp tên tốt hơn
        found_item_mask = (
            (self.inventory_data['name_normalized'] == item_name_normalized) |
            (self.inventory_data['iupac_name_normalized'] == item_name_normalized) |
            (self.inventory_data['vietnamese_name_normalized'] == item_name_normalized)
        )
        found_item = self.inventory_data[found_item_mask]

        if not found_item.empty:
            # Trả về tổng số lượng nếu có nhiều mục khớp tên (ví dụ: A001A, A001B)
            total_quantity = found_item['quantity'].sum()
            # Đơn vị thường là nhất quán, lấy đơn vị của mục đầu tiên
            unit = found_item.iloc[0]['unit']
            return total_quantity, unit
        return None, None

    def get_location(self, item_name):
        """Lấy vị trí của một vật tư/hóa chất cụ thể dựa trên tên đã chuẩn hóa."""
        if self.inventory_data.empty:
            return None

        item_name_normalized = unicodedata.normalize('NFKD', item_name).encode('ascii', 'ignore').decode('utf-8').lower()
        
        found_item_mask = (
            (self.inventory_data['name_normalized'] == item_name_normalized) |
            (self.inventory_data['iupac_name_normalized'] == item_name_normalized) |
            (self.inventory_data['vietnamese_name_normalized'] == item_name_normalized)
        )
        found_item = self.inventory_data[found_item_mask]

        if not found_item.empty:
            # Nếu có nhiều mục trùng tên nhưng khác ID/vị trí, trả về tất cả các vị trí duy nhất
            unique_locations = found_item['location'].unique()
            return ", ".join(unique_locations)
        return None

    # --- CÁC HÀM TÌM KIẾM KHÁC (ĐÃ CẬP NHẬT ĐỂ SỬ DỤNG CÁC CỘT CHUẨN HÓA) ---

    def get_by_id(self, item_id):
        """Tìm kiếm vật tư/hóa chất theo ID chính xác."""
        if self.inventory_data.empty:
            return pd.DataFrame()

        item_id_normalized = unicodedata.normalize('NFKD', item_id).encode('ascii', 'ignore').decode('utf-8').lower()
        results = self.inventory_data[self.inventory_data['id_normalized'] == item_id_normalized]
        return results

    def list_by_location(self, location_query):
        """Liệt kê vật tư/hóa chất theo vị trí."""
        if self.inventory_data.empty:
            return pd.DataFrame()

        location_query_normalized = unicodedata.normalize('NFKD', location_query).encode('ascii', 'ignore').decode('utf-8').lower()
        results = self.inventory_data[self.inventory_data['location_normalized'].str.contains(location_query_normalized, na=False)]
        return results

    def list_by_type(self, item_type):
        """Liệt kê vật tư/hóa chất theo loại."""
        if self.inventory_data.empty:
            return pd.DataFrame()

        item_type_normalized = unicodedata.normalize('NFKD', item_type).encode('ascii', 'ignore').decode('utf-8').lower()
        results = self.inventory_data[self.inventory_data['type_normalized'] == item_type_normalized]
        return results

    def list_by_status(self, status_query):
        """Liệt kê vật tư/hóa chất theo tình trạng đã chuẩn hóa."""
        if self.inventory_data.empty:
            return pd.DataFrame()

        status_query_normalized = unicodedata.normalize('NFKD', status_query).encode('ascii', 'ignore').decode('utf-8').lower()
        results = self.inventory_data[self.inventory_data['status_normalized'] == status_query_normalized]
        return results

    def list_by_location_and_status(self, location_query, status_query):
        """Liệt kê vật tư/hóa chất theo vị trí VÀ tình trạng."""
        if self.inventory_data.empty:
            return pd.DataFrame()

        location_query_normalized = unicodedata.normalize('NFKD', location_query).encode('ascii', 'ignore').decode('utf-8').lower()
        status_query_normalized = unicodedata.normalize('NFKD', status_query).encode('ascii', 'ignore').decode('utf-8').lower()

        mask_location = self.inventory_data['location_normalized'].str.contains(location_query_normalized, na=False)
        mask_status = self.inventory_data['status_normalized'] == status_query_normalized

        results = self.inventory_data[mask_location & mask_status]
        return results

    def list_by_type_and_status(self, item_type, status_query):
        """Liệt kê vật tư/hóa chất theo loại VÀ tình trạng."""
        if self.inventory_data.empty:
            return pd.DataFrame()

        item_type_normalized = unicodedata.normalize('NFKD', item_type).encode('ascii', 'ignore').decode('utf-8').lower()
        status_query_normalized = unicodedata.normalize('NFKD', status_query).encode('ascii', 'ignore').decode('utf-8').lower()

        mask_type = self.inventory_data['type_normalized'] == item_type_normalized
        mask_status = self.inventory_data['status_normalized'] == status_query_normalized

        results = self.inventory_data[mask_type & mask_status]
        return results

    def list_by_type_and_location(self, item_type, location_query):
        """Liệt kê vật tư/hóa chất theo loại VÀ vị trí."""
        if self.inventory_data.empty:
            return pd.DataFrame()

        item_type_normalized = unicodedata.normalize('NFKD', item_type).encode('ascii', 'ignore').decode('utf-8').lower()
        location_query_normalized = unicodedata.normalize('NFKD', location_query).encode('ascii', 'ignore').decode('utf-8').lower()

        mask_type = self.inventory_data['type_normalized'] == item_type_normalized
        mask_location = self.inventory_data['location_normalized'].str.contains(location_query_normalized, na=False)

        results = self.inventory_data[mask_type & mask_location]
        return results
 
    def search_by_cas(self, cas_number):
        """Tìm kiếm vật tư/hóa chất theo số CAS chính xác."""
        if self.inventory_data.empty:
            return pd.DataFrame()

        cas_number_normalized = unicodedata.normalize('NFKD', cas_number).encode('ascii', 'ignore').decode('utf-8').lower()
        results = self.inventory_data[self.inventory_data['cas_number_normalized'] == cas_number_normalized]
        return results

    def upload_logs_to_github_on_startup(self, log_filepath):
        """
        Hàm này được gọi khi ứng dụng khởi động.
        Đọc file log hiện tại, tải lên GitHub và làm rỗng file log cục bộ.
        Sử dụng Personal Access Token (PAT) từ Streamlit secrets.
        """
        github_token = st.secrets.get("GITHUB_TOKEN")

        if not github_token:
            print("Lỗi: Không tìm thấy GitHub Personal Access Token trong st.secrets. Không thể tải log lên GitHub.")
            return False # Trả về False nếu không có token

        try:
            # Lấy đường dẫn thư mục gốc của repo (ví dụ: /mount/src/lab-manager)
            repo_path = Path(__file__).parent.parent # Sử dụng pathlib

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

            # Đọc nội dung log hiện tại
            # Sử dụng pathlib để kiểm tra file tồn tại
            if not Path(log_filepath).exists() or Path(log_filepath).stat().st_size == 0:
                print("Không có dữ liệu nhật ký để tải lên (file log rỗng hoặc không tồn tại).")
                return True # Không có gì để tải lên, coi như thành công

            with open(log_filepath, 'r', encoding='utf-8') as f:
                log_content = f.read()
            print("Đã đọc nội dung file log cục bộ.")

            # Tạo thư mục archive nếu chưa có
            archive_dir = repo_path / 'logs' / 'archive' # Sử dụng pathlib
            archive_dir.mkdir(parents=True, exist_ok=True) # Tạo thư mục nếu chưa có
            print(f"DEBUG: Đã tạo thư mục lưu trữ mới: {archive_dir}")

            # Tạo tên file log lưu trữ với timestamp
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_filename = f"chat_log_archive_{timestamp_str}.jsonl"
            archive_filepath = archive_dir / archive_filename # Sử dụng pathlib

            # Ghi nội dung vào file log lưu trữ
            with open(archive_filepath, 'w', encoding='utf-8') as f:
                f.write(log_content)
            print(f"Đã ghi nội dung vào file lưu trữ: {archive_filepath}")

            # Thêm file vào Git và commit
            repo_relative_archive_filepath = archive_filepath.relative_to(repo_path) # Sử dụng pathlib
            repo.index.add([str(repo_relative_archive_filepath)]) # add cần string
            commit_message = f"feat(logs): Archive chat log {archive_filename}"
            repo.index.commit(commit_message)
            print(f"Đã commit file {archive_filename} với thông báo: {commit_message}")

            # Lấy URL remote và chuẩn bị cho xác thực PAT
            remote_url = repo.remotes.origin.url
            print(f"URL remote gốc: {remote_url}")

            repo_url_with_auth = ""
            if remote_url.startswith("git@github.com:"):
                repo_path_no_git = remote_url.replace("git@github.com:", "").replace(".git", "")
                repo_url_with_auth = f"https://oauth2:{github_token}@github.com/{repo_path_no_git}"
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
            with open(log_filepath, 'w', encoding='utf-8') as f:
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