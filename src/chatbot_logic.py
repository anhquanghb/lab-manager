from src.database_manager import DatabaseManager
from src.nlp_processor import NLPProcessor

class ChatbotLogic:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.nlp_processor = NLPProcessor()

    def get_response(self, user_query):
        """
        Nhận câu hỏi từ người dùng và trả về phản hồi của chatbot.
        """
        parsed_query = self.nlp_processor.process_query(user_query)
        intent = parsed_query.get("intent")

        if intent == "get_quantity":
            item_name = parsed_query.get("item_name")
            if not item_name:
                return "Bạn muốn hỏi số lượng của vật tư/hóa chất nào?"

            qty, unit = self.db_manager.get_quantity(item_name)
            if qty is not None:
                return f"Số lượng **{item_name.capitalize()}** hiện có là **{qty} {unit}**."
            else:
                # Thử tìm kiếm rộng hơn nếu không tìm thấy chính xác
                search_results = self.db_manager.search_item(item_name)
                if not search_results.empty:
                    return f"Tôi không tìm thấy số lượng chính xác cho '{item_name}'. Bạn có thể đang muốn hỏi về **{search_results.iloc[0]['name']}**?"
                return f"Không tìm thấy thông tin số lượng cho '**{item_name}**'. Vui lòng kiểm tra lại tên."

        elif intent == "get_location":
            item_name = parsed_query.get("item_name")
            if not item_name:
                return "Bạn muốn hỏi vị trí của vật tư/hóa chất nào?"

            location = self.db_manager.get_location(item_name)
            if location:
                return f"**{item_name.capitalize()}** được đặt tại: **{location}**."
            else:
                # Thử tìm kiếm rộng hơn
                search_results = self.db_manager.search_item(item_name)
                if not search_results.empty:
                    return f"Tôi không tìm thấy vị trí chính xác cho '{item_name}'. Bạn có thể đang muốn hỏi về **{search_results.iloc[0]['name']}**?"
                return f"Không tìm thấy thông tin vị trí cho '**{item_name}**'. Vui lòng kiểm tra lại tên."

        elif intent == "search_item":
            query_text = parsed_query.get("query")
            if not query_text or len(query_text.strip()) < 2: # Ít nhất 2 ký tự để tìm kiếm
                return "Bạn muốn tôi tìm kiếm thông tin gì? Vui lòng nhập từ khóa cụ thể hơn."

            results = self.db_manager.search_item(query_text)
            if not results.empty:
                response = f"Tôi tìm thấy **{len(results)}** kết quả liên quan đến '*{query_text}*':\n\n"
                for index, row in results.iterrows():
                    response += (f"- **{row['name']}** ({row['type']}), số lượng: {row['quantity']} {row['unit']}, "
                                 f"vị trí: {row['location']}. Mô tả: {row['description']}\n")
                return response
            else:
                return f"Xin lỗi, tôi không tìm thấy vật tư/hóa chất nào liên quan đến '**{query_text}**'. Bạn có muốn thử từ khóa khác không?"

        else:
            return "Tôi không hiểu yêu cầu của bạn. Bạn có thể hỏi về số lượng, vị trí hoặc tìm kiếm một vật tư/hóa chất cụ thể (ví dụ: 'số lượng Axeton', 'ống nghiệm ở đâu', 'tìm bình tam giác')."