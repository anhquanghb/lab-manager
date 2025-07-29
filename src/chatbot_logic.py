import pandas as pd
from src.database_manager import DatabaseManager
from src.nlp_processor import NLPProcessor
import json # Được sử dụng cho json.dumps trong _log_interaction
from pathlib import Path # Được sử dụng để xử lý đường dẫn

class ChatbotLogic:
    LOG_FILE = "chat_log.jsonl"
    ISSUE_LOG_DIR_NAME = "issues" # Sử dụng tên thư mục nhất quán

    def __init__(self):
        self.db_manager = DatabaseManager()
        self.nlp_processor = NLPProcessor()

        # Sử dụng pathlib để xử lý đường dẫn nhất quán
        project_root = Path(__file__).parent.parent # Đi tới thư mục gốc của dự án
        self.logs_base_dir = project_root / 'logs'
        self.logs_base_dir.mkdir(parents=True, exist_ok=True) # Đảm bảo thư mục logs cơ sở tồn tại

        self.log_filepath = self.logs_base_dir / self.LOG_FILE # Sử dụng đối tượng Path cho đường dẫn file log chính

        # Đảm bảo thư mục logs/issues tồn tại
        (self.logs_base_dir / self.ISSUE_LOG_DIR_NAME).mkdir(parents=True, exist_ok=True) # Sử dụng đối tượng Path


    GUIDANCE_MESSAGE = """
    Chào bạn! Tôi có thể giúp bạn tra cứu vật tư và hóa chất trong phòng thí nghiệm.
    Dưới đây là các loại câu lệnh bạn có thể sử dụng:

    **1. Tìm kiếm chung:**
    - Tìm kiếm theo tên (Tiếng Việt hoặc Tiếng Anh), công thức, hoặc từ khóa trong mô tả.
    - **Cấu trúc:** `[Từ khóa]`, `tìm [Từ khóa]`, `hãy tìm [Từ khóa]`, `tra cứu [Từ khóa]`.
    - **Ví dụ:** `axit sulfuric`, `SULFURIC ACID`, `H2SO4`, `tìm ống nghiệm`.

    **2. Hỏi vị trí:**
    - **Cấu trúc:** `[Tên/Mã/CTHH] ở đâu`, `vị trí của [Tên/Mã/CTHH]`.
    - **Ví dụ:** `H2SO4 ở đâu`, `vị trí của NaCl`.

    **3. Báo cáo Tình trạng/Vấn đề:**
    - **Cấu trúc:** `[Tên/Mã/Vị trí] [không thấy/đã hết/hỏng]`, `[không thấy/đã hết/hỏng] [Tên/Mã/Vị trí]`.
    - **Ví dụ:** `Không thấy H2SO4`, `HCl đã hết`, `tủ sấy bị hư hỏng`.

    **4. Các lệnh khác:**
    - Tìm kiếm theo Mã ID: `tìm mã [ID]`.
    - Tìm kiếm theo số CAS: `tìm CAS [Số SỐ]`.
    - Liệt kê theo Loại: `liệt kê [Loại]`.
    - Liệt kê theo Loại và Vị trí: `liệt kê [Loại] trong tủ [Vị trí]`.
    Nếu bạn cần hướng dẫn này bất cứ lúc nào, chỉ chỉ cần hỏi "hướng dẫn" hoặc "cách tìm kiếm".
    """

    def _format_results(self, results, query_context=""):
        """Hàm trợ giúp để định dạng kết quả tìm kiếm và thêm gợi ý hướng dẫn."""
        if results.empty:
            return_message = f"Xin lỗi, tôi không tìm thấy vật tư/hóa chất nào liên quan đến '*{query_context}*'." if query_context else "Xin lỗi, tôi không tìm thấy kết quả nào phù hợp."
            return_message += "\n\nHãy thử tìm kiếm bằng công thức hoặc tên tiếng Anh hoặc sử dụng từ khóa khác ngắn hơn.\nHãy nói tôi hướng dẫn nếu bạn cần chi tiết hơn."
            return return_message

        response = f"Tôi tìm thấy **{len(results)}** kết quả:\n\n"
        for index, row in results.iterrows():
            # Sử dụng trường 'description' đã được convert_data.py tạo ra để hiển thị tổng hợp
            response += (f"- **{row['name']}** (ID: {row['id']}, Loại: {row['type']})\n"
                         f"  Số lượng: {row['quantity']} {row['unit']}, Vị trí: {row['location']}.\n"
                         f"  Mô tả: {row['description']}\n\n")
        return response.strip()

    def _log_interaction(self, user_query, chatbot_response_text, parsed_query, log_type="chat"):
        """
        Ghi lại tương tác của người dùng và phản hồi của chatbot vào file log.
        log_type: "chat" hoặc "issue"
        """
        log_entry = {
            "timestamp": pd.Timestamp.now().isoformat(),
            "user_query": user_query,
            "chatbot_response": chatbot_response_text,
            "parsed_intent": parsed_query.get("intent"),
            "parsed_entities": {k: v for k, v in parsed_query.items() if k != "intent"}
        }
        
        full_log_filepath = self.log_filepath # Đây đã là đối tượng Path

        if log_type == "issue":
            issue_log_dir = self.logs_base_dir / self.ISSUE_LOG_DIR_NAME # Đây là đối tượng Path
            issue_log_dir.mkdir(parents=True, exist_ok=True) # Đảm bảo thư mục tồn tại
            
            timestamp_str = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S_%f") # Thêm microsecond để đảm bảo duy nhất
            log_file_name = f"log_issue_{timestamp_str}.jsonl"
            full_log_filepath = issue_log_dir / log_file_name # Đối tượng Path cho file log sự cố

        try:
            # Luôn sử dụng chế độ 'a' (append) để thêm dòng mới vào file
            with open(full_log_filepath, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"Lỗi khi ghi log ({log_type}): {e}")

    def get_response(self, user_query):
        parsed_query = self.nlp_processor.process_query(user_query)
        intent = parsed_query.get("intent")

        # --- Xử lý ý định CHÀO HỎI / HƯỚNG DẪN (Ưu tiên cao nhất) ---
        if intent == "request_guidance": # Tên ý định đã thay đổi trong nlp_processor
            final_response = self.GUIDANCE_MESSAGE
        # --- Xử lý ý định TẢI LOG LÊN GITHUB ---
        elif intent == "upload_logs_to_github": # Tên ý định đã thay đổi trong nlp_processor
            # Logic tải log tự động khi khởi động đã được xử lý trong main.py
            # Ở đây, chỉ cần đưa ra thông báo về tính năng này.
            final_response = "Tính năng tải nhật ký lên GitHub được xử lý tự động khi ứng dụng khởi động. Vui lòng kiểm tra kho lưu trữ của bạn."
            # Nếu bạn muốn kích hoạt tải log thủ công TẠI ĐÂY, hãy uncomment đoạn code dưới:
            # upload_success = self.db_manager.upload_logs_to_github_on_startup(self.log_filepath)
            # if upload_success:
            #     final_response = "Yêu cầu tải nhật ký lên GitHub đã được xử lý. Vui lòng kiểm tra kho lưu trữ của bạn."
            # else:
            #     final_response = "Có lỗi xảy ra khi cố gắng tải nhật ký lên GitHub. Vui lòng kiểm tra log ứng dụng."


        # --- Xử lý ý định BÁO CÁO TÌNH TRẠNG/VẤN ĐỀ (report_issue) ---
        elif intent == "report_issue":
            reported_id = parsed_query.get("reported_id")
            reported_item_name = parsed_query.get("reported_item_name")
            reported_location = parsed_query.get("reported_location")
            problem_description = parsed_query.get("problem_description")

            context_info = ""
            if reported_id:
                context_info = f"mã ID '{reported_id}'"
            elif reported_item_name:
                context_info = f"vật tư/hóa chất '{reported_item_name}'"
            elif reported_location:
                context_info = f"vị trí '{reported_location}'"
            else:
                context_info = "một vật tư/hóa chất/vị trí không xác định" # Fallback nếu không trích xuất được gì

            final_response = f"Phản ánh về {context_info} (vấn đề: '{problem_description}') đã được ghi nhận.\nCám ơn bạn đã phản hồi về tình trạng này."

            # Ghi log riêng cho sự cố
            self._log_interaction(user_query, final_response, parsed_query, log_type="issue")
            return final_response # Trả lời ngay và không ghi log chung ở cuối hàm

        # --- Xử lý các ý định DỰA TRÊN TỪ KHÓA LỆNH (được nhận diện bởi nlp_processor mới) ---

        # Ý định: Lệnh Vị trí (get_location)
        elif intent == "get_location":
            item_name = parsed_query.get("item_name")
            if not item_name:
                final_response = "Bạn muốn hỏi vị trí của vật tư/hóa chất nào?"
            else:
                location = self.db_manager.get_location(item_name) # Hàm này sử dụng cột đã normalized
                if location:
                    final_response = f"**{item_name.capitalize()}** được đặt tại: **{location}**."
                else:
                    # Nếu tìm kiếm chính xác theo tên không ra, thử tìm kiếm rộng hơn
                    results_general = self.db_manager.search_item(item_name) # Hàm này tìm kiếm trên nhiều cột
                    if not results_general.empty:
                        # Nếu tìm kiếm rộng hơn có kết quả, trả về chi tiết các mục đó
                        final_response = self._format_results(results_general, f"có thể liên quan đến '{item_name}' (và vị trí)")
                    else:
                        final_response = self._format_results(pd.DataFrame(), item_name) # Không tìm thấy, gợi ý hướng dẫn

        # Ý định: Lệnh Thống kê/Số lượng (get_quantity)
        elif intent == "get_quantity":
            item_name = parsed_query.get("item_name")
            if not item_name:
                final_response = "Bạn muốn hỏi số lượng của vật tư/hóa chất nào?"
            else:
                # get_quantity trong db_manager tìm chính xác trên các cột đã normalized
                qty, unit = self.db_manager.get_quantity(item_name)
                if qty is not None:
                    final_response = f"Số lượng **{item_name.capitalize()}** hiện có là **{qty} {unit}**."
                else:
                    results_general = self.db_manager.search_item(item_name)
                    if not results_general.empty:
                        final_response = self._format_results(results_general, f"có thể liên quan đến '{item_name}' (và số lượng)")
                    else:
                        final_response = self._format_results(pd.DataFrame(), item_name)

        # Ý định: Lệnh Tình trạng (get_status)
        elif intent == "get_status":
            item_name = parsed_query.get("item_name")
            if not item_name:
                final_response = "Bạn muốn hỏi tình trạng của vật tư/hóa chất nào?"
            else:
                # Lấy tất cả các mục liên quan đến tên để hiển thị tình trạng
                # search_item sẽ tìm trên các cột đã chuẩn hóa
                results = self.db_manager.search_item(item_name)
                if not results.empty:
                    response_parts = [f"Tôi tìm thấy các mục liên quan đến **{item_name.capitalize()}** với tình trạng:\n\n"]
                    for index, row in results.iterrows():
                        # Sử dụng trường 'status' đã chuẩn hóa, hoặc 'description' để hiển thị chi tiết
                        status_display = row.get('status', 'không xác định').capitalize() # Sử dụng trường 'status' mới và viết hoa chữ cái đầu
                        response_parts.append(f"- **{row['name']}** (ID: {row['id']}, Vị trí: {row['location']}): Tình trạng: **{status_display}**.\n  Mô tả chi tiết: {row['description']}\n\n")
                    final_response = "".join(response_parts).strip()
                else:
                    final_response = self._format_results(pd.DataFrame(), item_name)

        # Ý định: Lệnh Tìm kiếm (search_item) - Cho các từ khóa lệnh tìm kiếm chung
        elif intent == "search_item": # Đây là intent cho các câu hỏi bắt đầu bằng "tìm", "tra cứu"
            query_text = parsed_query.get("query")
            if not query_text or len(query_text.strip()) < 2:
                final_response = "Bạn muốn tôi tìm kiếm thông tin gì? Vui lòng nhập từ khóa cụ thể hơn."
            else:
                results = self.db_manager.search_item(query_text)
                final_response = self._format_results(results, query_text)
        
        # --- Fallback cho các ý định phức tạp hơn hoặc không khớp ---
        else:
            final_response = "Tôi không hiểu yêu cầu của bạn."
            final_response += "\n\nBạn muốn tôi hướng dẫn tìm kiếm không?"

        # Ghi log chung (chỉ cho loại "chat")
        self._log_interaction(user_query, final_response, parsed_query, log_type="chat")
        return final_response