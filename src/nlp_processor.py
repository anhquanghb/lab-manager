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

# Đảm bảo định nghĩa class NLPProcessor ở đây
class NLPProcessor: # <--- Dòng này phải có và đúng chính tả
    def __init__(self):
        pass

    def process_query(self, query):
        """
        Xử lý câu hỏi của người dùng để trích xuất ý định và các thực thể.
        Trả về một dictionary chứa intent và các tham số.
        """
        query_lower = query.lower()

        # Ý định tra cứu số lượng
        if "bao nhiêu" in query_lower or "số lượng" in query_lower or "còn mấy" in query_lower:
            item_name = self._extract_item_name(query_lower, ["bao nhiêu", "số lượng", "còn mấy"])
            return {"intent": "get_quantity", "item_name": item_name}

        # Ý định tra cứu vị trí
        if "ở đâu" in query_lower or "vị trí" in query_lower:
            item_name = self._extract_item_name(query_lower, ["ở đâu", "vị trí"])
            return {"intent": "get_location", "item_name": item_name}

        # Ý định tìm kiếm chung
        if "tìm" in query_lower or "có" in query_lower or "tra cứu" in query_lower or "thông tin" in query_lower:
            item_name = self._extract_item_name(query_lower, ["tìm", "có", "tra cứu", "thông tin"])
            return {"intent": "search_item", "query": item_name if item_name else query_lower}

        # Fallback: Nếu không khớp với intent nào, coi là tìm kiếm chung
        return {"intent": "search_item", "query": query_lower}

    def _extract_item_name(self, query_lower, keywords_to_remove):
        """
        Trích xuất tên vật tư/hóa chất từ câu hỏi bằng cách loại bỏ các từ khóa hỏi.
        """
        item_name_candidate = query_lower
        for kw in keywords_to_remove:
            item_name_candidate = item_name_candidate.replace(kw, "").strip()

        # Loại bỏ các từ thừa như "của", "là", "?" ở cuối câu
        item_name_candidate = re.sub(r'(của|là|\?|vật tư|hóa chất)$', '', item_name_candidate).strip()

        # Loại bỏ khoảng trắng thừa
        item_name_candidate = re.sub(r'\s+', ' ', item_name_candidate).strip()

        return item_name_candidate