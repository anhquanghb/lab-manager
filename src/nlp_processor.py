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
        # Được định nghĩa cục bộ trong class để tiện sử dụng cho các list từ khóa.
        def _remove_accents_and_normalize(input_str):
            if not isinstance(input_str, str):
                return str(input_str)
            nfkd_form = unicodedata.normalize('NFKD', input_str)
            only_ascii = nfkd_form.encode('ascii', 'ignore').decode('utf-8')
            return only_ascii.lower() # Luôn chuyển về chữ thường

        # CÁC TỪ KHÓA LỆNH CHÍNH (Xác định INTENT) - đã chuẩn hóa không dấu và chữ thường
        self.command_search_verbs_list = _remove_accents_and_normalize("tìm, hãy tìm, tra cứu, kiếm, thông tin về, hỏi về").split(', ')
        self.command_location_phrases_list = _remove_accents_and_normalize("ở đâu, vị trí của").split(', ')
        self.command_quantity_phrases_list = _remove_accents_and_normalize("số lượng, có bao nhiêu, bao nhiêu, còn bao nhiêu, số, lượng, còn lại, còn").split(', ')
        self.command_status_phrases_list = _remove_accents_and_normalize("tình trạng, trạng thái").split(', ')
        
        # Gộp từ khóa chào hỏi vào hướng dẫn
        self.command_guidance_phrases_list = _remove_accents_and_normalize("hướng dẫn, giúp tôi tìm kiếm, cách tìm kiếm, cách hỏi, chỉ dẫn, tôi không hiểu, bạn có thể hướng dẫn không, xin chào, chào, hello, hi, hey, giúp tôi").split(', ')
        
        # Đã đổi tên intent từ download_logs sang upload_logs để khớp với chức năng
        self.upload_log_command_phrases_list = _remove_accents_and_normalize("tải nhật ký, xuất log, lịch sử chat, tải log, đẩy log").split(', ')

        # --- BỔ SUNG: TỪ KHÓA LỆNH LIỆT KÊ ---
        self.command_list_verbs_list = _remove_accents_and_normalize("liệt kê, mô tả").split(', ')

        # CÁC TỪ KHÓA GIÁ TRỊ/THUỘC TÍNH (Sử dụng để trích xuất ENTITY hoặc lọc) - đã chuẩn hóa
        self.item_type_keywords_list = _remove_accents_and_normalize("vật tư, hóa chất, thiết bị").split(', ')
        self.specific_status_values_list = _remove_accents_and_normalize("đã mở, còn nguyên, đã sử dụng, hết hạn, còn hạn, còn, hết, đang sử dụng, sử dụng, đang mượn, thất lạc, huỷ, không xác định").split(', ')
        self.problem_keywords_list = _remove_accents_and_normalize("không thấy, đã hết, không còn, hỏng, bị hỏng, thiếu, bị mất, bị thất lạc, bị lỗi, lỗi, vấn đề, sự cố").split(', ')
        self.unit_words_list = _remove_accents_and_normalize("chai, lọ, thùng, gói, hộp, bình, cái, m, kg, g, ml, l, đơn vị, viên, cuộn, cục, bịch").split(', ')

        # Các từ dừng chung khác (để làm sạch chung nếu không phải từ khóa lệnh) - đã chuẩn hóa
        self.general_stopwords_list = _remove_accents_and_normalize("về, thông tin về, cho tôi biết về, hỏi về, của, là, ?, và, trong, ở, tại, có, có thể, làm thế nào, bạn muốn, bạn cần, bạn có biết, bạn có thể cho tôi biết, các, này").split(', ')

        # REGEX PATTERNS TỪ CÁC DANH SÁCH (cho các regex cụ thể)
        def _list_to_regex_pattern(word_list):
            # Tạo regex pattern cho các cụm từ (có thể chứa khoảng trắng)
            pattern_parts = []
            for phrase in word_list:
                # re.escape để xử lý các ký tự đặc biệt trong từ khóa
                # \b cho ranh giới từ để tránh khớp chuỗi con
                regex_phrase = r'\b' + r'\s*'.join(re.escape(word) for word in phrase.split()) + r'\b'
                pattern_parts.append(regex_phrase)
            return r"(?:" + "|".join(pattern_parts) + r")"

        self.location_phrases_regex = _list_to_regex_pattern(self.command_location_phrases_list)
        self.quantity_phrases_regex = _list_to_regex_pattern(self.command_quantity_phrases_list)
        self.status_command_phrases_regex = _list_to_regex_pattern(self.command_status_phrases_list)
        self.problem_keywords_regex = _list_to_regex_pattern(self.problem_keywords_list)
        self.search_command_verbs_regex = _list_to_regex_pattern(self.command_search_verbs_list)
        self.item_type_keywords_regex = _list_to_regex_pattern(self.item_type_keywords_list)
        # --- BỔ SUNG: REGEX LỆNH LIỆT KÊ ---
        self.command_list_verbs_regex = _list_to_regex_pattern(self.command_list_verbs_list)


    def _remove_keywords(self, text, keywords_to_remove_list):
        """
        Hàm trợ giúp để loại bỏ các từ khóa khỏi chuỗi truy vấn.
        Keywords_to_remove_list phải là danh sách các chuỗi (đã chuẩn hóa).
        Xử lý các từ khóa dài hơn trước để tránh xóa sai.
        """
        cleaned_text = text
        # Sắp xếp từ khóa theo độ dài giảm dần để xử lý các cụm từ dài trước
        # Ví dụ: "hãy tìm" trước "tìm"
        sorted_keywords = sorted(keywords_to_remove_list, key=len, reverse=True)

        for kw in sorted_keywords: # Sử dụng sorted_keywords
            # Tạo pattern với ranh giới từ để không xóa chuỗi con không mong muốn
            # và chấp nhận 0 hoặc nhiều khoảng trắng giữa các từ trong cụm từ
            kw_pattern = r'\b' + r'\s*'.join(re.escape(word) for word in kw.split()) + r'\b'
            # Chỉ thay thế khi kw_pattern thực sự khớp với một cụm từ
            cleaned_text = re.sub(kw_pattern, ' ', cleaned_text, flags=re.IGNORECASE).strip()

        # Xóa các ký tự không phải chữ cái/số/khoảng trắng ở đầu/cuối và nhiều khoảng trắng
        cleaned_text = re.sub(r'^\W+|\W+$', '', cleaned_text).strip()
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()

        return cleaned_text

    def process_query(self, query):
        # Lưu trữ truy vấn gốc
        original_query_text = query 
        
        # Chuẩn hóa truy vấn ngay từ đầu: loại bỏ dấu và chuyển chữ thường
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

        # --- Nhận diện Ý định BÁO CÁO SỰ CỐ (report_issue) ---
        print(f"DEBUG NLP: Kiểm tra Report Issue logic.")
        has_problem_keyword = any(re.search(r'\b' + re.escape(kw) + r'\b', query_normalized) for kw in self.problem_keywords_list)
        has_search_command_verb = any(re.search(r'\b' + re.escape(kw) + r'\b', query_normalized) for kw in self.command_search_verbs_list)

        # Nếu có từ khóa vấn đề và không phải là câu lệnh tìm kiếm
        if has_problem_keyword and not has_search_command_verb:
            print(f"DEBUG NLP: MATCHED Report Issue (Problem keyword present, no search command verb).")
            
            # Loại bỏ các từ khóa vấn đề để tìm phần tên/ID/vị trí
            temp_query_cleaned = self._remove_keywords(query_normalized, self.problem_keywords_list)
            
            reported_id = None
            reported_item_name = None
            reported_location = None
            problem_description = ""

            # Cố gắng tìm từ khóa vấn đề đã khớp (từ query gốc đã chuẩn hóa)
            for kw_problem in self.problem_keywords_list:
                if re.search(r'\b' + re.escape(kw) + r'\b', query_normalized):
                    problem_description = kw_problem
                    break

            # Ưu tiên kiểm tra ID, sau đó Vị trí, sau đó Tên
            # ID: thường là chuỗi chữ hoa/số/dấu gạch ngang (ví dụ A001A, ITEM_123)
            if re.fullmatch(r'[a-z0-9-]+', temp_query_cleaned):
                reported_id = temp_query_cleaned.upper()
            # Vị trí: thường có dạng "tủ X", "kệ Y", hoặc chỉ "3C", "2B"
            elif re.fullmatch(r'(tủ|kệ|khu)\s*[a-z0-9.-]+', temp_query_cleaned) or re.fullmatch(r'[a-z0-9.-]+', temp_query_cleaned) and len(temp_query_cleaned) <= 3: # Giả định vị trí ngắn
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
                # Nếu không trích xuất được thực thể nào, vẫn báo cáo sự cố nhưng thiếu ngữ cảnh
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

        # --- BỔ SUNG: NHẬN DIỆN Ý ĐỊNH LIỆT KÊ (LIST_BY_...) ---
        # Ý định: Lệnh Liệt kê theo Vị trí (list_by_location)
        # Ví dụ: "liệt kê tủ 3C", "mô tả tủ L", "liệt kê 3C"
        # Pattern: (list_verb) (location_phrase)
        # Location phrase có thể là "tủ 3c", "3c", "khu a", v.v.
        # Sử dụng một regex linh hoạt hơn để bắt phần vị trí và kiểm tra kết thúc chuỗi
        location_list_full_pattern = r"(?:{})\s*((?:tủ|kệ|khu)\s*[a-z0-9.-]+|[a-z0-9.-]+)\s*$".format(self.command_list_verbs_regex)
        match_location_list = re.search(location_list_full_pattern, query_normalized)
        if match_location_list:
            location_entity = match_location_list.group(1).strip()
            if location_entity: # Đảm bảo trích xuất được entity
                print(f"DEBUG NLP: MATCHED List By Location. Entity: '{location_entity}'")
                return {"intent": "list_by_location", "location_query": location_entity, "original_query": original_query_text}
            
        # Ý định: Lệnh Liệt kê theo Loại (list_by_type)
        # Ví dụ: "liệt kê hóa chất", "mô tả vật tư"
        # Pattern: (list_verb) (item_type_keywords)
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
            # Loại bỏ tất cả các từ khóa lệnh và các từ dừng chung
            cleaned_query = self._remove_keywords(query_normalized, 
                                                  self.command_search_verbs_list + 
                                                  self.command_location_phrases_list + 
                                                  self.command_quantity_phrases_list + 
                                                  self.command_status_phrases_list + 
                                                  self.command_list_verbs_list + # Bổ sung list verbs vào đây
                                                  self.general_stopwords_list) # Và các từ dừng chung
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
            return {"intent": "search_item", "query": query_normalized, "original_query": original_query_text} # Nếu chỉ gõ "hóa chất"

        # --- Ý định chung (Fallback cuối cùng) ---
        print(f"DEBUG NLP: Rơi vào General Search Fallback.")
        all_command_keywords = list(set(
            self.command_search_verbs_list + self.command_location_phrases_list +
            self.command_quantity_phrases_list + self.command_status_phrases_list +
            self.general_stopwords_list + self.command_guidance_phrases_list + 
            self.upload_log_command_phrases_list + 
            self.problem_keywords_list + self.unit_words_list +
            self.item_type_keywords_list + 
            self.command_list_verbs_list # Bổ sung list verbs vào đây
        ))

        cleaned_query_for_general_search = self._remove_keywords(query_normalized, all_command_keywords)

        if not cleaned_query_for_general_search:
            return {"intent": "search_item", "query": "", "original_query": original_query_text}

        return {"intent": "search_item", "query": cleaned_query_for_general_search, "original_query": original_query_text}