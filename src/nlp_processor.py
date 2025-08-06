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
        def _remove_accents_and_normalize(input_str):
            if not isinstance(input_str, str):
                return str(input_str)
            nfkd_form = unicodedata.normalize('NFKD', input_str)
            only_ascii = nfkd_form.encode('ascii', 'ignore').decode('utf-8')
            return only_ascii.lower()

        # CÁC TỪ KHÓA LỆNH CHÍNH (Xác định INTENT)
        self.command_search_verbs_list = _remove_accents_and_normalize("tìm, hãy tìm, tra cứu, kiếm, thông tin về, hỏi về, tìm mã, tìm CAS").split(', ')
        self.command_location_phrases_list = _remove_accents_and_normalize("ở đâu, vị trí của").split(', ')
        self.command_quantity_phrases_list = _remove_accents_and_normalize("số lượng, có bao nhiêu, bao nhiêu, còn bao nhiêu, số, lượng, còn lại, còn").split(', ')
        self.command_status_phrases_list = _remove_accents_and_normalize("tình trạng, trạng thái").split(', ')
        self.command_api_guidance_phrases_list = _remove_accents_and_normalize("tạo api, cách tạo api, lấy api key, xin api, api gemini").split(', ')
        self.command_guidance_phrases_list = _remove_accents_and_normalize("hướng dẫn, giúp tôi tìm kiếm, cách tìm kiếm, cách hỏi, chỉ dẫn, tôi không hiểu, bạn có thể hướng dẫn không, xin chào, chào, hello, hi, hey, giúp tôi").split(', ')
        self.upload_log_command_phrases_list = _remove_accents_and_normalize("tải nhật ký, xuất log, lịch sử chat, tải log, đẩy log").split(', ')
        self.command_list_verbs_list = _remove_accents_and_normalize("liệt kê, mô tả").split(', ')
        self.report_command_keywords_list = _remove_accents_and_normalize("báo cáo").split(', ')

        # CÁC TỪ KHÓA GIÁ TRỊ/THUỘC TÍNH
        self.item_type_keywords_list = _remove_accents_and_normalize("vật tư, hóa chất, thiết bị").split(', ')
        self.specific_status_values_list = _remove_accents_and_normalize("đã mở, còn nguyên, đã sử dụng, hết hạn, còn hạn, còn, hết, đang sử dụng, sử dụng, đang mượn, thất lạc, huỷ, không xác định").split(', ')
        self.problem_keywords_list = _remove_accents_and_normalize("không thấy, đã hết, không còn, hỏng, bị hỏng, thiếu, bị mất, bị thất lạc, bị lỗi, lỗi, vấn đề, sự cố").split(', ')
        self.unit_words_list = _remove_accents_and_normalize("chai, lọ, thùng, gói, hộp, bình, cái, m, kg, g, ml, l, đơn vị, viên, cuộn, cục, bịch").split(', ')

        # Các từ dừng chung khác
        self.general_stopwords_list = _remove_accents_and_normalize("về, thông tin về, cho tôi biết về, hỏi về, của, là, ?, và, có, có thể, làm thế nào, bạn muốn, bạn cần, bạn có biết, bạn có thể cho tôi biết, các, này, trong, tủ, phòng").split(', ')

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
        self.report_command_regex = _list_to_regex_pattern(self.report_command_keywords_list)
        
        # BỔ SUNG: REGEX CHO TỪ KHÓA TẠO API
        self.api_guidance_regex = _list_to_regex_pattern(self.command_api_guidance_phrases_list)


    def _remove_keywords(self, text, keywords_to_remove_list):
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

        # --- Nhận diện Ý định HƯỚNG DẪN và CHÀO HỎI (Ưu tiên cao nhất) ---
        if any(re.search(r'\b' + re.escape(kw) + r'\b', query_normalized) for kw in self.command_guidance_phrases_list):
            print(f"DEBUG NLP: MATCHED Guidance/Greeting.")
            return {"intent": "request_guidance", "original_query": original_query_text}

        # --- BỔ SUNG: Nhận diện Ý định HƯỚNG DẪN TẠO API (Ưu tiên cao) ---
        if re.search(self.api_guidance_regex, query_normalized):
            print(f"DEBUG NLP: MATCHED API Guidance.")
            return {"intent": "request_api_guidance", "original_query": original_query_text}

        # --- Nhận diện Ý định TẢI LOG LÊN GITHUB ---
        if any(re.search(r'\b' + re.escape(kw) + r'\b', query_normalized) for kw in self.upload_log_command_phrases_list):
            print(f"DEBUG NLP: MATCHED Upload Log.")
            return {"intent": "upload_logs_to_github", "original_query": original_query_text}

        # ... (Phần còn lại của hàm process_query giữ nguyên, từ phần xử lý Báo cáo Sự cố trở đi) ...

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
            self.report_command_keywords_list +
            self.command_api_guidance_phrases_list # Bổ sung từ khóa API vào đây
        ))

        cleaned_query_for_general_search = self._remove_keywords(query_normalized, all_command_keywords)

        if not cleaned_query_for_general_search:
            return {"intent": "search_item", "query": "", "original_query": original_query_text}

        return {"intent": "search_item", "query": cleaned_query_for_general_search, "original_query": original_query_text}