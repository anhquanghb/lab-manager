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

        # --- Nhận diện các ý định cụ thể hơn ---

        # Ý định: Search by ID (Tìm mã A001A, tìm code XYZ)
        # Regex tìm kiếm các cụm từ như "mã", "code" theo sau là một chuỗi ký tự (ID)
        match_id = re.search(r'(mã|code)\s+([a-zA-Z0-9-]+)', query_lower)
        if match_id:
            return {"intent": "search_by_id", "id": match_id.group(2).upper()}

        # Ý định: Search by CAS (Tìm CAS 511-89-8, CAS 77-88-9)
        # Regex tìm kiếm "cas" theo sau là một chuỗi số và dấu gạch ngang
        match_cas = re.search(r'(cas|số cas)\s+([0-9-]+)', query_lower)
        if match_cas:
            return {"intent": "search_by_cas", "cas": match_cas.group(2)}

        # Ý định: List by Location (Liệt kê tủ 3C, tìm trong kệ A1)
        # Regex tìm kiếm "liệt kê" hoặc "tìm" theo sau là "trong" hoặc "từ" và "tủ" hoặc "kệ" và tên vị trí
        match_location = re.search(r'(liệt\s+kê|tìm|có)\s+(trong|từ)\s+(tủ|kệ)\s+([a-zA-Z0-9\s]+)', query_lower)
        if match_location:
            return {"intent": "list_by_location", "location": match_location.group(4).strip().upper()}

        # Ý định: List by Type and/or Status (Liệt kê Hóa chất đã mở, tìm vật tư còn nguyên)
        # Regex tìm kiếm "liệt kê" hoặc "tìm" theo sau là loại (hóa chất/vật tư) và có thể là tình trạng
        match_type_status = re.search(r'(liệt\s+kê|tìm)\s+(hóa\s+chất|vật\s+tư|chất)(?:\s+(.+))?', query_lower)
        if match_type_status:
            item_type_raw = match_type_status.group(2)
            status_phrase = match_type_status.group(3) if match_type_status.group(3) else ""

            # Chuẩn hóa loại vật tư
            item_type = ""
            if "hóa chất" in item_type_raw or "chất" in item_type_raw:
                item_type = "Hóa chất"
            elif "vật tư" in item_type_raw:
                item_type = "Vật tư"

            # Trích xuất tình trạng từ cụm từ (có thể cần regex phức tạp hơn cho nhiều trạng thái)
            status = None
            if "đã mở" in status_phrase:
                status = "Đã mở"
            elif "còn nguyên" in status_phrase:
                status = "Còn nguyên"
            # Thêm các trạng thái khác nếu có trong dữ liệu của bạn

            return {"intent": "list_by_type_status", "type": item_type, "status": status}

        # Ý định: List by Location and Status (Liệt kê đã mở từ tủ 3C, tìm còn nguyên ở kệ A1)
        # Regex tìm kiếm "liệt kê" hoặc "tìm" theo sau là tình trạng, rồi "trong/từ", "tủ/kệ", và tên vị trí
        match_loc_status = re.search(r'(liệt\s+kê|tìm|có)\s+(.+)\s+(trong|từ)\s+(tủ|kệ)\s+([a-zA-Z0-9\s]+)', query_lower)
        if match_loc_status:
            status_phrase_full = match_loc_status.group(2).strip()
            location = match_loc_status.group(5).strip().upper()

            status = None
            if "đã mở" in status_phrase_full:
                status = "Đã mở"
            elif "còn nguyên" in status_phrase_full:
                status = "Còn nguyên"
            # Thêm các trạng thái khác

            return {"intent": "list_by_location_status", "location": location, "status": status}


        # --- Ý định chung ---
        # Fallback: General Search (Nếu không khớp với các ý định cụ thể, coi là tìm kiếm chung)
        # Điều này sẽ bắt các câu hỏi như "Tìm NaCl" hoặc "Tìm NEUTRAL RED"
        return {"intent": "search_item", "query": query_lower}

    def _extract_item_name(self, query_lower, keywords_to_remove):
        """
        Hàm trợ giúp này được dùng trong các phiên bản trước cho tìm kiếm chung.
        Hiện tại, các regex ở trên đã cụ thể hơn, nhưng hàm này vẫn có thể được giữ lại
        cho các trường hợp tìm kiếm chung mà không có từ khóa rõ ràng.
        """
        item_name_candidate = query_lower
        for kw in keywords_to_remove:
            item_name_candidate = item_name_candidate.replace(kw, "").strip()

        item_name_candidate = re.sub(r'(của|là|\?|vật tư|hóa chất)$', '', item_name_candidate).strip()
        item_name_candidate = re.sub(r'\s+', ' ', item_name_candidate).strip()
        return item_name_candidate