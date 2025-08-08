# src/auth.py

import streamlit as st
from streamlit_oauth import OAuth2Component
import jwt # <-- Thư viện mới để giải mã token

# Lấy thông tin từ Streamlit secrets
CLIENT_ID = st.secrets.get("GOOGLE_CLIENT_ID")
CLIENT_SECRET = st.secrets.get("GOOGLE_CLIENT_SECRET")
AUTHORIZE_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
REVOKE_ENDPOINT = "https://oauth2.googleapis.com/revoke"

def initialize_oauth_component():
    """Khởi tạo component OAuth2."""
    if not all([CLIENT_ID, CLIENT_SECRET]):
        st.error("Lỗi cấu hình: Vui lòng cung cấp GOOGLE_CLIENT_ID và GOOGLE_CLIENT_SECRET trong secrets.")
        return None
    
    return OAuth2Component(
        CLIENT_ID,
        CLIENT_SECRET,
        AUTHORIZE_ENDPOINT,
        TOKEN_ENDPOINT,
        TOKEN_ENDPOINT,
        REVOKE_ENDPOINT
    )

oauth2 = initialize_oauth_component()

def get_user_info():
    """Hàm chính xử lý toàn bộ logic đăng nhập."""
    if not oauth2:
        return None

    if 'token' in st.session_state:
        token = st.session_state['token']
        id_token = token.get('id_token')
        
        # --- THAY ĐỔI LỚN Ở ĐÂY ---
        # Kiểm tra và giải mã id_token để lấy thông tin người dùng
        if id_token:
            try:
                # Giải mã id_token. 
                # Bỏ qua bước xác thực chữ ký vì chúng ta nhận token trực tiếp 
                # từ Google qua kênh bảo mật.
                user_info = jwt.decode(id_token, options={"verify_signature": False})
                st.session_state.user_info = user_info
                return user_info
            except Exception as e:
                st.error(f"Lỗi khi giải mã token: {e}")
                return None
        # --- KẾT THÚC THAY ĐỔI ---

    # Nếu chưa có token, hiển thị nút đăng nhập
    result = oauth2.authorize_button(
        name="Đăng nhập bằng Google",
        icon="https://www.google.com/favicon.ico",
        redirect_uri="https://dtu-lab-manager.streamlit.app",
        scope="openid email profile",
        key="google_login"
    )

    if result and "token" in result:
        st.session_state.token = result.get('token')
        st.rerun()
    
    return None

def logout():
    """Xóa thông tin phiên đăng nhập."""
    keys_to_clear = ["token", "user_info", "user_role"]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    #st.rerun()