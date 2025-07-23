import pandas as pd
from src.database_manager import DatabaseManager
from src.nlp_processor import NLPProcessor
from googletrans import Translator
import re

class ChatbotLogic:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.nlp_processor = NLPProcessor()
        self.translator = Translator()

    # Hàm trợ giúp để định dạng kết quả tìm kiếm (hiển thị nhiều mục)
    def _format_results(self, results, query_context=""):
        if results.empty:
            return f"Xin lỗi, tôi không tìm thấy vật tư/hóa chất nào liên quan đến '*{query_context}*'." if query_context else "Xin lỗi, tôi không tìm thấy kết quả nào phù hợp."

        response = f"Tôi tìm thấy **{len(results)}** kết quả:\n\n"
        for index, row in results.iterrows():
            response += (f"- **{row['name']}** (ID: {row['id']}, Loại: {row['type']})\n"
                         f"  Số lượng: {row['quantity']} {row['unit']}, Vị trí: {row['location']}.\n"
                         f"  Mô tả: {row['description']}\n\n")
        return response.strip()

    def _translate_query(self, text, dest_lang='en', src_lang='auto'):
        """Hàm trợ giúp để dịch truy vấn."""
        print(f"DEBUG: Bắt đầu dịch '{text}' từ '{src_lang}' sang '{dest_lang}'") # Dòng debug 1
        try:
            if re.fullmatch(r'[A-Z0-9().-]+', text.upper()):
                print(f"DEBUG: Bỏ qua dịch vì có vẻ là công thức hóa học: {text}") # Dòng debug 2
                return text

            translated = self.translator.translate(text, dest=dest_lang, src=src_lang)
            if translated and translated.text.lower() != text.lower():
                print(f"DEBUG: Dịch thành công: '{text}' -> '{translated.text}'") # Dòng debug 3
                return translated.text
            else:
                print(f"DEBUG: Không dịch (có thể là cùng chuỗi hoặc lỗi): '{text}'") # Dòng debug 4
                return None
        except Exception as e:
            print(f"DEBUG: Lỗi khi dịch '{text}': {e}") # Dòng debug 5
            return None

    def _handle_no_results_fallback(self, original_user_query, specific_intent_query_text):
        """
        Xử lý các trường hợp không có kết quả từ tìm kiếm cụ thể bằng cách thử tìm kiếm dự phòng.
        Giai đoạn 1: Thử tìm kiếm chung.
        Giai đoạn 2: Dịch thuật.
        """
        print(f"DEBUG: _handle_no_results_fallback được gọi. Query gốc: '{original_user_query}', Query cụ thể: '{specific_intent_query_text}'") # Dòng debug 6
        fallback_response = ""

        # GIAI ĐOẠN 1: Thử tìm kiếm chung trên toàn bộ các trường (với truy vấn đã làm sạch)
        print(f"DEBUG: Giai đoạn 1 - Tìm kiếm chung với '{specific_intent_query_text}'") # Dòng debug 7
        general_search_results = self.db_manager.search_item(specific_intent_query_text)
        if not general_search_results.empty:
            print(f"DEBUG: Giai đoạn 1 - Tìm thấy {len(general_search_results)} kết quả chung.") # Dòng debug 8
            fallback_response += f"Tôi không tìm thấy kết quả chính xác cho yêu cầu ban đầu của bạn, nhưng tôi tìm thấy các mục sau khi tìm kiếm chung với từ khóa '*{specific_intent_query_text}*':\n\n"
            fallback_response += self._format_results(general_search_results)
            return fallback_response
        else:
            print("DEBUG: Giai đoạn 1 - Không tìm thấy kết quả chung.") # Dòng debug 9

        # GIAI ĐOẠN 2: Dịch thuật
        print("DEBUG: Giai đoạn 2 - Thử dịch thuật.") # Dòng debug 10
        translated_query = self._translate_query(specific_intent_query_text, dest_lang='en')
        if translated_query and translated_query.lower() != specific_intent_query_text.lower():
            print(f"DEBUG: Giai đoạn 2 - Đã dịch thành: '{translated_query}'. Bắt đầu tìm kiếm.") # Dòng debug 11
            translated_results = self.db_manager.search_item(translated_query)
            if not translated_results.empty:
                print(f"DEBUG: Giai đoạn 2 - Tìm thấy {len(translated_results)} kết quả sau dịch.") # Dòng debug 12
                fallback_response += f"Tôi không tìm thấy bằng tiếng Việt, nhưng tôi tìm thấy các mục sau khi dịch sang tiếng Anh ('*{translated_query}*'):\n\n"
                fallback_response += self._format_results(translated_results)
                return fallback_response
            else:
                print("DEBUG: Giai đoạn 2 - Không tìm thấy kết quả sau dịch.") # Dòng debug 13
        else:
            print("DEBUG: Giai đoạn 2 - Không dịch hoặc dịch không thay đổi chuỗi.") # Dòng debug 14

        return self._format_results(pd.DataFrame(), specific_intent_query_text) # Vẫn không tìm thấy

    def get_response(self, user_query):
        parsed_query = self.nlp_processor.process_query(user_query)
        intent = parsed_query.get("intent")

        # --- Xử lý các ý định cụ thể ---

        if intent == "get_quantity_status": # Xử lý ý định mới: Số lượng VÀ Tình trạng
            item_name = parsed_query.get("item_name")
            status = parsed_query.get("status")

            if not item_name or not status:
                return "Bạn muốn hỏi số lượng của vật tư/hóa chất nào với tình trạng ra sao?"

            # Lấy tất cả các mục liên quan đến tên
            # Đây là một điểm yếu nếu db_manager.get_item_details_for_summary không có.
            # Cần thay bằng search_item hoặc một hàm hợp lệ. Tạm thời dùng search_item để tránh lỗi.
            matching_items = self.db_manager.search_item(item_name) # Sửa từ get_item_details_for_summary

            if not matching_items.empty:
                # Lọc thêm theo tình trạng trong mô tả
                filtered_items = matching_items[matching_items['description'].str.lower().str.contains(status.lower(), na=False)]

                if not filtered_items.empty:
                    total_quantity = filtered_items['quantity'].sum()

                    response = f"Tôi tìm thấy **{len(filtered_items)}** mục **{item_name.capitalize()}** với tình trạng **{status.capitalize()}**.\n"
                    response += f"Tổng số lượng hiện có là **{total_quantity} đơn vị**.\n\n"
                    response += "Chi tiết từng mục:\n"

                    for index, row in filtered_items.iterrows():
                        response += (f"- **{row['name']}** (ID: {row['id']}, Loại: {row['type']})\n"
                                     f"  Số lượng: {row['quantity']} {row['unit']}, Vị trí: {row['location']}.\n"
                                     f"  Mô tả: {row['description']}\n\n")
                    return response.strip()
                else:
                    return self._handle_no_results_fallback(user_query, f"{item_name} {status}")
            else:
                return self._handle_no_results_fallback(user_query, item_name) # Nếu không tìm thấy tên ban đầu

        elif intent == "list_by_type_location":
            item_type = parsed_query.get("type")
            location = parsed_query.get("location")
            if not item_type or not location:
                return "Bạn muốn tìm hóa chất/vật tư loại gì và ở vị trí nào?"
            results = self.db_manager.list_by_type_and_location(item_type, location)
            if results.empty:
                return self._handle_no_results_fallback(user_query, f"{item_type} {location}")
            return self._format_results(results, f"loại '{item_type}' trong vị trí '{location}'")

        elif intent == "list_by_location_status":
            location = parsed_query.get("location")
            status = parsed_query.get("status")

            if not location and not status:
                return "Bạn muốn liệt kê vật tư/hóa chất theo vị trí và tình trạng nào?"

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

            if results.empty:
                return self._handle_no_results_fallback(user_query, query_context_text)
            return self._format_results(results, query_context_text)

        elif intent == "list_by_type_status":
            item_type = parsed_query.get("type")
            status = parsed_query.get("status")

            if not item_type and not status:
                return "Bạn muốn liệt kê hóa chất/vật tư theo loại và tình trạng nào?"

            results = pd.DataFrame()
            query_context_text = ""
            if item_type and status:
                results = self.db_manager.list_by_type_and_status(item_type, status)
                query_context_text = f"loại '{item_type}' và tình trạng '{status}'"

            if results.empty:
                return self._handle_no_results_fallback(user_query, query_context_text)
            return self._format_results(results, query_context_text)

        elif intent == "list_by_type":
            item_type = parsed_query.get("type")
            if not item_type:
                return "Bạn muốn liệt kê vật tư/hóa chất theo loại nào?"
            results = self.db_manager.list_by_type(item_type)
            if results.empty:
                return self._handle_no_results_fallback(user_query, f"loại '{item_type}'")
            return self._format_results(results, f"loại '{item_type}'")

        elif intent == "search_by_id":
            item_id = parsed_query.get("id")
            if not item_id:
                return "Bạn muốn tìm vật tư/hóa chất theo mã ID nào?"

            results = self.db_manager.get_by_id(item_id)
            if results.empty:
                return self._handle_no_results_fallback(user_query, item_id)
            return self._format_results(results, item_id)

        elif intent == "search_by_cas":
            cas_number = parsed_query.get("cas")
            if not cas_number:
                return "Bạn muốn tìm hóa chất theo số CAS nào?"

            results = self.db_manager.search_by_cas(cas_number)
            if results.empty:
                return self._handle_no_results_fallback(user_query, cas_number)
            return self._format_results(results, f"CAS {cas_number}")

        elif intent == "list_by_location":
            location = parsed_query.get("location")
            if not location:
                return "Bạn muốn liệt kê vật tư/hóa chất ở vị trí nào?"

            results = self.db_manager.list_by_location(location)
            if results.empty:
                return self._handle_no_results_fallback(user_query, location)
            return self._format_results(results, f"vị trí '{location}'")

        elif intent == "get_quantity":
            item_name = parsed_query.get("item_name")
            if not item_name:
                return "Bạn muốn hỏi số lượng của vật tư/hóa chất nào?"

            # Sửa lỗi: Hàm db_manager.get_item_details_for_summary không tồn tại, dùng search_item thay thế.
            matching_items = self.db_manager.search_item(item_name) 

            if not matching_items.empty:
                # Lọc thêm theo tình trạng trong mô tả
                # Logic này nên được thực hiện ở nlp_processor hoặc db_manager.
                # Để đơn giản, giả định rằng get_quantity chỉ hỏi tổng số lượng theo tên.
                # Nếu cần kết hợp số lượng và trạng thái, cần xử lý trong intent get_quantity_status.
                total_quantity = matching_items['quantity'].sum()

                response = f"Tôi tìm thấy **{len(matching_items)}** mục liên quan đến **{item_name.capitalize()}**.\n"
                response += f"Tổng số lượng hiện có là **{total_quantity} đơn vị**.\n\n"
                response += "Chi tiết từng mục:\n"

                for index, row in matching_items.iterrows():
                    response += (f"- **{row['name']}** (ID: {row['id']}, Loại: {row['type']})\n"
                                 f"  Số lượng: {row['quantity']} {row['unit']}, Vị trí: {row['location']}.\n"
                                 f"  Mô tả: {row['description']}\n\n")
                return response.strip()
            else:
                return self._handle_no_results_fallback(user_query, item_name)

        elif intent == "get_location":
            item_name = parsed_query.get("item_name")
            if not item_name:
                return "Bạn muốn hỏi vị trí của vật tư/hóa chất nào?"
            location = self.db_manager.get_location(item_name) # get_location là hàm cũ, tìm theo tên chính xác
            if location:
                return f"**{item_name.capitalize()}** được đặt tại: **{location}**."
            else:
                return self._handle_no_results_fallback(user_query, item_name)

        elif intent == "search_item":
            query_text = parsed_query.get("query")
            if not query_text or len(query_text.strip()) < 2:
                return "Bạn muốn tôi tìm kiếm thông tin gì? Vui lòng nhập từ khóa cụ thể hơn."

            results = self.db_manager.search_item(query_text)
            if results.empty:
                return self._handle_no_results_fallback(user_query, query_text)
            return self._format_results(results, query_text)

        else:
            return "Tôi không hiểu yêu cầu của bạn. Bạn có thể hỏi về số lượng, vị trí, tìm kiếm một vật tư/hóa chất cụ thể (theo tên, ID, CAS), hoặc liệt kê theo vị trí, loại, tình trạng hoặc kết hợp chúng."