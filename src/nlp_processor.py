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
        self.status_keywords_list = ["đã mở", "còn nguyên", "đã sử dụng", "hết hạn", "còn hạn", "còn", "hết", "đang sử dụng", "sử dụng", "còn lại", "còn bao nhiêu", "tình trạng", "trạng thái"]
        self.guidance_keywords_list = ["hướng dẫn", "giúp tôi tìm kiếm", "cách tìm kiếm", "cách hỏi", "chỉ dẫn", "tôi không hiểu", "bạn có thể hướng dẫn không"]
        self.download_log_keywords_list = ["tải nhật ký", "xuất log", "lịch sử chat", "tải log"]
        self.greeting_keywords_list = ["xin chào", "chào", "hello", "hi", "hey"]
        self.problem_keywords_list = ["không thấy", "đã hết", "không còn", "hư hỏng", "hỏng", "bị hỏng", "thiếu", "bị mất", "bị thất lạc", "bị lỗi", "lỗi", "vấn đề", "sự cố"]
        self.location_phrases_list = ["ở đâu", "vị trí của"] # Từ khóa cho vị trí

        # Hàm trợ giúp để chuyển danh sách từ/cụm từ sang regex pattern an toàn
        def _list_to_regex_pattern(word_list):
            pattern_parts = []
            for phrase in word_list:
                regex_phrase = r'\s+'.join(re.escape(word) for word in phrase.split())
                pattern_parts.append(regex_phrase)
            return r"(?:" + "|".join(pattern_parts) + r")"

        # Tạo các regex pattern từ danh sách từ khóa
        self.quantity_phrases_regex = _list_to_regex_pattern(self.quantity_phrases_list)
        self.unit_words_regex = _list_to_regex_pattern(self.unit_words_list)
        self.status_keywords_regex = _list_to_regex_pattern(self.status_keywords_list)
        self.problem_keywords_regex = _list_to_regex_pattern(self.problem_keywords_list)
        self.location_phrases_regex = _list_to_regex_pattern(self.location_phrases_list)

        # Động từ chung cho lệnh liệt kê/tìm kiếm
        self.list_search_verbs_regex = r'(?:liệt\s+kê|tìm|có|thống\s+kê)'


    def _remove_keywords(self, text, keywords_to_remove_list):
        """
        Hàm trợ giúp để loại bỏ các từ khóa khỏi chuỗi truy vấn.
        Keywords_to_remove_list phải là danh sách các chuỗi, không phải regex.
        """
        cleaned_text = text
        for kw in keywords_to_remove_list:
            cleaned_text = re.sub(r'\b' + re.escape(kw) + r'\b', ' ', cleaned_text, flags=re.IGNORECASE).strip()

        cleaned_text = re.sub(r'^\W+|\W+$', '', cleaned_text).strip()
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()

        return cleaned_text

    def process_query(self, query):
        """
        Xử lý câu hỏi của người dùng để trích xuất ý định và các thực thể.
        Trả về một dictionary chứa intent và các tham số.
        """
        query_lower = query.lower().strip()
        print(f"DEBUG NLP: Xử lý truy vấn: '{query_lower}'") # DEBUG

        # --- Nhận diện Ý định CHÀO HỎI (Ưu tiên cao nhất) ---
        print(f"DEBUG NLP: Kiểm tra Greeting (từ khóa: {self.greeting_keywords_list})") # DEBUG
        for kw in self.greeting_keywords_list:
            if kw in query_lower:
                print(f"DEBUG NLP: MATCHED Greeting: '{kw}'") # DEBUG
                return {"intent": "greeting"}

        # --- Nhận diện Ý định TẢI LOG CỤC BỘ ---
        print(f"DEBUG NLP: Kiểm tra Download Log (từ khóa: {self.download_log_keywords_list})") # DEBUG
        for kw in self.download_log_keywords_list:
            if kw in query_lower:
                print(f"DEBUG NLP: MATCHED Download Log: '{kw}'") # DEBUG
                return {"intent": "download_logs"} 

        # --- Nhận diện Ý định HƯỚNG DẪN ---
        print(f"DEBUG NLP: Kiểm tra Guidance (từ khóa: {self.guidance_keywords_list})") # DEBUG
        for kw in self.guidance_keywords_list:
            if kw in query_lower:
                print(f"DEBUG NLP: MATCHED Guidance: '{kw}'") # DEBUG
                return {"intent": "request_guidance"}

        # --- Nhận diện Ý định BÁO CÁO TÌNH TRẠNG/VẤN ĐỀ ---
        print(f"DEBUG NLP: Kiểm tra Report Status (regex: {self.problem_keywords_regex})") # DEBUG
        problem_report_regex_combined = (
            r'(.+?)\s+' + self.problem_keywords_regex + r'|' + 
            self.problem_keywords_regex + r'\s+([a-zA-Z0-9\s.-]+)'
        )
        match_problem = re.search(problem_report_regex_combined, query_lower)
        if match_problem:
            print(f"DEBUG NLP: MATCHED Report Status. Groups: {match_problem.groups()}") # DEBUG
            reported_item_or_location = None
            problem_description = None

            if match_problem.group(1):
                reported_item_or_location = match_problem.group(1).strip()
                problem_description_raw = match_problem.group(0)[len(reported_item_or_location):].strip()
                for kw_problem in self.problem_keywords_list:
                    if re.search(r'\b' + re.escape(kw_problem) + r'\b', problem_description_raw, flags=re.IGNORECASE):
                        problem_description = kw_problem
                        break
            elif match_problem.group(2):
                problem_description_raw = match_problem.group(0)[0:match_problem.start(2) - match_problem.start(0)].strip()
                reported_item_or_location = match_problem.group(2).strip()
                for kw_problem in self.problem_keywords_list:
                    if re.search(r'\b' + re.escape(kw_problem) + r'\b', problem_description_raw, flags=re.IGNORECASE):
                        problem_description = kw_problem
                        break

            if reported_item_or_location and problem_description:
                print(f"DEBUG NLP: Extracted Item/Loc: '{reported_item_or_location}', Problem: '{problem_description}'") # DEBUG
                is_id = re.fullmatch(r'[a-zA-Z0-9-]+', reported_item_or_location)
                is_location_phrase = re.fullmatch(r'(tủ|kệ)\s+([a-zA-Z0-9\s.-]+)', reported_item_or_location)

                if is_id:
                    return {"intent": "report_status_or_problem", "reported_id": reported_item_or_location.upper(), "problem_description": problem_description}
                elif is_location_phrase:
                    return {"intent": "report_status_or_problem", "reported_location": reported_item_or_location, "problem_description": problem_description}
                else:
                    return {"intent": "report_status_or_problem", "reported_item_name": reported_item_or_location, "problem_description": problem_description}


        # --- Các ý định tìm kiếm vị trí ---
        print(f"DEBUG NLP: Kiểm tra Get Location (regex: {self.location_phrases_regex})") # DEBUG
        # Mẫu 1: [tên/công thức] ở đâu / vị trí của [tên/công thức] (ví dụ: "h2so4 ở đâu?")
        match_get_location_direct = re.search(r'([a-zA-Z0-9\s.-]+?)\s+' + self.location_phrases_regex, query_lower)
        if match_get_location_direct:
            print(f"DEBUG NLP: MATCHED Get Location (direct). Groups: {match_get_location_direct.groups()}") # DEBUG
            item_name = match_get_location_direct.group(1).strip()
            item_name = self._remove_keywords(item_name, self.general_stopwords_list + self.quantity_phrases_list + self.unit_words_list)
            if item_name:
                print(f"DEBUG NLP: Extracted Location Item (direct): '{item_name}'") # DEBUG
                return {"intent": "get_location", "item_name": item_name}

        # Mẫu 2: tìm/liệt kê/có vị trí [tên/công thức] (ví dụ: "tìm vị trí h2so4")
        print(f"DEBUG NLP: Kiểm tra Get Location (verb phrase) (regex: {self.list_search_verbs_regex} ... {self.location_phrases_regex})") # DEBUG
        match_get_location_verb_phrase = re.search(self.list_search_verbs_regex + r'\s+' + self.location_phrases_regex + r'\s*(của)?\s*([a-zA-Z0-9\s.-]+)', query_lower)
        if match_get_location_verb_phrase:
            print(f"DEBUG NLP: MATCHED Get Location (verb phrase). Groups: {match_get_location_verb_phrase.groups()}") # DEBUG
            item_name = match_get_location_verb_phrase.group(4).strip()
            item_name = self._remove_keywords(item_name, self.general_stopwords_list + self.quantity_phrases_list + self.unit_words_list)
            if item_name:
                print(f"DEBUG NLP: Extracted Location Item (verb phrase): '{item_name}'") # DEBUG
                return {"intent": "get_location", "item_name": item_name}

        # --- Các ý định tìm kiếm khác (sau vị trí và báo cáo) ---
        # ... (phần còn lại của hàm process_query, không thay đổi) ...

        # --- Ý định chung (Fallback cuối cùng) ---
        print(f"DEBUG NLP: Rơi vào General Search Fallback.") # DEBUG
        commands_to_remove_in_general_search = list(set(
            self.general_stopwords_list + self.quantity_phrases_list + self.unit_words_list +
            self.status_keywords_list + self.guidance_keywords_list + self.download_log_keywords_list +
            self.greeting_keywords_list + self.problem_keywords_list + self.location_phrases_list +
            self.list_search_verbs_regex.replace(r'(?:', '').replace(r')', '').split('|')
        ))

        cleaned_query_for_general_search = query_lower
        for kw in commands_to_remove_in_general_search:
            cleaned_query_for_general_search = re.sub(r'\b' + re.escape(kw) + r'\b', ' ', cleaned_query_for_general_search, flags=re.IGNORECASE).strip()

        cleaned_query_for_general_search = re.sub(r'\s+', ' ', cleaned_query_for_general_search).strip()

        if not cleaned_query_for_general_search:
            return {"intent": "search_item", "query": ""} 

        return {"intent": "search_item", "query": cleaned_query_for_general_search}

    def _extract_item_name(self, query_lower, keywords_to_remove):
        item_name_candidate = query_lower
        for kw in keywords_to_remove:
            item_name_candidate = item_name_candidate.replace(kw, "").strip()

        item_name_candidate = re.sub(r'(của|là|\?|vật tư|hóa chất)$', '', item_name_candidate).strip()
        item_name_candidate = re.sub(r'\s+', ' ', item_name_candidate).strip()
        return item_name_candidate