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
        # CÁC TỪ KHÓA LỆNH CHÍNH (Xác định INTENT) - theo yêu cầu mới của người dùng
        self.command_search_verbs_list = ["tìm", "hãy tìm", "tra cứu", "kiếm", "thông tin về", "hỏi về"]
        self.command_location_phrases_list = ["ở đâu", "vị trí của"]
        self.command_quantity_phrases_list = ["số lượng", "có bao nhiêu", "bao nhiêu", "còn bao nhiêu", "số", "lượng", "còn lại", "còn"]
        self.command_status_phrases_list = ["tình trạng", "trạng thái"] # Từ khóa để hỏi về tình trạng (ý định)
        self.command_guidance_phrases_list = ["hướng dẫn", "giúp tôi tìm kiếm", "cách tìm kiếm", "cách hỏi", "chỉ dẫn", "tôi không hiểu", "bạn có thể hướng dẫn không", "xin chào", "chào", "hello", "hi", "hey"]
        self.download_log_command_phrases_list = ["tải nhật ký", "xuất log", "lịch sử chat", "tải log"]

        # CÁC TỪ KHÓA GIÁ TRỊ/THUỘC TÍNH (Sử dụng để trích xuất ENTITY hoặc lọc)
        self.item_type_keywords_list = ["vật tư", "hóa chất", "thiết bị"] # Loại item
        self.specific_status_values_list = ["đã mở", "còn nguyên", "đã sử dụng", "hết hạn", "còn hạn", "còn", "hết", "đang sử dụng", "sử dụng"] # Giá trị của tình trạng
        self.problem_keywords_list = ["không thấy", "đã hết", "không còn", "hỏng", "bị hỏng", "thiếu", "bị mất", "bị thất lạc", "bị lỗi", "lỗi", "vấn đề", "sự cố"] # Từ khóa báo cáo sự cố
        self.unit_words_list = ["chai", "lọ", "thùng", "gói", "hộp", "bình", "cái", "m", "kg", "g", "ml", "l", "đơn vị", "viên", "cuộn","cái", "cục", "gói", "hộp", "bịch"] # Từ khóa đơn vị

        # Các từ dừng chung khác (để làm sạch chung nếu không phải từ khóa lệnh)
        self.general_stopwords_list = ["về", "thông tin về", "cho tôi biết về", "hỏi về", "của", "là", "?", "và", "trong", "ở", "tại", "có", "có thể", "làm thế nào", "giúp tôi", "giúp", "bạn có thể", "bạn muốn", "bạn cần", "bạn có biết", "bạn có thể cho tôi biết", "các", "này",] 

        # REGEX PATTERNS TỪ CÁC DANH SÁCH (cho các regex cụ thể)
        def _list_to_regex_pattern(word_list):
            pattern_parts = []
            for phrase in word_list:
                regex_phrase = r'\s+'.join(re.escape(word) for word in phrase.split())
                pattern_parts.append(regex_phrase)
            return r"(?:" + "|".join(pattern_parts) + r")"

        self.location_phrases_regex = _list_to_regex_pattern(self.command_location_phrases_list)
        self.quantity_phrases_regex = _list_to_regex_pattern(self.command_quantity_phrases_list)
        self.status_command_phrases_regex = _list_to_regex_pattern(self.command_status_phrases_list)
        self.problem_keywords_regex = _list_to_regex_pattern(self.problem_keywords_list)
        self.search_command_verbs_regex = _list_to_regex_pattern(self.command_search_verbs_list) # Động từ tìm kiếm (tìm, tra cứu, ...)
        self.item_type_keywords_regex = _list_to_regex_pattern(self.item_type_keywords_list) # Hóa chất, vật tư, thiết bị


    def _remove_keywords(self, text, keywords_to_remove_list):
        """
        Hàm trợ giúp để loại bỏ các từ khóa khỏi chuỗi truy vấn.
        Keywords_to_remove_list phải là danh sách các chuỗi, không phải regex.
        """
        cleaned_text = text
        for kw in keywords_to_remove_list:
            kw_pattern = r'\b' + r'\s+'.join(re.escape(word) for word in kw.split()) + r'\b'
            cleaned_text = re.sub(kw_pattern, ' ', cleaned_text, flags=re.IGNORECASE).strip()

        cleaned_text = re.sub(r'^\W+|\W+$', '', cleaned_text).strip()
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()

        return cleaned_text

    def process_query(self, query):
        query_lower = query.lower().strip()
        print(f"DEBUG NLP: Xử lý truy vấn: '{query_lower}'") # DEBUG

        # --- Nhận diện Ý định HƯỚNG DẪN (Ưu tiên cao nhất, bao gồm chào hỏi) ---
        if any(kw in query_lower for kw in self.command_guidance_phrases_list): # Sử dụng command_guidance_phrases_list
            print(f"DEBUG NLP: MATCHED Guidance.") # DEBUG
            return {"intent": "request_guidance"}

        # --- Nhận diện Ý định TẢI LOG CỤC BỘ ---
        if any(kw in query_lower for kw in self.download_log_command_phrases_list):
            print(f"DEBUG NLP: MATCHED Download Log.") # DEBUG
            return {"intent": "download_logs"} 

        # --- Nhận diện Ý định BÁO CÁO SỰ CỐ (report_issue) ---
        print(f"DEBUG NLP: Kiểm tra Report Issue logic.") # DEBUG
        has_problem_keyword = any(kw in query_lower for kw in self.problem_keywords_list)
        has_search_command_verb = any(kw in query_lower for kw in self.command_search_verbs_list)

        if has_problem_keyword and not has_search_command_verb:
            print(f"DEBUG NLP: MATCHED Report Issue (Problem keyword present, no search command verb).") # DEBUG
            problem_report_regex_combined = (
                r'(.+?)\s+' + self.problem_keywords_regex + r'|' + # Item Problem
                self.problem_keywords_regex + r'\s+([a-zA-Z0-9\s.-]+)' # Problem Item
            )
            match_problem = re.search(problem_report_regex_combined, query_lower)
            if match_problem:
                print(f"DEBUG NLP: Matched Problem Regex. Groups: {match_problem.groups()}") # DEBUG
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
                    print(f"DEBUG NLP: Extracted Item/Loc for Report: '{reported_item_or_location}', Problem: '{problem_description}'") # DEBUG
                    is_id = re.fullmatch(r'[a-zA-Z0-9-]+', reported_item_or_location)
                    is_location_phrase = re.fullmatch(r'(tủ|kệ)\s+([a-zA-Z0-9\s.-]+)', reported_item_or_location)

                    if is_id:
                        return {"intent": "report_issue", "reported_id": reported_item_or_location.upper(), "problem_description": problem_description}
                    elif is_location_phrase:
                        return {"intent": "report_issue", "reported_location": reported_item_or_location, "problem_description": problem_description}
                    else:
                        return {"intent": "report_issue", "reported_item_name": reported_item_or_location, "problem_description": problem_description}

        # --- Xác định loại lệnh theo từ khóa chính (ưu tiên theo thứ tự: vị trí, số lượng, trạng thái, tìm kiếm chung) ---

        # Ý định: Lệnh Vị trí (get_location)
        if any(kw in query_lower for kw in self.command_location_phrases_list):
            print(f"DEBUG NLP: MATCHED Get Location command.") # DEBUG
            item_name_candidate = self._remove_keywords(query_lower, self.command_location_phrases_list + self.command_search_verbs_list)
            if item_name_candidate:
                print(f"DEBUG NLP: Extracted Location Item (simple): '{item_name_candidate}'") # DEBUG
                return {"intent": "get_location", "item_name": item_name_candidate}
            return {"intent": "get_location", "item_name": None}

        # Ý định: Lệnh Thống kê/Số lượng (get_quantity)
        if any(kw in query_lower for kw in self.command_quantity_phrases_list):
            print(f"DEBUG NLP: Kiểm tra Get Quantity (simple keyword check)") # DEBUG
            item_name_candidate = self._remove_keywords(query_lower, self.command_quantity_phrases_list + self.command_search_verbs_list + self.command_location_phrases_list + self.unit_words_list)
            if item_name_candidate:
                return {"intent": "get_quantity", "item_name": item_name_candidate}
            return {"intent": "get_quantity", "item_name": None}

        # Ý định: Lệnh Tình trạng (get_status)
        if any(kw in query_lower for kw in self.command_status_phrases_list):
            print(f"DEBUG NLP: Kiểm tra Get Status (simple keyword check)") # DEBUG
            item_name_candidate = self._remove_keywords(query_lower, self.command_status_phrases_list + self.command_search_verbs_list + self.command_location_phrases_list + self.command_quantity_phrases_list)
            if item_name_candidate:
                print(f"DEBUG NLP: Extracted Status Item (simple): '{item_name_candidate}'") # DEBUG
                return {"intent": "get_status", "item_name": item_name_candidate}
            return {"intent": "get_status", "item_name": None}

        # Ý định: Lệnh Tìm kiếm (search_item) - Nếu có từ khóa lệnh tìm kiếm (hoặc chỉ loại item)
        if any(kw in query_lower for kw in self.command_search_verbs_list):
            print(f"DEBUG NLP: MATCHED Search command.") # DEBUG
            cleaned_query = self._remove_keywords(query_lower, self.command_search_verbs_list + self.command_location_phrases_list + self.command_quantity_phrases_list + self.command_status_phrases_list)
            if cleaned_query:
                print(f"DEBUG NLP: Cleaned Search Query (verb check): '{cleaned_query}'") # DEBUG
                return {"intent": "search_item", "query": cleaned_query}
            return {"intent": "search_item", "query": None}

        # Nếu chỉ có từ khóa loại item mà không có từ khóa lệnh nào khác
        if any(kw in query_lower for kw in self.item_type_keywords_list):
            print(f"DEBUG NLP: MATCHED Item Type (implicit search).") # DEBUG
            cleaned_query = self._remove_keywords(query_lower, self.item_type_keywords_list)
            if cleaned_query:
                print(f"DEBUG NLP: Cleaned Item Type Query: '{cleaned_query}'") # DEBUG
                return {"intent": "search_item", "query": cleaned_query}
            return {"intent": "search_item", "query": query_lower}

        # --- Ý định chung (Fallback cuối cùng) ---
        print(f"DEBUG NLP: Rơi vào General Search Fallback.") # DEBUG
        all_command_keywords = list(set(
            self.command_search_verbs_list + self.command_location_phrases_list +
            self.command_quantity_phrases_list + self.command_status_phrases_list +
            self.general_stopwords_list + self.command_guidance_phrases_list + # ĐÃ SỬA TÊN BIẾN
            self.download_log_command_phrases_list + self.greeting_keywords_list + # TÊN ĐÃ ĐÚNG NHƯ __init__
            self.problem_keywords_list + self.unit_words_list +
            self.item_type_keywords_list
        ))

        cleaned_query_for_general_search = self._remove_keywords(query_lower, all_command_keywords)

        if not cleaned_query_for_general_search:
            return {"intent": "search_item", "query": ""} 

        return {"intent": "search_item", "query": cleaned_query_for_general_search}

    def _extract_item_name(self, query_lower, keywords_to_remove):
        # Hàm này không còn được gọi từ process_query nữa, có thể xóa hoặc giữ nếu dùng ở nơi khác.
        item_name_candidate = query_lower
        for kw in keywords_to_remove:
            item_name_candidate = item_name_candidate.replace(kw, "").strip()

        item_name_candidate = re.sub(r'(của|là|\?|vật tư|hóa chất)$', '', item_name_candidate).strip()
        item_name_candidate = re.sub(r'\s+', ' ', item_name_candidate).strip()
        return item_name_candidate