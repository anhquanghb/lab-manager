import unicodedata
import pandas as pd # Cần import pandas để xử lý pd.isna

def remove_accents_and_normalize(input_str):
    """
    Loại bỏ dấu tiếng Việt, chuyển chữ 'đ'/'Đ' thành 'd'/'D', và chuẩn hóa chuỗi về chữ thường.
    Hàm này được dùng chung trên toàn bộ dự án.
    """
    if pd.isna(input_str):
        return ''
    if not isinstance(input_str, str):
        return str(input_str)
    
    input_str = input_str.replace('đ', 'd').replace('Đ', 'D')
    
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    only_ascii = nfkd_form.encode('ascii', 'ignore').decode('utf-8')
    return only_ascii.lower()