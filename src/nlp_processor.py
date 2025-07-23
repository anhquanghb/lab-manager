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

        # Ý định: List by Type and Location AND/OR Status (Phức tạp nhất)
        # Ví dụ: "Liệt kê hóa chất đã mở từ tủ 3C" (Type + Status + Location)
        #          "Tìm hóa chất trong tủ 3C" (Type + Location)
        #          "Liệt kê đã mở từ tủ 3C" (Status + Location) -> đã có list_by_location_status

        # Pattern cho Type + Location (ví dụ: "hóa chất trong tủ 3c")
        # Cần đảm bảo rằng các regex không xung đột quá nhiều

        # --- CÁC Ý ĐỊNH KẾT HỢP (ưu tiên cao hơn) ---

        # Ý định: List by Type AND Location (MỚI: "Tìm hóa chất trong tủ 3C", "liệt kê vật tư ở kệ A1")
        match_type_location = re.search(r'(liệt\s+kê|tìm|có)\s+(hóa\s+chất|vật\s+tư|chất)\s+(trong|từ|ở)\s+(tủ|kệ)\s+([a-zA-Z0-9\s]+)', query_lower)
        if match_type_location:
            item_type_raw = match_type_location.group(2)
            location = match_type_location.group(6).strip().upper() # Group 6 là tên vị trí

            item_type = ""
            if "hóa chất" in item_type_raw or "chất" in item_type_raw:
                item_type = "Hóa chất"
            elif "vật tư" in item_type_raw:
                item_type = "Vật tư"

            return {"intent": "list_by_type_location", "type": item_type, "location": location}

        # Ý định: List by Location AND Status (Đã có: "Liệt kê đã mở từ tủ 3C")
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

        # Ý định: List by Type AND Status (Đã có: "Liệt kê Hóa chất đã mở", "tìm vật tư còn nguyên")
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

            # Chỉ trả về list_by_type_status nếu CÓ status được tìm thấy, nếu không, nó sẽ rơi vào list_by_type đơn thuần hoặc tìm kiếm chung
            if status:
                return {"intent": "list_by_type_status", "type": item_type, "status": status}
            elif item_type: # Nếu chỉ có loại mà không có trạng thái cụ thể
                return {"intent": "list_by_type", "type": item_type} # Ý định mới: chỉ lọc theo loại


        # --- CÁC Ý ĐỊNH ĐƠN LẺ (ưu tiên thấp hơn các ý định kết hợp) ---

        # Ý định: Search by ID (Tìm mã A001A, tìm code XYZ)
        match_id = re.search(r'(mã|code)\s+([a-zA-Z0-9-]+)', query_lower)
        if match_id:
            return {"intent": "search_by_id", "id": match_id.group(2).upper()}

        # Ý định: Search by CAS (Tìm CAS 553-24-2, CAS 77-88-9)
        match_cas = re.search(r'(cas|số cas)\s+([0-9-]+)', query_lower)
        if match_cas:
            return {"intent": "search_by_cas", "cas": match_cas.group(2)}

        # Ý định: List by Location (Đơn thuần: "Liệt kê tủ 3C", "tìm trong kệ A1")
        match_location_simple = re.search(r'(liệt\s+kê|tìm|có)\s*(trong|từ|ở)?\s*(tủ|kệ)\s+([a-zA-Z0-9\s]+)', query_lower)
        if match_location_simple:
            return {"intent": "list_by_location", "location": match_location_simple.group(4).strip().upper()}


        # --- Ý định chung ---
        # Fallback: General Search (Nếu không khớp với các ý định cụ thể, coi là tìm kiếm chung)
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