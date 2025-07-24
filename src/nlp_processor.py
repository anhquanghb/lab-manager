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
        self.download_log_keywords = ["tải nhật ký", "xuất log", "lịch sử chat", "tải log"]
        self.greeting_keywords = ["xin chào", "chào", "hello", "hi", "hey"]

        # Định nghĩa các động từ chung cho lệnh liệt kê/tìm kiếm
        self.list_search_verbs = r'(liệt\s+kê|tìm|có|thống\s+kê)' # Đã thêm 'thống\s+kê'


    def _remove_keywords(self, text, keywords_to_remove):
        """
        Hàm trợ giúp để loại bỏ các từ khóa khỏi chuỗi truy vấn.
        Sử dụng r'\b' để đảm bảo chỉ khớp toàn bộ từ.
        """
        cleaned_text = text
        for kw in keywords_to_remove:
            if kw not in self.guidance_keywords and \
               kw not in self.download_log_keywords and \
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

        # --- Nhận diện Ý định CHÀO HỎI (Ưu tiên cao nhất) ---
        for kw in self.greeting_keywords:
            if kw in query_lower:
                return {"intent": "greeting"}

        # --- Nhận diện Ý định TẢI LOG (Ưu tiên cao thứ hai) ---
        for kw in self.download_log_keywords:
            if kw in query_lower:
                return {"intent": "download_logs"}

        # --- Nhận diện Ý định HƯỚNG DẪN (Ưu tiên cao thứ ba) ---
        for kw in self.guidance_keywords:
            if kw in query_lower:
                return {"intent": "request_guidance"}

        # --- Các ý định cụ thể khác (sau khi kiểm tra hướng dẫn và tải log) ---

        # Ý định: Get Quantity AND Status
        match_quantity_status = re.search(r'(?:' + '|'.join(self.quantity_phrases) + r')\s+(?:' + '|'.join(self.unit_words) + r')?\s*([a-zA-Z0-9\s.-]+?)\s*(' + '|'.join(self.status_keywords) + r')', query_lower)
        if match_quantity_status:
            raw_item_name = match_quantity_status.group(2).strip()
            status_found = match_quantity_status.group(3).strip()
            item_name = self._remove_keywords(raw_item_name, self.unit_words)
            if item_name and "hóa chất" not in item_name and "vật tư" not in item_name:
                return {"intent": "get_quantity_status", "item_name": item_name, "status": status_found}

        # Ý định: List by Type AND Location
        match_type_location = re.search(self.list_search_verbs + r'\s+(hóa\s+chất|vật\s+tư|chất)\s+(trong|từ|ở)\s+(tủ|kệ)\s+([a-zA-Z0-9\s.-]+)', query_lower) # Dùng self.list_search_verbs
        if match_type_location:
            item_type_raw = match_type_location.group(2)
            location = match_type_location.group(5).strip().upper()

            item_type = ""
            if "hóa chất" in item_type_raw or "chất" in item_type_raw:
                item_type = "Hóa chất"
            elif "vật tư" in item_type_raw:
                item_type = "Vật tư"

            return {"intent": "list_by_type_location", "type": item_type, "location": location}

        # Ý định: List by Location AND Status
        match_loc_status = re.search(self.list_search_verbs + r'\s+(.+)\s+(trong|từ)\s+(tủ|kệ)\s+([a-zA-Z0-9\s.-]+)', query_lower) # Dùng self.list_search_verbs
        if match_loc_status:
            status_phrase_full = match_loc_status.group(2).strip()
            location = match_loc_status.group(5).strip().upper()

            status = None
            for kw in self.status_keywords:
                if kw in status_phrase_full:
                    status = kw.capitalize()
                    break
            return {"intent": "list_by_location_status", "location": location, "status": status}

        # Ý định: List by Type AND Status
        match_type_status = re.search(self.list_search_verbs + r'\s+(hóa\s+chất|vật\s+tư|chất)(?:\s+(.+))?', query_lower) # Dùng self.list_search_verbs
        if match_type_status:
            item_type_raw = match_type_status.group(2)
            status_phrase = match_type_status.group(3) if match_type_status.group(3) else ""

            item_type = ""
            if "hóa chất" in item_type_raw or "chất" in item_type_raw:
                item_type = "Hóa chất"
            elif "vật tư" in item_type_raw:
                item_type = "Vật tư"

            status = None
            for kw in self.status_keywords:
                if kw in status_phrase:
                    status = kw.capitalize()
                    break

            if status:
                return {"intent": "list_by_type_status", "type": item_type, "status": status}
            elif item_type:
                return {"intent": "list_by_type", "type": item_type}


        # --- CÁC Ý ĐỊNH ĐƠN LẺ ---

        # Ý định: Get Quantity
        match_get_quantity = re.search(r'(?:' + '|'.join(self.quantity_phrases) + r')\s+(.+)', query_lower)
        if match_get_quantity:
            raw_item_name = match_get_quantity.group(1).strip()
            item_name = self._remove_keywords(raw_item_name, self.unit_words)
            if item_name and "hóa chất" not in item_name and "vật tư" not in item_name:
                return {"intent": "get_quantity", "item_name": item_name}

        # Ý định: Search by ID
        match_id = re.search(r'(mã|code)\s+([a-zA-Z0-9-]+)', query_lower)
        if match_id:
            return {"intent": "search_by_id", "id": match_id.group(2).upper()}

        # Ý định: Search by CAS
        match_cas = re.search(r'(cas|số cas)\s+([0-9-]+)', query_lower)
        if match_cas:
            return {"intent": "search_by_cas", "cas": match_cas.group(2)}

        # Ý định: List by Location (Đơn thuần)
        match_location_simple = re.search(self.list_search_verbs + r'\s*(trong|từ|ở)?\s*(tủ|kệ)\s+([a-zA-Z0-9\s.-]+)', query_lower) # Dùng self.list_search_verbs
        if match_location_simple:
            return {"intent": "list_by_location", "location": match_location_simple.group(4).strip().upper()}


        # --- Ý định chung (Fallback cuối cùng) ---
        all_keywords_to_remove = self.general_stopwords + self.quantity_phrases + self.unit_words + \
                                 self.status_keywords + self.guidance_keywords + \
                                 self.download_log_keywords + self.greeting_keywords + \
                                 self.list_search_verbs.replace(r'\s+', ' ').split('|') # Thêm list_search_verbs

        cleaned_query_for_general_search = self._remove_keywords(query_lower, all_keywords_to_remove)

        if not cleaned_query_for_general_search:
            return {"intent": "search_item", "query": ""} 

        return {"intent": "search_item", "query": cleaned_query_for_general_search}

    def _extract_item_name(self, query_lower, keywords_to_remove):
        """
        Hàm trợ giúp này được dùng trong các phiên bản trước cho tìm kiếm chung.
        Hiện tại, các regex ở trên đã cụ thể hơn, nhưng hàm này vẫn có thể được giữ lại
        cho các trường hợp tìm kiếm chung mà không có từ khóa rõ ràng.
        """
        # Hàm này sẽ được thay thế bởi _remove_keywords. Tạm giữ để tránh lỗi nếu còn được gọi từ đâu đó.
        item_name_candidate = query_lower
        for kw in keywords_to_remove:
            item_name_candidate = item_name_candidate.replace(kw, "").strip()

        item_name_candidate = re.sub(r'(của|là|\?|vật tư|hóa chất)$', '', item_name_candidate).strip()
        item_name_candidate = re.sub(r'\s+', ' ', item_name_candidate).strip()
        return item_name_candidate