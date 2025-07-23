import re
import nltk
import os

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
        # Các từ khóa liên quan đến số lượng (sẽ loại bỏ khi trích xuất tên vật tư)
        self.quantity_phrases = ["có bao nhiêu", "số lượng", "bao nhiêu"]
        # Các từ chỉ đơn vị (sẽ loại bỏ khi trích xuất tên vật tư)
        self.unit_words = ["chai", "lọ", "thùng", "gói", "hộp", "bình", "cái", "m", "kg", "g", "ml", "l", "đơn vị", "viên", "cuộn"]
        # Các từ dừng chung khi tìm kiếm (sẽ loại bỏ khi tìm kiếm chung)
        self.general_stopwords = ["tìm", "kiếm", "về", "thông tin về", "cho tôi biết về", "hãy tìm", "hỏi về", "của", "là", "?", "vật tư", "hóa chất", "chất"]
        # Các từ khóa tình trạng
        self.status_keywords = ["đã mở", "còn nguyên"]

    def _remove_keywords(self, text, keywords_to_remove):
        """
        Hàm trợ giúp để loại bỏ các từ khóa khỏi chuỗi truy vấn.
        Sử dụng r'\b' để đảm bảo chỉ khớp toàn bộ từ.
        """
        cleaned_text = text
        for kw in keywords_to_remove:
            cleaned_text = re.sub(r'\b' + re.escape(kw) + r'\b', '', cleaned_text, flags=re.IGNORECASE).strip()

        # Loại bỏ các ký tự đặc biệt hoặc khoảng trắng thừa ở đầu/cuối
        cleaned_text = re.sub(r'^\W+|\W+$', '', cleaned_text).strip()
        # Loại bỏ khoảng trắng thừa giữa các từ
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()

        return cleaned_text

    def process_query(self, query):
        """
        Xử lý câu hỏi của người dùng để trích xuất ý định và các thực thể.
        Trả về một dictionary chứa intent và các tham số.
        """
        query_lower = query.lower().strip()

        # --- Nhận diện các ý định cụ thể hơn (Ưu tiên các ý định kết hợp trước) ---

        # Ý định: Get Quantity AND Status (MỚI: "có bao nhiêu chai h2so4 đã mở")
        # Tìm các cụm từ hỏi số lượng + tên vật tư + từ khóa tình trạng
        match_quantity_status = re.search(r'(có\s+bao\s+nhiêu|số\s+lượng|bao\s+nhiêu)\s+(?:' + '|'.join(self.unit_words) + r')?\s*([a-zA-Z0-9\s.-]+?)\s*(' + '|'.join(self.status_keywords) + r')', query_lower)
        if match_quantity_status:
            raw_item_name = match_quantity_status.group(2).strip()
            status_found = match_quantity_status.group(3).strip()

            # Làm sạch tên vật tư/hóa chất: chỉ loại bỏ các từ chỉ đơn vị
            item_name = self._remove_keywords(raw_item_name, self.unit_words)

            # Đảm bảo item_name không rỗng và không phải từ chung chung
            if item_name and "hóa chất" not in item_name and "vật tư" not in item_name:
                return {"intent": "get_quantity_status", "item_name": item_name, "status": status_found}


        # Ý định: List by Type AND Location
        match_type_location = re.search(r'(liệt\s+kê|tìm|có)\s+(hóa\s+chất|vật\s+tư|chất)\s+(trong|từ|ở)\s+(tủ|kệ)\s+([a-zA-Z0-9\s.-]+)', query_lower)
        if match_type_location:
            item_type_raw = match_type_location.group(2)
            location = match_type_location.group(6).strip().upper()

            item_type = ""
            if "hóa chất" in item_type_raw or "chất" in item_type_raw:
                item_type = "Hóa chất"
            elif "vật tư" in item_type_raw:
                item_type = "Vật tư"

            return {"intent": "list_by_type_location", "type": item_type, "location": location}

        # Ý định: List by Location AND Status
        match_loc_status = re.search(r'(liệt\s+kê|tìm|có)\s+(.+)\s+(trong|từ)\s+(tủ|kệ)\s+([a-zA-Z0-9\s.-]+)', query_lower)
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
        match_type_status = re.search(r'(liệt\s+kê|tìm)\s+(hóa\s+chất|vật\s+tư|chất)(?:\s+(.+))?', query_lower)
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

        # Ý định: Get Quantity (CẬP NHẬT: "có bao nhiêu chai H2SO4", "số lượng Axeton")
        # Bắt toàn bộ phần còn lại của câu hỏi sau cụm từ hỏi số lượng
        match_get_quantity = re.search(r'(?:' + '|'.join(self.quantity_phrases) + r')\s+(.+)', query_lower)
        if match_get_quantity:
            raw_item_name = match_get_quantity.group(1).strip() # Lấy toàn bộ phần sau cụm từ hỏi số lượng
            # Làm sạch tên vật tư/hóa chất: chỉ loại bỏ các từ chỉ đơn vị
            item_name = self._remove_keywords(raw_item_name, self.unit_words)

            # Đảm bảo item_name không rỗng sau khi làm sạch và không phải là từ chung chung
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
        match_location_simple = re.search(r'(liệt\s+kê|tìm|có)\s*(trong|từ|ở)?\s*(tủ|kệ)\s+([a-zA-Z0-9\s.-]+)', query_lower)
        if match_location_simple:
            return {"intent": "list_by_location", "location": match_location_simple.group(4).strip().upper()}


        # --- Ý định chung (Fallback cuối cùng) ---
        # Sử dụng tất cả các từ khóa để làm sạch truy vấn tìm kiếm chung
        all_keywords_to_remove = self.general_stopwords + self.quantity_phrases + self.unit_words + self.status_keywords
        cleaned_query_for_general_search = self._remove_keywords(query_lower, all_keywords_to_remove)

        # Trả về ý định tìm kiếm chung với truy vấn đã được làm sạch.
        # Nếu cleaned_query_for_general_search rỗng (ví dụ: người dùng chỉ gõ "tìm"),
        # thì vẫn giữ nguyên query_lower ban đầu để ChatbotLogic có thể xử lý lỗi "nhập từ khóa cụ thể hơn".
        return {"intent": "search_item", "query": cleaned_query_for_general_search if cleaned_query_for_general_search else query_lower}