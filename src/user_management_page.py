# src/user_management_page.py
import streamlit as st
import pandas as pd
from src.user_manager import UserManager

def user_management_page(user_manager: UserManager):
    st.title("👨‍💻 Quản lý người dùng & Phân quyền")
    
    st.markdown("---")
    st.subheader("Danh sách người dùng hiện có")
    
    users_df = user_manager.get_all_users_as_df()
    if users_df.empty:
        st.info("Chưa có người dùng nào được thêm.")
    else:
        st.dataframe(users_df)
    
    st.markdown("---")
    st.subheader("Thêm/Cập nhật vai trò người dùng")
    
    with st.form("add_update_user_form"):
        email = st.text_input("Email người dùng:")
        role = st.selectbox("Chọn vai trò:", options=["administrator", "moderator", "user", "registered"])
        submit_button = st.form_submit_button("Lưu")
        
        if submit_button:
            if user_manager.add_or_update_user(email.strip().lower(), role):
                st.success(f"Đã lưu người dùng {email} với vai trò {role}.")
                st.rerun()
            else:
                st.error("Lỗi khi lưu người dùng.")
                
    st.markdown("---")
    st.subheader("Xóa người dùng")
    
    with st.form("delete_user_form"):
        user_to_delete = st.selectbox("Chọn email để xóa:", options=[""] + users_df['email'].tolist())
        delete_button = st.form_submit_button("Xóa")
        
        if delete_button and user_to_delete:
            if user_manager.delete_user(user_to_delete):
                st.success(f"Đã xóa người dùng {user_to_delete}.")
                st.rerun()
            else:
                st.error("Lỗi khi xóa người dùng.")