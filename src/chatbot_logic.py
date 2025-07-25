import pandas as pd
from src.database_manager import DatabaseManager
from src.nlp_processor import NLPProcessor
import re
import os
import json

class ChatbotLogic:
    LOG_FILE = "chat_log.jsonl"
    ISSUE_LOG_DIR = "logs/issues" # Thư mục riêng cho log sự cố
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.nlp_processor = NLPProcessor()
        
        self.logs_base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'logs'))
        if not os.path.exists(self.logs_base_dir):
            os.makedirs(self.logs_base_dir)
        
        self.log_filepath = os.path.join(self.logs_base_dir, self.LOG_FILE)

        # Đảm bảo thư mục logs/issues tồn tại
        if not os.path.exists(self.ISSUE_LOG_DIR):
            os.makedirs(self.ISSUE_LOG_DIR)


    GUIDANCE_MESSAGE = """
    Chào bạn! Tôi có thể giúp bạn tra cứu vật tư và hóa chất trong phòng thí nghiệm.
    Dưới đây là các loại câu lệnh bạn có thể sử dụng:

    **1. Tìm kiếm chung:**
    - Tìm kiếm theo tên (Tiếng Việt hoặc Tiếng Anh), công thức, hoặc từ khóa trong mô tả.
    - **Cấu trúc:** `[Từ khóa]`, `tìm [Từ khóa]`, `hãy tìm [Từ khóa]`, `tra cứu [Từ khóa]`.
    - **Ví dụ:** `axit sulfuric`, `SULFURIC ACID`, `H2SO4`, `tìm ống nghiệm`.

    **2. Hỏi vị trí:**
    - **Cấu trúc:** `[Tên/Mã/CTHH] ở đâu`, `vị trí của [Tên/Mã/CTHH]`, `tìm vị trí [Tên/Mã/CTHH]`.
    - **Ví dụ:** `H2SO4 ở đâu`, `vị trí của NaCl`.

    **3. Hỏi số lượng:**
    - **Cấu trúc:** `có bao nhiêu [Tên/Mã/CTHH]`, `số lượng [Tên/Mã/CTHH]`.
    - **Ví dụ:** `có bao nhiêu Axeton`, `số lượng H2SO4`.

    **4. Hỏi tình trạng:**
    - **Cấu trúc:** `tình trạng [Tên/Mã/Loại]`, `trạng thái [Tên/Mã/Loại]`.
    - **Ví dụ:** `tình trạng Axeton`, `trạng thái Hóa chất đã mở`.

    **5. Báo cáo Tình trạng/Vấn đề:**
    - **Cấu trúc:** `[Tên/Mã/Vị trí] [không thấy/đã hết/hỏng]`, `[không thấy/đã hết/hỏng] [Tên/Mã/Vị trí]`.
    - **Ví dụ:** `Không thấy H2SO4`, `HCl đã hết`, `tủ sấy bị hư hỏng`.

    **6. Các lệnh khác:**
    - Tìm kiếm theo Mã ID: `tìm mã [ID]`.
    - Tìm kiếm theo số CAS: `tìm CAS [Số CAS]`.
    - Liệt kê theo Loại: `liệt kê [Loại]`.
    - Liệt kê theo Loại và Vị trí: `liệt kê [Loại] trong tủ [Vị trí]`.

    Nếu bạn cần hướng dẫn này bất cứ lúc nào, chỉ chỉ cần hỏi "hướng dẫn" hoặc "cách tìm kiếm".
    """

    def _format_results(self, results, query_context=""):
        """Hàm trợ giúp để định dạng kết quả tìm kiếm và thêm gợi ý hướng dẫn."""
        if results.empty:
            return_message = f"Xin lỗi, tôi không tìm thấy vật tư/hóa chất nào liên quan đến '*{query_context}*'." if query_context else "Xin lỗi, tôi không tìm thấy kết quả nào phù hợp."
            return_message += "\n\nHãy thử tìm kiếm bằng công thức hoặc tên tiếng Anh hoặc sử dụng từ khóa khác ngắn hơn. Hãy nói tôi hướng dẫn nếu bạn cần chi tiết hơn."
            return return_message
        
        response = f"Tôi tìm thấy **{len(results)}** kết quả:\n\n"
        for index, row in results.iterrows():
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
        log_dir = self.logs_base_dir
        log_file = self.LOG_FILE
        
        if log_type == "issue":
            log_dir = os.path.join(self.logs_base_dir, "issues") # Thư mục riêng cho issue logs
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            # Tên file cho issue log sẽ là timestamped
            timestamp_str = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            log_file = f"log_issue_{timestamp_str}.jsonl"

        full_log_filepath = os.path.join(log_dir, log_file)

        try:
            # Ghi vào file log chính nếu là chat, ghi vào file timestamped nếu là issue
            mode = 'a' if log_type == 'chat' else 'w' # 'w' cho issue log để tạo file mới mỗi lần
            with open(full_log_filepath, mode, encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"Lỗi khi ghi log ({log_type}): {e}")

    def get_response(self, user_query):
        parsed_query = self.nlp_processor.process_query(user_query)
        intent = parsed_query.get("intent")
        
        # --- Xử lý ý định CHÀO HỎI (Ưu tiên cao nhất) ---
        if intent == "greeting":
            final_response = self.GUIDANCE_MESSAGE
        # --- Xử lý ý định HƯỚNG DẪN ---
        elif intent == "request_guidance":
            final_response = self.GUIDANCE_MESSAGE
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
            
            final_response = f"Phản ánh về {context_info} (vấn đề: '{problem_description}') đã được ghi nhận. Cám ơn bạn đã phản hồi về tình trạng này."
            
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
                location = self.db_manager.get_location(item_name) # Hàm này tìm kiếm chính xác
                if location:
                    final_response = f"**{item_name.capitalize()}** được đặt tại: **{location}**."
                else:
                    # Nếu tìm kiếm chính xác theo tên không ra, thử tìm kiếm rộng hơn
                    results_general = self.db_manager.search_item(item_name)
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
                # get_quantity trong db_manager tìm chính xác, nếu không có, dùng search_item
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
                results = self.db_manager.search_item(item_name)
                if not results.empty:
                    response_parts = [f"Tôi tìm thấy các mục liên quan đến **{item_name.capitalize()}** với tình trạng:\n\n"]
                    for index, row in results.iterrows():
                        response_parts.append(f"- **{row['name']}** (ID: {row['id']}, Vị trí: {row['location']}): {row['description']}\n\n")
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
    ```

---

### File 4: `src/main.py`

File này chứa logic khởi tạo ứng dụng Streamlit và gọi hàm tải log tự động khi khởi động.

```python
import streamlit as st
import sys
import os

# Thêm thư mục gốc của dự án vào Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.chatbot_logic import ChatbotLogic
from src.database_manager import DatabaseManager # Cần import DatabaseManager để gọi hàm upload

# Khởi tạo chatbot logic một lần duy nhất
@st.cache_resource
def get_chatbot_logic():
    # Gọi hàm tải log tự động khi ứng dụng khởi động
    # DatabaseManager cần được khởi tạo trước để có đường dẫn và hàm upload
    db_manager_instance = DatabaseManager() 
    print("Bắt đầu kiểm tra và tải nhật ký tự động khi ứng dụng khởi động...")
    # Sử dụng thuộc tính LOG_FILE từ ChatbotLogic class
    if db_manager_instance.upload_logs_to_github_on_startup(ChatbotLogic.LOG_FILE): 
         print("Tải nhật ký tự động hoàn tất (hoặc không có log để tải).")
    else:
         print("Tải nhật ký tự động thất bại hoặc có lỗi xảy ra.")
    
    return ChatbotLogic() # Trả về instance của ChatbotLogic như cũ

def main():
    st.set_page_config(page_title="Lab AI Chatbot - Duy Tan University", layout="centered")
    st.title("🧪 Lab AI Chatbot - Duy Tan University")
    st.write("Chào bạn! Tôi là trợ lý ảo giúp bạn tra cứu, thống kê vật tư và hóa chất trong phòng thí nghiệm được thiết kế bởi Khoa Môi trường và Khoa học tự nhiên phục vụ công tác nội bộ. Bạn muốn tìm kiếm hóa chất hoặc vật tư? Hãy cho tôi biết! Hoặc nếu bạn muốn tôi hướng dẫn tìm kiếm, hãy gõ Hướng dẫn...")

    chatbot = get_chatbot_logic()

    # Khởi tạo lịch sử chat trong session_state
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Hiển thị các tin nhắn cũ từ lịch sử
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Xử lý input từ người dùng
    if prompt := st.chat_input("Nhập câu hỏi của bạn..."):
        # Thêm tin nhắn người dùng vào lịch sử chat
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Lấy phản hồi từ chatbot
        with st.spinner("Đang xử lý..."):
            response = chatbot.get_response(prompt)
        
        # Thêm tin nhắn của chatbot vào lịch sử chat
        st.session_state.messages.append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.markdown(response)

if __name__ == "__main__":
    main()