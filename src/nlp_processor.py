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
        # Định nghĩa các từ khóa dưới dạng danh sách chuỗi, sau đó chuyển thành regex pattern
        self.quantity_phrases_list = ["có bao nhiêu", "số lượng", "bao nhiêu"]
        self.unit_words_list = ["chai", "lọ", "thùng", "gói", "hộp", "bình", "cái", "m", "kg", "g", "ml", "l", "đơn vị", "viên", "cuộn"]
        self.general_stopwords_list = ["tìm", "kiếm", "về", "thông tin về", "cho tôi biết về", "hãy tìm", "hỏi về", "của", "là", "?", "vật tư", "hóa chất", "chất"]
        self.status_keywords_list = ["đã mở", "còn nguyên"]
        self.guidance_keywords_list = ["hướng dẫn", "giúp tôi tìm kiếm", "cách tìm kiếm", "cách hỏi", "chỉ dẫn", "tôi không hiểu", "bạn có thể hướng dẫn không"]
        self.download_log_keywords_list = ["tải nhật ký", "xuất log", "lịch sử chat", "tải log"]
        self.greeting_keywords_list = ["xin chào", "chào", "hello", "hi", "hey"]
        self.problem_keywords_list = ["không thấy", "đã hết", "không còn", "hư hỏng", "hỏng", "bị hỏng", "thiếu"]
        self.location_phrases_list = ["ở đâu", "vị trí của"] # Từ khóa cho vị trí

        # Tạo các regex pattern từ danh sách từ khóa
        # Sử dụng re.escape() cho từng từ khóa để an toàn, sau đó join bằng '|' và gói trong non-capturing group (?:...)
        self.quantity_phrases_regex = r"(?:" + "|".join(map(re.escape, self.quantity_phrases_list)) + r")"
        self.unit_words_regex = r"(?:" + "|".join(map(re.escape, self.unit_words_list)) + r")"
        self.status_keywords_regex = r"(?:" + "|".join(map(re.escape, self.status_keywords_list)) + r")"
        self.problem_keywords_regex = r"(?:" + "|".join(map(re.escape, self.problem_keywords_list)) + r")"
        self.location_phrases_regex = r"(?:" + "|".join(map(re.escape, self.location_phrases_list)) + r")"

        # Động từ chung cho lệnh liệt kê/tìm kiếm
        self.list_search_verbs_regex = r'(?:liệt\s+kê|tìm|có|thống\s+kê)'


    def _remove_keywords(self, text, keywords_to_remove_list):
        """
        Hàm trợ giúp để loại bỏ các từ khóa khỏi chuỗi truy vấn.
        Keywords_to_remove_list phải là danh sách các chuỗi, không phải regex.
        """
        cleaned_text = text
        for kw in keywords_to_remove_list:
            # Thay thế từ khóa bằng một khoảng trắng để giữ ranh giới từ và làm sạch sau
            cleaned_text = re.sub(r'\b' + re.escape(kw) + r'\b', ' ', cleaned_text, flags=re.IGNORECASE).strip()

        # Làm sạch khoảng trắng thừa
        cleaned_text = re.sub(r'^\W+|\W+$', '', cleaned_text).strip() # Loại bỏ ký tự không phải chữ/số/khoảng trắng ở đầu cuối
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip() # Loại bỏ nhiều khoảng trắng thành một

        return cleaned_text

    def process_query(self, query):
        """
        Xử lý câu hỏi của người dùng để trích xuất ý định và các thực thể.
        Trả về một dictionary chứa intent và các tham số.
        """
        query_lower = query.lower().strip()

        # --- Nhận diện Ý định CHÀO HỎI (Ưu tiên cao nhất) ---
        for kw in self.greeting_keywords_list:
            if kw in query_lower:
                return {"intent": "greeting"}

        # --- Nhận diện Ý định TẢI LOG CỤC BỘ ---
        for kw in self.download_log_keywords_list:
            if kw in query_lower:
                return {"intent": "download_logs"} 

        # --- Nhận diện Ý định HƯỚNG DẪN ---
        for kw in self.guidance_keywords_list:
            if kw in query_lower:
                return {"intent": "request_guidance"}

        # --- Nhận diện Ý định BÁO CÁO TÌNH TRẠNG/VẤN ĐỀ ---
        # Mẫu: [tên/id/vị trí] [từ khóa vấn đề]
        # Ví dụ: "h2so4 đã hết", "tủ sấy bị hỏng", "A001A không còn"
        problem_report_regex = r'(.+?)\s+' + self.problem_keywords_regex
        match_problem = re.search(problem_report_regex, query_lower)
        if match_problem:
            reported_item_or_location = match_problem.group(1).strip()
            reported_status_phrase = match_problem.group(0)[len(reported_item_or_location):].strip()

            is_id = re.fullmatch(r'[a-zA-Z0-9-]+', reported_item_or_location)
            is_location_phrase = re.fullmatch(r'(tủ|kệ)\s+([a-zA-Z0-9\s.-]+)', reported_item_or_location)

            if is_id:
                return {"intent": "report_status_or_problem", "reported_id": reported_item_or_location.upper(), "problem_description": reported_status_phrase}
            elif is_location_phrase:
                return {"intent": "report_status_or_problem", "reported_location": reported_item_or_location, "problem_description": reported_status_phrase}
            else:
                return {"intent": "report_status_or_problem", "reported_item_name": reported_item_or_location, "problem_description": reported_status_phrase}

        # --- Các ý định tìm kiếm vị trí ---
        # Mẫu 1: [tên/công thức] ở đâu / vị trí của [tên/công thức] (ví dụ: "h2so4 ở đâu?")
        match_get_location_direct = re.search(r'([a-zA-Z0-9\s.-]+?)\s+' + self.location_phrases_regex, query_lower)
        if match_get_location_direct:
            item_name = match_get_location_direct.group(1).strip()
            # Loại bỏ các từ khóa chung nếu chúng vô tình bị bắt vào tên item
            item_name = self._remove_keywords(item_name, self.general_stopwords_list + self.quantity_phrases_list + self.unit_words_list)
            if item_name:
                return {"intent": "get_location", "item_name": item_name}

        # Mẫu 2: tìm/liệt kê/có vị trí [tên/công thức] (ví dụ: "tìm vị trí h2so4")
        match_get_location_verb_phrase = re.search(self.list_search_verbs_regex + r'\s+' + self.location_phrases_regex + r'\s*(của)?\s*([a-zA-Z0-9\s.-]+)', query_lower)
        if match_get_location_verb_phrase:
            item_name = match_get_location_verb_phrase.group(3).strip() # group(3) nếu 'của' là optional group
            item_name = self._remove_keywords(item_name, self.general_stopwords_list + self.quantity_phrases_list + self.unit_words_list)
            if item_name:
                return {"intent": "get_location", "item_name": item_name}

        # --- Các ý định tìm kiếm khác (sau vị trí và báo cáo) ---

        # Ý định: Get Quantity AND Status
        match_quantity_status = re.search(self.quantity_phrases_regex + r'\s+(?:' + self.unit_words_regex + r')?\s*([a-zA-Z0-9\s.-]+?)\s+' + self.status_keywords_regex, query_lower)
        if match_quantity_status:
            raw_item_name = match_quantity_status.group(2).strip()
            status_found = match_quantity_status.group(3).strip() # Vị trí group có thể thay đổi tùy regex
            item_name = self._remove_keywords(raw_item_name, self.unit_words_list)
            if item_name and "hóa chất" not in item_name and "vật tư" not in item_name:
                return {"intent": "get_quantity_status", "item_name": item_name, "status": status_found}

        # Ý định: List by Type AND Location
        match_type_location = re.search(self.list_search_verbs_regex + r'\s+(hóa\s+chất|vật\s+tư|chất)\s+(trong|từ|ở)\s+(tủ|kệ)\s+([a-zA-Z0-9\s.-]+)', query_lower)
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
        match_loc_status = re.search(self.list_search_verbs_regex + r'\s+(.+)\s+(trong|từ)\s+(tủ|kệ)\s+([a-zA-Z0-9\s.-]+)', query_lower)
        if match_loc_status:
            status_phrase_full = match_loc_status.group(2).strip()
            location = match_loc_status.group(5).strip().upper()

            status = None
            for kw in self.status_keywords_list:
                if kw in status_phrase_full:
                    status = kw.capitalize()
                    break
            return {"intent": "list_by_location_status", "location": location, "status": status}

        # Ý định: List by Type AND Status
        match_type_status = re.search(self.list_search_verbs_regex + r'\s+(hóa\s+chất|vật\s+tư|chất)(?:\s+(.+))?', query_lower)
        if match_type_status:
            item_type_raw = match_type_status.group(2)
            status_phrase = match_type_status.group(3) if match_type_status.group(3) else ""

            item_type = ""
            if "hóa chất" in item_type_raw or "chất" in item_type_raw:
                item_type = "Hóa chất"
            elif "vật tư" in item_type_raw:
                item_type = "Vật tư"

            status = None
            for kw in self.status_keywords_list:
                if kw in status_phrase:
                    status = kw.capitalize()
                    break

            if status:
                return {"intent": "list_by_type_status", "type": item_type, "status": status}
            elif item_type:
                return {"intent": "list_by_type", "type": item_type}


        # --- CÁC Ý ĐỊNH ĐƠN LẺ ---

        # Ý định: Get Quantity
        match_get_quantity = re.search(self.quantity_phrases_regex + r'\s+([a-zA-Z0-9\s.-]+)', query_lower)
        if match_get_quantity:
            raw_item_name = match_get_quantity.group(1).strip()
            item_name = self._remove_keywords(raw_item_name, self.unit_words_list)
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
        match_location_simple = re.search(self.list_search_verbs_regex + r'\s*(trong|từ|ở)?\s*(tủ|kệ)\s+([a-zA-Z0-9\s.-]+)', query_lower)
        if match_location_simple:
            return {"intent": "list_by_location", "location": match_location_simple.group(4).strip().upper()}


        # --- Ý định chung (Fallback cuối cùng) ---
        commands_to_remove_in_general_search = list(set(
            self.general_stopwords_list + self.quantity_phrases_list + self.unit_words_list +
            self.status_keywords_list + self.guidance_keywords_list + self.download_log_keywords_list +
            self.greeting_keywords_list + self.problem_keywords_list + self.location_phrases_list +
            self.list_search_verbs_regex.replace(r'\s+', ' ').replace(r'(?:', '').replace(r')', '').split('|')
        ))

        cleaned_query_for_general_search = query_lower
        for kw in commands_to_remove_in_general_search:
            cleaned_query_for_general_search = re.sub(r'\b' + re.escape(kw) + r'\b', ' ', cleaned_query_for_general_search, flags=re.IGNORECASE).strip()

        cleaned_query_for_general_search = re.sub(r'\s+', ' ', cleaned_query_for_general_search).strip()

        if not cleaned_query_for_general_search:
            return {"intent": "search_item", "query": ""} 

        return {"intent": "search_item", "query": cleaned_query_for_general_search}

    def _extract_item_name(self, query_lower, keywords_to_remove):
        # Hàm này sẽ được tích hợp hoàn toàn vào _remove_keywords hoặc xóa nếu không còn dùng.
        item_name_candidate = query_lower
        for kw in keywords_to_remove:
            item_name_candidate = item_name_candidate.replace(kw, "").strip()

        item_name_candidate = re.sub(r'(của|là|\?|vật tư|hóa chất)$', '', item_name_candidate).strip()
        item_name_candidate = re.sub(r'\s+', ' ', item_name_candidate).strip()
        return item_name_candidate