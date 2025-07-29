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
        # Hàm trợ giúp để loại bỏ dấu tiếng Việt và chuẩn hóa chuỗi về chữ thường.
        def _remove_accents_and_normalize(input_str):
            if not isinstance(input_str, str):
                return str(input_str)
            nfkd_form = unicodedata.normalize('NFKD', input_str)
            only_ascii = nfkd_form.encode('ascii', 'ignore').decode('utf-8')
            return only_ascii.lower() # Luôn chuyển về chữ thường

        # CÁC TỪ KHÓA LỆNH CHÍNH (Xác định INTENT) - đã chuẩn hóa không dấu và chữ thường
        self.command_search_verbs_list = _remove_accents_and_normalize("tìm, hãy tìm, tra cứu, kiếm, thông tin về, hỏi về, tìm mã, tìm CAS").split(', ')
        self.command_location_phrases_list = _remove_accents_and_normalize("ở đâu, vị trí của").split(', ')
        self.command_quantity_phrases_list = _remove_accents_and_normalize("số lượng, có bao nhiêu, bao nhiêu, còn bao nhiêu, số, lượng, còn lại, còn").split(', ')
        self.command_status_phrases_list = _remove_accents_and_normalize("tình trạng, trạng thái").split(', ')
        
        # Gộp từ khóa chào hỏi vào hướng dẫn
        self.command_guidance_phrases_list = _remove_accents_and_normalize("hướng dẫn, giúp tôi tìm kiếm, cách tìm kiếm, cách hỏi, chỉ dẫn, tôi không hiểu, bạn có thể hướng dẫn không, xin chào, chào, hello, hi, hey, giúp tôi").split(', ')
        
        self.upload_log_command_phrases_list = _remove_accents_and_normalize("tải nhật ký, xuất log, lịch sử chat, tải log, đẩy log").split(', ')

        # BỔ SUNG: TỪ KHÓA LỆNH LIỆT KÊ
        self.command_list_verbs_list = _remove_accents_and_normalize("liệt kê, mô tả").split(', ')

        # BỔ SUNG: TỪ KHÓA BÁO CÁO MỚI (chỉ cần "báo cáo")
        self.report_command_keywords_list = _remove_accents_and_normalize("báo cáo").split(', ')

        # CÁC TỪ KHÓA GIÁ TRỊ/THUỘC TÍNH (Sử dụng để trích xuất ENTITY hoặc lọc) - đã chuẩn hóa
        self.item_type_keywords_list = _remove_accents_and_normalize("vật tư, hóa chất, thiết bị").split(', ')
        self.specific_status_values_list = _remove_accents_and_normalize("đã mở, còn nguyên, đã sử dụng, hết hạn, còn hạn, còn, hết, đang sử dụng, sử dụng, đang mượn, thất lạc, huỷ, không xác định").split(', ')
        # problem_keywords_list vẫn giữ lại để trích xuất problem_description nếu người dùng vẫn dùng
        self.problem_keywords_list = _remove_accents_and_normalize("không thấy, đã hết, không còn, hỏng, bị hỏng, thiếu, bị mất, bị thất lạc, bị lỗi, lỗi, vấn đề, sự cố").split(', ')
        self.unit_words_list = _remove_accents_and_normalize("chai, lọ, thùng, gói, hộp, bình, cái, m, kg, g, ml, l, đơn vị, viên, cuộn, cục, bịch").split(', ')

        # Các từ dừng chung khác (để làm sạch chung nếu không phải từ khóa lệnh) - đã chuẩn hóa
        self.general_stopwords_list = _remove_accents_and_normalize("về, thông tin về, cho tôi biết về, hỏi về, của, là, ?, và, trong, ở, tại, có, có thể, làm thế nào, bạn muốn, bạn cần, bạn có biết, bạn có thể cho tôi biết, các, này, trong, tủ, phòng").split(', ')

        # REGEX PATTERNS TỪ CÁC DANH SÁCH (cho các regex cụ thể)
        def _list_to_regex_pattern(word_list):
            pattern_parts = []
            for phrase in word_list:
                regex_phrase = r'\b' + r'\s*'.join(re.escape(word) for word in phrase.split()) + r'\b'
                pattern_parts.append(regex_phrase)
            return r"(?:" + "|".join(pattern_parts) + r")"

        self.location_phrases_regex = _list_to_regex_pattern(self.command_location_phrases_list)
        self.quantity_phrases_regex = _list_to_regex_pattern(self.command_quantity_phrases_list)
        self.status_command_phrases_regex = _list_to_regex_pattern(self.command_status_phrases_list)
        self.problem_keywords_regex = _list_to_regex_pattern(self.problem_keywords_list)
        self.search_command_verbs_regex = _list_to_regex_pattern(self.command_search_verbs_list)
        self.item_type_keywords_regex = _list_to_regex_pattern(self.item_type_keywords_list)
        self.command_list_verbs_regex = _list_to_regex_pattern(self.command_list_verbs_list)
        # BỔ SUNG: REGEX CHO TỪ KHÓA BÁO CÁO MỚI
        self.report_command_regex = _list_to_regex_pattern(self.report_command_keywords_list)


    def _remove_keywords(self, text, keywords_to_remove_list):
        """
        Hàm trợ giúp để loại bỏ các từ khóa khỏi chuỗi truy vấn.
        Keywords_to_remove_list phải là danh sách các chuỗi (đã chuẩn hóa).
        Xử lý các từ khóa dài hơn trước để tránh xóa sai.
        """
        cleaned_text = text
        sorted_keywords = sorted(keywords_to_remove_list, key=len, reverse=True)

        for kw in sorted_keywords:
            kw_pattern = r'\b' + r'\s*'.join(re.escape(word) for word in kw.split()) + r'\b'
            cleaned_text = re.sub(kw_pattern, ' ', cleaned_text, flags=re.IGNORECASE).strip()

        cleaned_text = re.sub(r'^\W+|\W+$', '', cleaned_text).strip()
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()

        return cleaned_text

    def process_query(self, query):
        original_query_text = query 
        
        query_normalized = unicodedata.normalize('NFKD', query).encode('ascii', 'ignore').decode('utf-8').lower().strip()
        print(f"DEBUG NLP: Xử lý truy vấn (normalized): '{query_normalized}'")

        # --- Nhận diện Ý định HƯỚNG DẪN (Ưu tiên cao nhất, bao gồm chào hỏi) ---
        if any(re.search(r'\b' + re.escape(kw) + r'\b', query_normalized) for kw in self.command_guidance_phrases_list):
            print(f"DEBUG NLP: MATCHED Guidance/Greeting.")
            return {"intent": "request_guidance", "original_query": original_query_text}

        # --- Nhận diện Ý định TẢI LOG LÊN GITHUB ---
        if any(re.search(r'\b' + re.escape(kw) + r'\b', query_normalized) for kw in self.upload_log_command_phrases_list):
            print(f"DEBUG NLP: MATCHED Upload Log.")
            return {"intent": "upload_logs_to_github", "original_query": original_query_text}

        # --- BỔ SUNG: Nhận diện Ý định BÁO CÁO SỰ CỐ (report_issue) dựa trên từ "báo cáo" ---
        # Ưu tiên từ "báo cáo" trước các từ khóa vấn đề chi tiết
        if re.search(self.report_command_regex, query_normalized):
            print(f"DEBUG NLP: MATCHED Report Issue (via 'báo cáo' keyword).")
            
            # Loại bỏ từ "báo cáo" và các từ khóa vấn đề cũ để trích xuất phần còn lại
            temp_query_cleaned = self._remove_keywords(query_normalized, self.report_command_keywords_list + self.problem_keywords_list)
            
            reported_id = None
            reported_item_name = None
            reported_location = None
            problem_description = "không xác định" # Mặc định nếu chỉ có "báo cáo"

            # Nếu có thêm thông tin sau "báo cáo", cố gắng trích xuất
            if temp_query_cleaned:
                # Cố gắng tìm từ khóa vấn đề trong phần còn lại của câu hỏi nếu có
                for kw_problem in self.problem_keywords_list:
                    if re.search(r'\b' + re.escape(kw_problem) + r'\b', query_normalized): # Kiểm tra trên query gốc đã normalized
                        problem_description = kw_problem
                        break
                
                # Sau đó cố gắng trích xuất ID/Tên/Vị trí từ phần còn lại sau khi loại bỏ từ khóa vấn đề
                cleaned_for_entity = self._remove_keywords(temp_query_cleaned, self.problem_keywords_list)

                if re.fullmatch(r'[a-z0-9-]+', cleaned_for_entity):
                    reported_id = cleaned_for_entity.upper()
                elif re.fullmatch(r'(tủ|kệ|khu)\s*[a-z0-9.-]+', cleaned_for_entity) or (re.fullmatch(r'[a-z0-9.-]+', cleaned_for_entity) and len(cleaned_for_entity) <= 3):
                    reported_location = cleaned_for_entity
                else:
                    reported_item_name = cleaned_for_entity

            return {
                "intent": "report_issue",
                "reported_id": reported_id,
                "reported_item_name": reported_item_name,
                "reported_location": reported_location,
                "problem_description": problem_description,
                "original_query": original_query_text
            }

        # --- Nhận diện Ý định BÁO CÁO SỰ CỐ (report_issue) DỰA TRÊN CÁC TỪ KHÓA VẤN ĐỀ CŨ ---
        # Logic này chỉ chạy nếu không khớp với từ "báo cáo" ở trên
        has_problem_keyword = any(re.search(r'\b' + re.escape(kw) + r'\b', query_normalized) for kw in self.problem_keywords_list)
        has_search_command_verb = any(re.search(r'\b' + re.escape(kw) + r'\b', query_normalized) for kw in self.command_search_verbs_list)

        if has_problem_keyword and not has_search_command_verb:
            print(f"DEBUG NLP: MATCHED Report Issue (Problem keyword present, no search command verb).")
            
            temp_query_cleaned = self._remove_keywords(query_normalized, self.problem_keywords_list)
            
            reported_id = None
            reported_item_name = None
            reported_location = None
            problem_description = ""

            for kw_problem in self.problem_keywords_list:
                if re.search(r'\b' + re.escape(kw_problem) + r'\b', query_normalized):
                    problem_description = kw_problem
                    break

            if re.fullmatch(r'[a-z0-9-]+', temp_query_cleaned):
                reported_id = temp_query_cleaned.upper()
            elif re.fullmatch(r'(tủ|kệ|khu)\s*[a-z0-9.-]+', temp_query_cleaned) or (re.fullmatch(r'[a-z0-9.-]+', temp_query_cleaned) and len(temp_query_cleaned) <= 3):
                reported_location = temp_query_cleaned
            else:
                reported_item_name = temp_query_cleaned

            if reported_id or reported_item_name or reported_location:
                return {
                    "intent": "report_issue",
                    "reported_id": reported_id,
                    "reported_item_name": reported_item_name,
                    "reported_location": reported_location,
                    "problem_description": problem_description if problem_description else "không xác định",
                    "original_query": original_query_text
                }
            else:
                return {"intent": "report_issue", "problem_description": problem_description if problem_description else "không xác định", "raw_query": query, "original_query": original_query_text}


        # --- Xác định loại lệnh theo từ khóa chính (ưu tiên theo thứ tự: vị trí, số lượng, trạng thái, tìm kiếm chung) ---

        # Ý định: Lệnh Vị trí (get_location)
        if re.search(self.location_phrases_regex, query_normalized):
            print(f"DEBUG NLP: MATCHED Get Location command.")
            item_name_candidate = self._remove_keywords(query_normalized, self.command_location_phrases_list + self.command_search_verbs_list)
            if item_name_candidate:
                print(f"DEBUG NLP: Extracted Location Item: '{item_name_candidate}'")
                return {"intent": "get_location", "item_name": item_name_candidate, "original_query": original_query_text}
            return {"intent": "get_location", "item_name": None, "original_query": original_query_text}

        # Ý định: Lệnh Thống kê/Số lượng (get_quantity)
        if re.search(self.quantity_phrases_regex, query_normalized):
            print(f"DEBUG NLP: MATCHED Get Quantity command.")
            item_name_candidate = self._remove_keywords(query_normalized, self.command_quantity_phrases_list + self.command_search_verbs_list + self.command_location_phrases_list + self.unit_words_list)
            if item_name_candidate:
                print(f"DEBUG NLP: Extracted Quantity Item: '{item_name_candidate}'")
                return {"intent": "get_quantity", "item_name": item_name_candidate, "original_query": original_query_text}
            return {"intent": "get_quantity", "item_name": None, "original_query": original_query_text}

        # Ý định: Lệnh Tình trạng (get_status)
        if re.search(self.status_command_phrases_regex, query_normalized):
            print(f"DEBUG NLP: MATCHED Get Status command.")
            item_name_candidate = self._remove_keywords(query_normalized, self.command_status_phrases_list + self.command_search_verbs_list + self.command_location_phrases_list + self.command_quantity_phrases_list)
            if item_name_candidate:
                print(f"DEBUG NLP: Extracted Status Item: '{item_name_candidate}'")
                return {"intent": "get_status", "item_name": item_name_candidate, "original_query": original_query_text}
            return {"intent": "get_status", "item_name": None, "original_query": original_query_text}

        # BỔ SUNG: NHẬN DIỆN Ý ĐỊNH LIỆT KÊ (LIST_BY_...)
        location_list_full_pattern = r"(?:{})\s*((?:tủ|kệ|khu)\s*[a-z0-9.-]+|[a-z0-9.-]+)\s*$".format(self.command_list_verbs_regex)
        match_location_list = re.search(location_list_full_pattern, query_normalized)
        if match_location_list:
            location_entity = match_location_list.group(1).strip()
            if location_entity:
                print(f"DEBUG NLP: MATCHED List By Location. Entity: '{location_entity}'")
                return {"intent": "list_by_location", "location_query": location_entity, "original_query": original_query_text}
            
        type_list_pattern = r"(?:{})\s*(?:{})".format(self.command_list_verbs_regex, self.item_type_keywords_regex)
        match_type_list = re.search(type_list_pattern, query_normalized)
        if match_type_list:
            found_type_keyword = None
            for kw in self.item_type_keywords_list:
                if re.search(r'\b' + re.escape(kw) + r'\b', query_normalized):
                    found_type_keyword = kw
                    break
            if found_type_keyword:
                print(f"DEBUG NLP: MATCHED List By Type. Type: '{found_type_keyword}'")
                return {"intent": "list_by_type", "item_type": found_type_keyword, "original_query": original_query_text}

        # Ý định: Lệnh Tìm kiếm (search_item) - Cho các từ khóa lệnh tìm kiếm chung
        if re.search(self.search_command_verbs_regex, query_normalized):
            print(f"DEBUG NLP: MATCHED Search command verb.")
            cleaned_query = self._remove_keywords(query_normalized, 
                                                    self.command_search_verbs_list + 
                                                    self.command_location_phrases_list + 
                                                    self.command_quantity_phrases_list + 
                                                    self.command_status_phrases_list + 
                                                    self.command_list_verbs_list +
                                                    self.general_stopwords_list)
            if cleaned_query:
                print(f"DEBUG NLP: Cleaned Search Query (verb check): '{cleaned_query}'")
                return {"intent": "search_item", "query": cleaned_query, "original_query": original_query_text}
            return {"intent": "search_item", "query": None, "original_query": original_query_text}

        # Nếu chỉ có từ khóa loại item mà không có từ khóa lệnh nào khác (implicit search)
        if re.search(self.item_type_keywords_regex, query_normalized):
            print(f"DEBUG NLP: MATCHED Item Type (implicit search).")
            cleaned_query = self._remove_keywords(query_normalized, self.item_type_keywords_list)
            if cleaned_query:
                print(f"DEBUG NLP: Cleaned Item Type Query: '{cleaned_query}'")
                return {"intent": "search_item", "query": cleaned_query, "original_query": original_query_text}
            return {"intent": "search_item", "query": query_normalized, "original_query": original_query_text}

        # --- Ý định chung (Fallback cuối cùng) ---
        print(f"DEBUG NLP: Rơi vào General Search Fallback.")
        all_command_keywords = list(set(
            self.command_search_verbs_list + self.command_location_phrases_list +
            self.command_quantity_phrases_list + self.command_status_phrases_list +
            self.general_stopwords_list + self.command_guidance_phrases_list + 
            self.upload_log_command_phrases_list + 
            self.problem_keywords_list + self.unit_words_list +
            self.item_type_keywords_list + 
            self.command_list_verbs_list +
            self.report_command_keywords_list # Bổ sung từ khóa báo cáo vào đây
        ))

        cleaned_query_for_general_search = self._remove_keywords(query_normalized, all_command_keywords)

        if not cleaned_query_for_general_search:
            return {"intent": "search_item", "query": "", "original_query": original_query_text}

        return {"intent": "search_item", "query": cleaned_query_for_general_search, "original_query": original_query_text}