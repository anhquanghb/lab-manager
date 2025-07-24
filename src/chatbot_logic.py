import pandas as pd
from src.database_manager import DatabaseManager
from src.nlp_processor import NLPProcessor
import re
import os
import json

class ChatbotLogic:
    LOG_FILE = "chat_log.jsonl"

    def __init__(self):
        self.db_manager = DatabaseManager()
        self.nlp_processor = NLPProcessor()

        if not os.path.exists('logs'):
            os.makedirs('logs')
        self.log_filepath = os.path.join('logs', self.LOG_FILE)

    GUIDANCE_MESSAGE = """
    Chào bạn! Tôi có thể giúp bạn tra cứu vật tư và hóa chất trong phòng thí nghiệm.
    Dưới đây là các loại câu lệnh bạn có thể sử dụng:

    **1. Tìm kiếm chung:**
    - Tìm kiếm theo tên (Tiếng Việt hoặc Tiếng Anh), công thức, hoặc từ khóa trong mô tả.
    - **Cấu trúc:** `[Từ khóa]`, `tìm [Từ khóa]`, `hãy tìm [Từ khóa]`, `tra cứu [Từ khóa]`.
    - **Ví dụ:** `axit sulfuric`, `SULFURIC ACID`, `H2SO4`, `tìm ống nghiệm`.

    **2. Tìm kiếm theo Mã ID:**
    - **Cấu trúc:** `tìm mã [ID]`, `tìm code [ID]`.
    - **Ví dụ:** `tìm mã A001A`, `tìm code HC001`.

    **3. Tìm kiếm theo số CAS:**
    - **Cấu trúc:** `tìm CAS [Số CAS]`, `CAS [Số CAS]`, `số cas [Số CAS]`.
    - **Ví dụ:** `tìm CAS 553-24-2`.

    **4. Liệt kê theo Vị trí:**
    - **Cấu trúc:** `liệt kê tủ [Vị trí]`, `tìm trong tủ [Vị trí]`, `có ở kệ [Vị trí]`.
    - **Ví dụ:** `liệt kê tủ 3C`, `tìm trong kệ A1`.

    **5. Liệt kê theo Loại:**
    - **Cấu trúc:** `liệt kê [Loại]`, `tìm [Loại]`.
    - **Loại được hỗ trợ:** `Hóa chất`, `Vật tư`.
    - **Ví dụ:** `liệt kê Hóa chất`, `tìm Vật tư`.

    **6. Liệt kê theo Loại và Tình trạng:**
    - **Cấu trúc:** `liệt kê [Loại] [Tình trạng]`, `tìm [Loại] [Tình trạng]`.
    - **Tình trạng được hỗ trợ:** `đã mở`, `còn nguyên`.
    - **Ví dụ:** `liệt kê Hóa chất đã mở`, `tìm Vật tư còn nguyên`.

    **7. Liệt kê theo Vị trí và Tình trạng:**
    - **Cấu trúc:** `liệt kê [Tình trạng] từ tủ [Vị trí]`, `tìm [Tình trạng] ở kệ [Vị trí]`.
    - **Ví dụ:** `liệt kê đã mở từ tủ 3C`.

    **8. Liệt kê theo Loại và Vị trí:**
    - **Cấu trúc:** `liệt kê [Loại] trong tủ [Vị trí]`, `tìm [Loại] ở kệ [Vị trí]`.
    - **Ví dụ:** `liệt kê hóa chất trong tủ 3C`.

    **9. Hỏi số lượng:**
    - **Cấu trúc:** `có bao nhiêu [Tên vật tư/hóa chất]`, `số lượng [Tên vật tư/hóa chất]`, `bao nhiêu [Tên vật tư/hóa chất]`.
    - **Ví dụ:** `có bao nhiêu Axeton`.

    **10. Hỏi vị trí:**
    - **Cấu trúc:** `[Tên vật tư/hóa chất] ở đâu`, `vị trí của [Tên vật tư/hóa chất]`.
    - **Ví dụ:** `Ống nghiệm ở đâu`.

    Nếu bạn cần hướng dẫn này bất cứ lúc nào, chỉ cần hỏi "hướng dẫn tìm kiếm" hoặc "cách tìm kiếm".
    """

    def _format_results(self, results, query_context=""):
        """Hàm trợ giúp để định dạng kết quả tìm kiếm và thêm gợi ý hướng dẫn."""
        if results.empty:
            return_message = f"Xin lỗi, tôi không tìm thấy vật tư/hóa chất nào liên quan đến '*{query_context}*'." if query_context else "Xin lỗi, tôi không tìm thấy kết quả nào phù hợp."
            return_message += "\n\nBạn muốn tôi hướng dẫn tìm kiếm không?"
            return return_message

        response = f"Tôi tìm thấy **{len(results)}** kết quả:\n\n"
        for index, row in results.iterrows():
            response += (f"- **{row['name']}** (ID: {row['id']}, Loại: {row['type']})\n"
                         f"  Số lượng: {row['quantity']} {row['unit']}, Vị trí: {row['location']}.\n"
                         f"  Mô tả: {row['description']}\n\n")
        return response.strip()

    def _log_interaction(self, user_query, chatbot_response_text, parsed_query):
        """Ghi lại tương tác của người dùng và phản hồi của chatbot vào file log."""
        log_entry = {
            "timestamp": pd.Timestamp.now().isoformat(),
            "user_query": user_query,
            "chatbot_response": chatbot_response_text,
            "parsed_intent": parsed_query.get("intent"),
            "parsed_entities": {k: v for k, v in parsed_query.items() if k != "intent"}
        }
        try:
            with open(self.log_filepath, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"Lỗi khi ghi log: {e}")


    def get_response(self, user_query):
        parsed_query = self.nlp_processor.process_query(user_query)
        intent = parsed_query.get("intent")

        # --- Xử lý ý định CHÀO HỎI (Ưu tiên cao nhất) ---
        if intent == "greeting":
            final_response = self.GUIDANCE_MESSAGE # Trả về hướng dẫn khi chào hỏi
        # --- Xử lý ý định HƯỚNG DẪN ---
        elif intent == "request_guidance":
            final_response = self.GUIDANCE_MESSAGE
        # --- Xử lý các ý định cụ thể khác ---
        elif intent == "get_quantity_status":
            item_name = parsed_query.get("item_name")
            status = parsed_query.get("status")

            if not item_name or not status:
                final_response = "Bạn muốn hỏi số lượng của vật tư/hóa chất nào với tình trạng ra sao?"
            else:
                matching_items = self.db_manager.search_item(item_name) 

                if not matching_items.empty:
                    filtered_items = matching_items[matching_items['description'].str.lower().str.contains(status.lower(), na=False)]

                    if not filtered_items.empty:
                        total_quantity = filtered_items['quantity'].sum()

                        response_parts = [f"Tôi tìm thấy **{len(filtered_items)}** mục **{item_name.capitalize()}** với tình trạng **{status.capitalize()}**.",
                                          f"Tổng số lượng hiện có là **{total_quantity} đơn vị**.\n\n",
                                          "Chi tiết từng mục:\n"]
                        for index, row in filtered_items.iterrows():
                            response_parts.append(f"- **{row['name']}** (ID: {row['id']}, Loại: {row['type']})\n"
                                                  f"  Số lượng: {row['quantity']} {row['unit']}, Vị trí: {row['location']}.\n"
                                                  f"  Mô tả: {row['description']}\n\n")
                        final_response = "".join(response_parts).strip()
                    else:
                        final_response = self._format_results(pd.DataFrame(), f"{item_name} {status}")
                else:
                    final_response = self._format_results(pd.DataFrame(), item_name)

        elif intent == "list_by_type_location":
            item_type = parsed_query.get("type")
            location = parsed_query.get("location")
            if not item_type or not location:
                final_response = "Bạn muốn tìm hóa chất/vật tư loại gì và ở vị trí nào?"
            else:
                results = self.db_manager.list_by_type_and_location(item_type, location)
                final_response = self._format_results(results, f"loại '{item_type}' trong vị trí '{location}'")

        elif intent == "list_by_location_status":
            location = parsed_query.get("location")
            status = parsed_query.get("status")

            if not location and not status:
                final_response = "Bạn muốn liệt kê vật tư/hóa chất theo vị trí và tình trạng nào?"
            else:
                results = pd.DataFrame()
                query_context_text = ""
                if location and status:
                    results = self.db_manager.list_by_location_and_status(location, status)
                    query_context_text = f"vị trí '{location}' và tình trạng '{status}'"
                elif location:
                    results = self.db_manager.list_by_location(location)
                    query_context_text = f"vị trí '{location}'"
                elif status:
                    results = self.db_manager.list_by_status(status)
                    query_context_text = f"tình trạng '{status}'"

                final_response = self._format_results(results, query_context_text)

        elif intent == "list_by_type_status":
            item_type = parsed_query.get("type")
            status = parsed_query.get("status")

            if not item_type and not status:
                final_response = "Bạn muốn liệt kê hóa chất/vật tư theo loại và tình trạng nào?"
            else:
                results = pd.DataFrame()
                query_context_text = ""
                if item_type and status:
                    results = self.db_manager.list_by_type_and_status(item_type, status)
                    query_context_text = f"loại '{item_type}' và tình trạng '{status}'"

                final_response = self._format_results(results, query_context_text)

        elif intent == "list_by_type":
            item_type = parsed_query.get("type")
            if not item_type:
                final_response = "Bạn muốn liệt kê vật tư/hóa chất theo loại nào?"
            else:
                results = self.db_manager.list_by_type(item_type)
                final_response = self._format_results(results, f"loại '{item_type}'")

        elif intent == "search_by_id":
            item_id = parsed_query.get("id")
            if not item_id:
                final_response = "Bạn muốn tìm vật tư/hóa chất theo mã ID nào?"
            else:
                results = self.db_manager.get_by_id(item_id)
                final_response = self._format_results(results, item_id)

        elif intent == "search_by_cas":
            cas_number = parsed_query.get("cas")
            if not cas_number:
                final_response = "Bạn muốn tìm hóa chất theo số CAS nào?"
            else:
                results = self.db_manager.search_by_cas(cas_number)
                final_response = self._format_results(results, f"CAS {cas_number}")

        elif intent == "list_by_location":
            location = parsed_query.get("location")
            if not location:
                final_response = "Bạn muốn liệt kê vật tư/hóa chất ở vị trí nào?"
            else:
                results = self.db_manager.list_by_location(location)
                final_response = self._format_results(results, f"vị trí '{location}'")

        elif intent == "get_quantity":
            item_name = parsed_query.get("item_name")
            if not item_name:
                final_response = "Bạn muốn hỏi số lượng của vật tư/hóa chất nào?"
            else:
                matching_items = self.db_manager.search_item(item_name) 

                if not matching_items.empty:
                    total_quantity = matching_items['quantity'].sum()

                    response_parts = [f"Tôi tìm thấy **{len(matching_items)}** mục liên quan đến **{item_name.capitalize()}**.",
                                      f"Tổng số lượng hiện có là **{total_quantity} đơn vị**.\n\n",
                                      "Chi tiết từng mục:\n"]
                    for index, row in matching_items.iterrows():
                        response_parts.append(f"- **{row['name']}** (ID: {row['id']}, Loại: {row['type']})\n"
                                              f"  Số lượng: {row['quantity']} {row['unit']}, Vị trí: {row['location']}.\n"
                                              f"  Mô tả: {row['description']}\n\n")
                    final_response = "".join(response_parts).strip()
                else:
                    final_response = self._format_results(pd.DataFrame(), item_name)

        elif intent == "get_location":
            item_name = parsed_query.get("item_name")
            if not item_name:
                final_response = "Bạn muốn hỏi vị trí của vật tư/hóa chất nào?"
            else:
                location = self.db_manager.get_location(item_name)
                if location:
                    final_response = f"**{item_name.capitalize()}** được đặt tại: **{location}**."
                else:
                    final_response = self._format_results(pd.DataFrame(), item_name)

        elif intent == "search_item":
            query_text = parsed_query.get("query")
            if not query_text or len(query_text.strip()) < 2:
                final_response = "Bạn muốn tôi tìm kiếm thông tin gì? Vui lòng nhập từ khóa cụ thể hơn."
            else:
                results = self.db_manager.search_item(query_text)
                final_response = self._format_results(results, query_text)

        else:
            final_response = "Tôi không hiểu yêu cầu của bạn."
            final_response += "\n\nBạn muốn tôi hướng dẫn tìm kiếm không?"

        # Ghi log sau khi xác định được final_response
        self._log_interaction(user_query, final_response, parsed_query)
        return final_response