# src/home_page.py

import streamlit as st

def home_page():
    st.title("🏡 Trang chủ")
    st.markdown("---")
    
    st.header("Chào mừng bạn đến với hệ thống Quản lý Lab!")
    st.write("""
        Đây là nền tảng giúp bạn tra cứu, quản lý và theo dõi các loại vật tư, hóa chất và thiết bị trong phòng thí nghiệm một cách hiệu quả.
        
        Sử dụng thanh điều hướng bên trái để truy cập các chức năng sau:
        - **Chatbot**: Tương tác với trợ lý ảo để tìm kiếm và hỏi đáp nhanh về tồn kho.
        - **Trợ lý AI**: Sử dụng trí tuệ nhân tạo để hỗ trợ các công việc phức tạp hơn.
        - **Quản lý & Thống kê**: Dành cho người dùng có quyền quản trị để cập nhật và theo dõi tồn kho.
    """)
    
    st.markdown("---")
    
    st.subheader("Trạng thái hệ thống")
    st.info("Hệ thống đang hoạt động bình thường. Nếu có bất kỳ vấn đề gì, vui lòng liên hệ bộ phận hỗ trợ.")