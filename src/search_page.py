# src/search_page.py

import streamlit as st
import pandas as pd
from src.database_manager import DatabaseManager

def search_page():
    st.title("🔍 Tra cứu")
    st.markdown("---")
    
    db_manager = DatabaseManager()
    
    if db_manager.inventory_data.empty:
        st.warning("Không có dữ liệu tồn kho để tra cứu.")
        return

    st.write("Nhập từ khóa để tra cứu thông tin chi tiết về vật tư và hóa chất.")
    
    search_query = st.text_input("Tìm kiếm theo tên, mã, công thức hóa học, hoặc từ khóa:", placeholder="Ví dụ: Axit Sulfuric, H2SO4, A001A")
    
    if search_query:
        with st.spinner("Đang tìm kiếm..."):
            results = db_manager.search_item(search_query)
        
        if not results.empty:
            st.subheader(f"Kết quả tìm kiếm cho '{search_query}'")
            st.write(f"Tìm thấy **{len(results)}** mục phù hợp.")
            
            # Hiển thị kết quả dưới dạng bảng
            st.dataframe(results[[
                'id', 'name', 'type', 'quantity', 'unit', 'location', 
                'status', 'tracking', 'description'
            ]])
            
        else:
            st.warning(f"Không tìm thấy kết quả nào phù hợp với '{search_query}'.")
    else:
        st.info("Vui lòng nhập từ khóa để bắt đầu tra cứu.")