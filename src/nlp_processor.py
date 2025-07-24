import re
import nltk
import os
import unicodedata

# Tải gói PunktTokenizer cho NLTK (chỉ cần chạy một lần)
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    print("Gói 'punkt' của NLTK không tìm thấy. Đang cố gắng tải xuống...")
    try:
        nltk.download('punkt')
        print("Đã tải xong gói 'punkt'.")
    except Exception as e:
        print(f"Không thể tải gói 'punkt'. Vui lòng chạy 'python -c \"import nltk; nltk.download(\\'punkt\\')\"' trong terminal để tải thủ công. Lỗi: {e}")

class NLPProcessor:
    def __init__(self):
        self.quantity_phrases = ["có bao nhiêu", "số lượng", "bao nhiêu"]
        self.unit_words = ["chai", "lọ", "thùng", "gói", "hộp", "bình", "cái", "m", "kg", "g", "ml", "l", "đơn vị", "viên", "cuộn"]
        self.general_stopwords = ["tìm", "kiếm", "về", "thông tin về", "cho tôi biết về", "hãy tìm", "hỏi về", "của", "là", "?", "vật tư", "hóa chất", "chất"]
        self.status_keywords = ["đã mở", "còn nguyên"]

        self.guidance_keywords = ["hướng dẫn", "giúp tôi tìm kiếm", "cách tìm kiếm", "cách hỏi", "chỉ dẫn", "tôi không hiểu", "bạn có thể hướng dẫn không"]

        # Thêm các từ khóa để nhận diện yêu cầu TẢI LOG LÊN GITHUB
        self.upload_log_github_keywords = ["tải nhật ký lên github", "upload log github", "đẩy log lên github"]
        # Giữ lại các từ khóa tải log cục bộ nếu muốn tách biệt
        self.download_log_keywords = ["tải nhật ký", "xuất log", "lịch sử chat", "tải log"] 

        self.greeting_keywords = ["xin chào", "chào", "hello", "hi", "hey"]


    def _remove_keywords(self, text, keywords_to_remove):
        """
        Hàm trợ giúp để loại bỏ các từ khóa khỏi chuỗi truy vấn.
        Sử dụng r'\b' để đảm bảo chỉ khớp toàn bộ từ.
        """
        cleaned_text = text
        for kw in keywords_to_remove:
            if kw not in self.guidance_keywords and \
               kw not in self.download_log_keywords and \
               kw not in self.upload_log_github_keywords and \
               kw not in self.greeting_keywords and \
               kw not in self.list_search_verbs.replace(r'\s+', ' ').split('|'): # Không loại bỏ các động từ lệnh
                cleaned_text = re.sub(r'\b' + re.escape(kw) + r'\b', '', cleaned_text, flags=re.IGNORECASE).strip()

        cleaned_text = re.sub(r'^\W+|\W+$', '', cleaned_text).strip()
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()

        return cleaned_text

    def process_query(self, query):
        """
        Xử lý câu hỏi của người dùng để trích xuất ý định và các thực thể.
        Trả về một dictionary chứa intent và các tham số.
        """
        query_lower = query.lower().strip()

        # --- Nhận diện Ý định TẢI LOG LÊN GITHUB (Ưu tiên cao nhất) ---
        for kw in self.upload_log_github_keywords:
            if kw in query_lower:
                return {"intent": "upload_log_github"}

        # --- Nhận diện Ý định CHÀO HỎI (Ưu tiên cao thứ hai) ---
        for kw in self.greeting_keywords:
            if kw in query_lower:
                return {"intent": "greeting"}

        # --- Nhận diện Ý định TẢI LOG CỤC BỘ (Nếu có) ---
        # (Bạn có thể bỏ qua nếu không cần chức năng tải cục bộ qua nút nữa)
        for kw in self.download_log_keywords:
            if kw in query_lower:
                return {"intent": "download_logs"} # Giữ lại nếu muốn chức năng này

        # --- Nhận diện Ý định HƯỚNG DẪN ---
        for kw in self.guidance_keywords:
            if kw in query_lower:
                return {"intent": "request_guidance"}

        # --- Các ý định cụ thể khác ---

        # (Các regex nhận diện ý định khác như list_by_type_location, search_by_id, v.v. giữ nguyên)
        # ... (Phần này sẽ tương tự như code hiện tại của bạn)

        # --- Ý định chung (Fallback cuối cùng) ---
        all_keywords_to_remove = self.general_stopwords + self.quantity_phrases + self.unit_words + \
                                 self.status_keywords + self.guidance_keywords + \
                                 self.download_log_keywords + self.upload_log_github_keywords + \
                                 self.greeting_keywords + \
                                 self.list_search_verbs.replace(r'\s+', ' ').split('|')

        cleaned_query_for_general_search = self._remove_keywords(query_lower, all_keywords_to_remove)

        if not cleaned_query_for_general_search:
            return {"intent": "search_item", "query": ""} 

        return {"intent": "search_item", "query": cleaned_query_for_general_search}

    def _extract_item_name(self, query_lower, keywords_to_remove):
        # Hàm này nên được tích hợp hoàn toàn vào _remove_keywords hoặc xóa nếu không còn dùng.
        # Để đơn giản, giữ nguyên như hiện tại nếu nó không gây lỗi.
        item_name_candidate = query_lower
        for kw in keywords_to_remove:
            item_name_candidate = item_name_candidate.replace(kw, "").strip()

        item_name_candidate = re.sub(r'(của|là|\?|vật tư|hóa chất)$', '', item_name_candidate).strip()
        item_name_candidate = re.sub(r'\s+', ' ', item_name_candidate).strip()
        return item_name_candidate