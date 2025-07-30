# src/nlp_processor_admin.py

# File này được tạo theo yêu cầu để phân tách các module liên quan đến trang Admin.
# Hiện tại, các chức năng tìm kiếm theo ID và cập nhật tracking không cần xử lý NLP hội thoại.
# Nếu trong tương lai có các chức năng admin yêu cầu phân tích ngôn ngữ tự nhiên
# (ví dụ: admin nhập lệnh bằng ngôn ngữ tự nhiên để sửa dữ liệu),
# thì logic NLP cụ thể cho admin có thể được thêm vào đây.

# Các tiện ích chung như remove_accents_and_normalize hiện đã có trong common_utils.py
# và được các module cần thiết import trực tiếp.

# Ví dụ:
# from src.common_utils import remove_accents_and_normalize
# class NLPProcessorAdmin:
#     def process_admin_command(self, command_text):
#         # Logic xử lý lệnh admin bằng ngôn ngữ tự nhiên (nếu có)
#         pass