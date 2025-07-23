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
        pass

    def process_query(self, query):
        """
        Xử lý câu hỏi của người dùng để trích xuất ý định và các thực thể.
        Trả về một dictionary chứa intent và các tham số.
        """
        query_lower = query.lower().strip()

        # --- Nhận diện các ý định cụ thể hơn (Ưu tiên các ý định kết hợp trước) ---

        # Ý định: List by Type AND Location
        match_type_location = re.search(r'(liệt\s+kê|tìm|có)\s+(hóa\s+chất|vật\s+tư|chất)\s+(trong|từ|ở)\s+(tủ|kệ)\s+([a-zA-Z0-9\s]+)', query_lower)
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
        match_loc_status = re.search(r'(liệt\s+kê|tìm|có)\s+(.+)\s+(trong|từ)\s+(tủ|kệ)\s+([a-zA-Z0-9\s]+)', query_lower)
        if match_loc_status:
            status_phrase_full = match_loc_status.group(2).strip()
            location = match_loc_status.group(5).strip().upper()

            status = None
            if "đã mở" in status_phrase_full:
                status = "Đã mở"
            elif "còn nguyên" in status_phrase_full:
                status = "Còn nguyên"

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
            if "đã mở" in status_phrase:
                status = "Đã mở"
            elif "còn nguyên" in status_phrase:
                status = "Còn nguyên"

            if status:
                return {"intent": "list_by_type_status", "type": item_type, "status": status}
            elif item_type:
                return {"intent": "list_by_type", "type": item_type}


        # --- CÁC Ý ĐỊNH ĐƠN LẺ ---

        # Ý định: Search by ID
        match_id = re.search(r'(mã|code)\s+([a-zA-Z0-9-]+)', query_lower)
        if match_id:
            return {"intent": "search_by_id", "id": match_id.group(2).upper()}

        # Ý định: Search by CAS
        match_cas = re.search(r'(cas|số cas)\s+([0-9-]+)', query_lower)
        if match_cas:
            return {"intent": "search_by_cas", "cas": match_cas.group(2)}

        # Ý định: List by Location (Đơn thuần)
        match_location_simple = re.search(r'(liệt\s+kê|tìm|có)\s*(trong|từ|ở)?\s*(tủ|kệ)\s+([a-zA-Z0-9\s]+)', query_lower)
        if match_location_simple:
            return {"intent": "list_by_location", "location": match_location_simple.group(4).strip().upper()}


        # --- Ý định chung (Fallback cuối cùng) ---
        # Đây là nơi chúng ta loại bỏ các từ khóa tìm kiếm chung trước khi gửi truy vấn
        general_search_keywords = ["tìm", "kiếm", "về", "thông tin về", "cho tôi biết về", "hãy tìm", "hỏi về"]
        # Sử dụng _extract_item_name để loại bỏ các từ khóa này
        cleaned_query_for_general_search = self._extract_item_name(query_lower, general_search_keywords)

        # Trả về ý định tìm kiếm chung với truy vấn đã được làm sạch.
        # Nếu cleaned_query_for_general_search rỗng (ví dụ: người dùng chỉ gõ "tìm"),
        # thì vẫn giữ nguyên query_lower ban đầu để ChatbotLogic có thể xử lý lỗi "nhập từ khóa cụ thể hơn".
        return {"intent": "search_item", "query": cleaned_query_for_general_search if cleaned_query_for_general_search else query_lower}

    def _extract_item_name(self, query_lower, keywords_to_remove):
        """
        Hàm trợ giúp để loại bỏ các từ khóa và làm sạch chuỗi truy vấn.
        """
        item_name_candidate = query_lower
        for kw in keywords_to_remove:
            item_name_candidate = item_name_candidate.replace(kw, "").strip()

        # Loại bỏ các từ thừa như "của", "là", "?" ở cuối câu
        item_name_candidate = re.sub(r'(của|là|\?|vật tư|hóa chất)$', '', item_name_candidate).strip()

        # Loại bỏ khoảng trắng thừa
        item_name_candidate = re.sub(r'\s+', ' ', item_name_candidate).strip()

        return item_name_candidate