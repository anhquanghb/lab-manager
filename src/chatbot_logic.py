import pandas as pd # Cần import pandas vì bây giờ dùng pd.DataFrame() trực tiếp
from src.database_manager import DatabaseManager
from src.nlp_processor import NLPProcessor

class ChatbotLogic:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.nlp_processor = NLPProcessor()

    # Hàm trợ giúp để định dạng kết quả tìm kiếm (hiển thị nhiều mục)
    # Đây là một phương thức của lớp ChatbotLogic, nên có thể gọi bằng self._format_results
    def _format_results(self, results, query_text=""):
        if results.empty:
            return f"Xin lỗi, tôi không tìm thấy vật tư/hóa chất nào liên quan đến '*{query_text}*'." if query_text else "Xin lỗi, tôi không tìm thấy kết quả nào phù hợp."

        response = f"Tôi tìm thấy **{len(results)}** kết quả:\n\n"
        for index, row in results.iterrows():
            response += (f"- **{row['name']}** (ID: {row['id']}, Loại: {row['type']})\n"
                         f"  Số lượng: {row['quantity']} {row['unit']}, Vị trí: {row['location']}.\n"
                         f"  Mô tả: {row['description']}\n\n")
        return response.strip() # Loại bỏ dòng trống cuối cùng

    def get_response(self, user_query):
        """
        Nhận câu hỏi từ người dùng và trả về phản hồi của chatbot dựa trên ý định.
        """
        parsed_query = self.nlp_processor.process_query(user_query)
        intent = parsed_query.get("intent")

        # --- Xử lý các ý định cụ thể ---

        if intent == "list_by_type_location": # Ý định MỚI
            item_type = parsed_query.get("type")
            location = parsed_query.get("location")
            if not item_type or not location:
                return "Bạn muốn tìm hóa chất/vật tư loại gì và ở vị trí nào?"
            results = self.db_manager.list_by_type_and_location(item_type, location)
            return self._format_results(results, f"loại '{item_type}' trong vị trí '{location}'")

        elif intent == "list_by_location_status": # Ý định ĐÃ CÓ
            location = parsed_query.get("location")
            status = parsed_query.get("status")

            if not location and not status:
                return "Bạn muốn liệt kê vật tư/hóa chất theo vị trí và tình trạng nào?"

            if location and status:
                results = self.db_manager.list_by_location_and_status(location, status)
                return self._format_results(results, f"vị trí '{location}' và tình trạng '{status}'")
            elif location: # Chỉ có vị trí (dùng hàm đơn lẻ nếu thiếu status)
                results = self.db_manager.list_by_location(location)
                return self._format_results(results, f"vị trí '{location}'")
            elif status: # Chỉ có tình trạng (tìm trên toàn bộ CSDL nếu thiếu vị trí)
                results = self.db_manager.list_by_status(status)
                return self._format_results(results, f"tình trạng '{status}'")

            return "Tôi không hiểu yêu cầu liệt kê theo vị trí và tình trạng này."

        elif intent == "list_by_type_status": # Ý định ĐÃ CÓ (khi có cả type và status)
            item_type = parsed_query.get("type")
            status = parsed_query.get("status")

            if not item_type and not status:
                return "Bạn muốn liệt kê hóa chất/vật tư theo loại và tình trạng nào?"

            if item_type and status:
                results = self.db_manager.list_by_type_and_status(item_type, status)
                return self._format_results(results, f"loại '{item_type}' và tình trạng '{status}'")

            return "Tôi không hiểu yêu cầu liệt kê theo loại và tình trạng này."

        elif intent == "list_by_type": # Ý định MỚI (chỉ loại, không trạng thái)
            item_type = parsed_query.get("type")
            if not item_type:
                return "Bạn muốn liệt kê vật tư/hóa chất theo loại nào?"
            results = self.db_manager.list_by_type(item_type)
            return self._format_results(results, f"loại '{item_type}'")

        elif intent == "search_by_id": # Ý định ĐÃ CÓ
            item_id = parsed_query.get("id")
            if not item_id:
                return "Bạn muốn tìm vật tư/hóa chất theo mã ID nào?"

            results = self.db_manager.get_by_id(item_id)
            return self._format_results(results, item_id)

        elif intent == "search_by_cas": # Ý định ĐÃ CÓ
            cas_number = parsed_query.get("cas")
            if not cas_number:
                return "Bạn muốn tìm hóa chất theo số CAS nào?"

            results = self.db_manager.search_by_cas(cas_number)
            return self._format_results(results, f"CAS {cas_number}")

        elif intent == "list_by_location": # Ý định ĐÃ CÓ
            location = parsed_query.get("location")
            if not location:
                return "Bạn muốn liệt kê vật tư/hóa chất ở vị trí nào?"

            results = self.db_manager.list_by_location(location)
            return self._format_results(results, f"vị trí '{location}'")

        # --- Xử lý các ý định chung (fallback) ---

        elif intent == "get_quantity": # Hàm cũ (tìm số lượng theo tên)
            item_name = parsed_query.get("item_name")
            if not item_name:
                return "Bạn muốn hỏi số lượng của vật tư/hóa chất nào?"
            qty, unit = self.db_manager.get_quantity(item_name)
            if qty is not None:
                return f"Số lượng **{item_name.capitalize()}** hiện có là **{qty} {unit}**."
            else:
                search_results = self.db_manager.search_item(item_name)
                if not search_results.empty:
                    return self._format_results(search_results, f"có thể liên quan đến '{item_name}'") # Sử dụng _format_results
                return f"Không tìm thấy thông tin số lượng cho '**{item_name}**'. Vui lòng kiểm tra lại tên."

        elif intent == "get_location": # Hàm cũ (tìm vị trí theo tên)
            item_name = parsed_query.get("item_name")
            if not item_name:
                return "Bạn muốn hỏi vị trí của vật tư/hóa chất nào?"
            location = self.db_manager.get_location(item_name)
            if location:
                return f"**{item_name.capitalize()}** được đặt tại: **{location}**."
            else:
                search_results = self.db_manager.search_item(item_name)
                if not search_results.empty:
                    return self._format_results(search_results, f"có thể liên quan đến '{item_name}'") # Sử dụng _format_results
                return f"Không tìm thấy thông tin vị trí cho '**{item_name}**'. Vui lòng kiểm tra lại tên."

        elif intent == "search_item": # Hàm tìm kiếm chung (fallback)
            query_text = parsed_query.get("query")
            if not query_text or len(query_text.strip()) < 2:
                return "Bạn muốn tôi tìm kiếm thông tin gì? Vui lòng nhập từ khóa cụ thể hơn."

            results = self.db_manager.search_item(query_text)
            return self._format_results(results, query_text)

        else:
            return "Tôi không hiểu yêu cầu của bạn. Bạn có thể hỏi về số lượng, vị trí, tìm kiếm một vật tư/hóa chất cụ thể (theo tên, ID, CAS), hoặc liệt kê theo vị trí, loại, tình trạng hoặc kết hợp chúng."