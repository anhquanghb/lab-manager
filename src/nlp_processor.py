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
        # Các từ khóa và regex patterns
        self.quantity_phrases_list = ["có bao nhiêu", "số lượng", "bao nhiêu"]
        self.unit_words_list = ["chai", "lọ", "thùng", "gói", "hộp", "bình", "cái", "m", "kg", "g", "ml", "l", "đơn vị", "viên", "cuộn"]
        self.general_stopwords_list = ["tìm", "kiếm", "về", "thông tin về", "cho tôi biết về", "hãy tìm", "hỏi về", "của", "là", "?", "vật tư", "hóa chất", "chất"]
        self.status_keywords_list = ["đã mở", "còn nguyên", "đã sử dụng", "hết hạn", "còn hạn", "còn", "hết", "đang sử dụng", "sử dụng", "còn lại", "còn bao nhiêu", "tình trạng", "trạng thái"]
        self.guidance_keywords_list = ["hướng dẫn", "giúp tôi tìm kiếm", "cách tìm kiếm", "cách hỏi", "chỉ dẫn", "tôi không hiểu", "bạn có thể hướng dẫn không"]
        self.download_log_keywords_list = ["tải nhật ký", "xuất log", "lịch sử chat", "tải log"]
        self.greeting_keywords_list = ["xin chào", "chào", "hello", "hi", "hey"]
        self.problem_keywords_list = ["không thấy", "đã hết", "không còn", "hư hỏng", "hỏng", "bị hỏng", "thiếu", "bị mất", "bị thất lạc", "bị lỗi", "lỗi", "vấn đề", "sự cố"]
        self.location_phrases_list = ["ở đâu", "vị trí của"]

        # Hàm trợ giúp để chuyển danh sách từ/cụm từ sang regex pattern an toàn
        # Giữ lại hàm này vì nó vẫn được dùng trong các regex khác
        def _list_to_regex_pattern(word_list):
            pattern_parts = []
            for phrase in word_list:
                regex_phrase = r'\s+'.join(re.escape(word) for word in phrase.split())
                pattern_parts.append(regex_phrase)
            return r"(?:" + "|".join(pattern_parts) + r")"

        self.quantity_phrases_regex = _list_to_regex_pattern(self.quantity_phrases_list)
        self.unit_words_regex = _list_to_regex_pattern(self.unit_words_list)
        self.status_keywords_regex = _list_to_regex_pattern(self.status_keywords_list)
        self.problem_keywords_regex = _list_to_regex_pattern(self.problem_keywords_list)
        self.location_phrases_regex = _list_to_regex_pattern(self.location_phrases_list)

        self.list_search_verbs_regex = r'(?:liệt\s+kê|tìm|có|thống\s+kê)'


    def _remove_keywords(self, text, keywords_to_remove_list):
        """
        Hàm trợ giúp để loại bỏ các từ khóa khỏi chuỗi truy vấn.
        Keywords_to_remove_list phải là danh sách các chuỗi, không phải regex.
        """
        cleaned_text = text
        for kw in keywords_to_remove_list:
            # Tạo pattern cho từng từ khóa để thay thế
            # Thay thế khoảng trắng trong từ khóa bằng \s+ để khớp đúng regex, sau đó re.escape toàn bộ
            kw_pattern = r'\b' + r'\s+'.join(re.escape(word) for word in kw.split()) + r'\b'
            cleaned_text = re.sub(kw_pattern, ' ', cleaned_text, flags=re.IGNORECASE).strip()

        cleaned_text = re.sub(r'^\W+|\W+$', '', cleaned_text).strip()
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()

        return cleaned_text

    def process_query(self, query):
        query_lower = query.lower().strip()
        print(f"DEBUG NLP: Xử lý truy vấn: '{query_lower}'")

        # --- Nhận diện Ý định CHÀO HỎI (Ưu tiên cao nhất) ---
        for kw in self.greeting_keywords_list:
            if kw in query_lower:
                print(f"DEBUG NLP: MATCHED Greeting: '{kw}'")
                return {"intent": "greeting"}

        # --- Nhận diện Ý định TẢI LOG CỤC BỘ ---
        for kw in self.download_log_keywords_list:
            if kw in query_lower:
                print(f"DEBUG NLP: MATCHED Download Log: '{kw}'")
                return {"intent": "download_logs"} 

        # --- Nhận diện Ý định HƯỚNG DẪN ---
        for kw in self.guidance_keywords_list:
            if kw in query_lower:
                print(f"DEBUG NLP: MATCHED Guidance: '{kw}'")
                return {"intent": "request_guidance"}

        # --- Nhận diện Ý định BÁO CÁO TÌNH TRẠNG/VẤN ĐỀ (Sử dụng cách kiểm tra từ khóa đơn giản hơn) ---
        # Xử lý các mẫu: "không thấy H2SO4", "H2SO4 đã hết", "tủ sấy bị hỏng"
        print(f"DEBUG NLP: Kiểm tra Report Status (simple keyword check)") # DEBUG

        reported_item_or_location = None
        problem_description = None

        # Tìm từ khóa vấn đề và vị trí của nó
        problem_match_pos = -1
        matched_problem_kw = ""
        for kw in self.problem_keywords_list:
            pos = query_lower.find(kw)
            if pos != -1:
                problem_match_pos = pos
                matched_problem_kw = kw
                break

        if problem_match_pos != -1:
            # Nếu từ khóa vấn đề ở đầu hoặc giữa: (problem item) hoặc (item problem)
            # Loại bỏ từ khóa vấn đề để lấy item_or_location
            temp_query_without_problem_kw = query_lower.replace(matched_problem_kw, '').strip()
            reported_item_or_location = self._remove_keywords(temp_query_without_problem_kw, self.general_stopwords_list + self.quantity_phrases_list + self.unit_words_list + self.location_phrases_list)
            problem_description = matched_problem_kw

            if reported_item_or_location:
                print(f"DEBUG NLP: MATCHED Report Status (simple). Item/Loc: '{reported_item_or_location}', Problem: '{problem_description}'") # DEBUG
                is_id = re.fullmatch(r'[a-zA-Z0-9-]+', reported_item_or_location)
                is_location_phrase = re.fullmatch(r'(tủ|kệ)\s+([a-zA-Z0-9\s.-]+)', reported_item_or_location)

                if is_id:
                    return {"intent": "report_status_or_problem", "reported_id": reported_item_or_location.upper(), "problem_description": problem_description}
                elif is_location_phrase:
                    return {"intent": "report_status_or_problem", "reported_location": reported_item_or_location, "problem_description": problem_description}
                else:
                    return {"intent": "report_status_or_problem", "reported_item_name": reported_item_or_location, "problem_description": problem_description}

        # --- Các ý định tìm kiếm vị trí (Sử dụng cách kiểm tra từ khóa đơn giản hơn) ---
        # Mẫu: [tên/công thức] ở đâu / vị trí của [tên/công thức] / tìm vị trí [tên]
        print(f"DEBUG NLP: Kiểm tra Get Location (simple keyword check)") # DEBUG

        location_match = None
        item_name_for_location = None

        # Mẫu 1: [item] ở đâu / [item] vị trí của
        for loc_phrase in self.location_phrases_list:
            if loc_phrase in query_lower:
                parts = query_lower.split(loc_phrase, 1)
                if parts:
                    item_name_candidate = parts[0].strip() # Lấy phần trước "ở đâu"
                    item_name_for_location = self._remove_keywords(item_name_candidate, self.general_stopwords_list + self.quantity_phrases_list + self.unit_words_list)
                    if item_name_for_location:
                        location_match = loc_phrase
                        break

        # Mẫu 2: tìm vị trí [item] / liệt kê ở đâu [item]
        if not item_name_for_location: # Nếu mẫu 1 không khớp
            for verb in self.list_search_verbs_regex.replace(r'(?:', '').replace(r')', '').split('|'):
                for loc_phrase in self.location_phrases_list:
                    pattern = verb + r'\s+' + loc_phrase # ví dụ: "tìm ở đâu"
                    match = re.search(pattern, query_lower)
                    if match:
                        item_name_candidate = query_lower[match.end():].strip() # Lấy phần sau "tìm ở đâu"
                        item_name_for_location = self._remove_keywords(item_name_candidate, self.general_stopwords_list + self.quantity_phrases_list + self.unit_words_list)
                        if item_name_for_location:
                            location_match = loc_phrase
                            break
                if item_name_for_location:
                    break

        if item_name_for_location and location_match:
            print(f"DEBUG NLP: MATCHED Get Location (simple). Item: '{item_name_for_location}'") # DEBUG
            return {"intent": "get_location", "item_name": item_name_for_location}

        # --- Các ý định tìm kiếm khác (sau vị trí và báo cáo) ---

        # Ý định: Get Quantity AND Status
        match_quantity_status = re.search(self.quantity_phrases_regex + r'\s+(?:' + self.unit_words_regex + r')?\s*([a-zA-Z0-9\s.-]+?)\s+' + self.status_keywords_regex, query_lower)
        if match_quantity_status:
            raw_item_name = match_quantity_status.group(2).strip()
            status_found = match_quantity_status.group(3).strip()
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

        # Ý định: List by Location (Đơn thuần, nhưng bây giờ sẽ là tìm kiếm chung)
        match_location_simple = re.search(self.list_search_verbs_regex + r'\s*(trong|từ|ở)?\s*(tủ|kệ)\s+([a-zA-Z0-9\s.-]+)', query_lower)
        if match_location_simple:
            # Nếu bạn vẫn muốn có một intent riêng cho list_by_location_simple, hãy giữ lại đoạn này
            # và xử lý trong chatbot_logic. Tuy nhiên, nếu mục đích là chuyển về tìm kiếm chung,
            # thì block này cũng nên được bỏ đi. Để phù hợp với giải pháp "chuyển về tìm kiếm chung",
            # tôi sẽ bỏ đi logic này.
            pass 


        # --- Ý định chung (Fallback cuối cùng) ---
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
        # Hàm này sẽ được tích hợp hoàn toàn vào _remove_keywords hoặc xóa nếu không còn dùng.
        item_name_candidate = query_lower
        for kw in keywords_to_remove:
            item_name_candidate = item_name_candidate.replace(kw, "").strip()

        item_name_candidate = re.sub(r'(của|là|\?|vật tư|hóa chất)$', '', item_name_candidate).strip()
        item_name_candidate = re.sub(r'\s+', ' ', item_name_candidate).strip()
        return item_name_candidate