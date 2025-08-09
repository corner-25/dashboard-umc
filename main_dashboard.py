#!/usr/bin/env python3
"""
Dashboard Tổng Hợp Phòng Hành Chính - UMC
Gộp tất cả các dashboard phụ vào một giao diện chung
"""

import streamlit as st
import pandas as pd
import os
import base64
from datetime import datetime
import hashlib
import importlib.util
import sys
from pathlib import Path

# Page config
st.set_page_config(
    page_title="Dashboard Phòng Hành chính - UMC",
    page_icon="./assets/logo.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS tùy chỉnh
st.markdown("""
<style>
    .main-header {
        background: #ffffff;
        padding: 2rem;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 2rem;
        color: #0066CC;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .main-title {
        font-size: 2.5rem;
        font-weight: bold;
        color: #0066CC;
        margin-bottom: 0.5rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    .main-subtitle {
        font-size: 1.2rem;
        opacity: 0.9;
        color: #0066CC;
        margin: 0;
    }
    
    .login-container {
        max-width: 400px;
        margin: 2rem auto;
        padding: 2rem;
        background: #f8f9fa;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* BUTTON TO HƠN - MÀU Y TẾ */
    .stButton > button {
        height: 80px !important;
        font-size: 1.2rem !important;
        font-weight: bold !important;
        border-radius: 15px !important;
        border: none !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2) !important;
        transition: all 0.3s ease !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-3px) !important;
        box-shadow: 0 6px 20px rgba(0,0,0,0.3) !important;
    }
    
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #5dade2 0%, #3498db 100%) !important;
        color: white !important;
    }
    
    /* BUTTON ĐĂNG XUẤT ĐỎ NHỎ */
    button[data-testid*="logout_btn"] {
        height: 40px !important;
        font-size: 0.9rem !important;
        font-weight: normal !important;
        border-radius: 8px !important;
        margin: 5px 0 !important;
        padding: 8px 16px !important;
        background: #e74c3c !important;
        color: white !important;
        box-shadow: 0 2px 8px rgba(231, 76, 60, 0.3) !important;
    }
    
    .stButton > button:not([kind="primary"]) {
        height: 40px !important;
        font-size: 0.9rem !important;
        font-weight: normal !important;
        border-radius: 8px !important;
        margin: 5px 0 !important;
        padding: 8px 16px !important;
        background: #e74c3c !important;
        color: white !important;
        box-shadow: 0 2px 8px rgba(231, 76, 60, 0.3) !important;
    }
    
    /* BUTTON DASHBOARD CHÍNH TO TO */
    button[data-testid*="dashboard_admin_main"],
    button[data-testid*="dashboard_fleet_main"], 
    button[data-testid*="dashboard_umc_main"] {
        height: 120px !important;
        font-size: 1.8rem !important;
        font-weight: bold !important;
        border-radius: 20px !important;
        margin: 15px 0 !important;
        padding: 20px !important;
    }
    
    /* DỰ PHÒNG - TARGET TẤT CẢ BUTTON TRONG COLUMNS */
    .main .block-container .stColumn .stButton > button[kind="primary"] {
        height: 120px !important;
        font-size: 1.8rem !important;
        font-weight: bold !important;
        border-radius: 20px !important;
        margin: 15px 0 !important;
        padding: 20px !important;
    }
    
    /* MÀU RIÊNG CHO TỪNG DASHBOARD */
    button[data-testid*="dashboard_admin_main"] {
        background: linear-gradient(135deg, #4e73df 0%, #224abe 100%) !important;
    }
    
    button[data-testid*="dashboard_fleet_main"] {
        background: linear-gradient(135deg, #1cc88a 0%, #17a2b8 100%) !important;
    }
    
    button[data-testid*="dashboard_umc_main"] {
        background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%) !important;
    }
    
    .dashboard-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 15px;
        margin: 1rem 0;
        text-align: center;
        cursor: pointer;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .dashboard-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.2);
    }
    
    .dashboard-card.fleet {
        background: linear-gradient(135deg, #1cc88a 0%, #17a2b8 100%);
    }
    
    .dashboard-card.admin {
        background: linear-gradient(135deg, #4e73df 0%, #224abe 100%);
    }
    
    .dashboard-card.umc {
        background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
    }
    
    .card-icon {
        font-size: 3rem;
        margin-bottom: 1rem;
        display: block;
    }
    
    .card-title {
        font-size: 1.5rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }
    
    .card-description {
        font-size: 1rem;
        opacity: 0.9;
        line-height: 1.4;
    }
    
    .status-indicator {
        display: inline-block;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        margin-right: 8px;
    }
    
    .status-online { background-color: #28a745; }
    .status-offline { background-color: #dc3545; }
    
    .user-info {
        background: #e9ecef;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    
    .logout-button {
        background-color: #dc3545;
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 5px;
        cursor: pointer;
        float: right;
    }
    
    .feature-list {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    .feature-item {
        display: flex;
        align-items: center;
        margin-bottom: 0.8rem;
        padding: 0.5rem;
        background: white;
        border-radius: 5px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    .feature-icon {
        margin-right: 12px;
        font-size: 1.2rem;
    }
    
    .dashboard-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
        gap: 1.5rem;
        margin: 2rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Thông tin xác thực
CREDENTIALS = {
    "phonghc.umc": "hanhchinh1"
}

def hash_password(password):
    """Hash mật khẩu để bảo mật"""
    return hashlib.sha256(password.encode()).hexdigest()

def check_authentication():
    """Kiểm tra xác thực người dùng"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if 'username' not in st.session_state:
        st.session_state.username = ""
    
    return st.session_state.authenticated

def login_page():
    """Trang đăng nhập"""
    # Header
    create_header()
    
    # Login form
    st.markdown("<div class='login-container'>", unsafe_allow_html=True)
    
    st.markdown("### 🔐 Đăng nhập hệ thống")
    st.markdown("*Vui lòng đăng nhập để truy cập dashboard*")
    
    with st.form("login_form"):
        username = st.text_input(
            "👤 Tài khoản:",
            placeholder="Nhập tài khoản..."
        )
        
        password = st.text_input(
            "🔑 Mật khẩu:",
            type="password",
            placeholder="Nhập mật khẩu..."
        )
        
        submitted = st.form_submit_button("🚀 Đăng nhập", use_container_width=True)
        
        if submitted:
            if username in CREDENTIALS and CREDENTIALS[username] == password:
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.login_time = datetime.now()
                st.success("✅ Đăng nhập thành công!")
                st.rerun()
            else:
                st.error("❌ Tài khoản hoặc mật khẩu không đúng!")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Thông tin hệ thống
    with st.expander("ℹ️ Thông tin hệ thống", expanded=False):
        st.markdown("""
        **🏥 Dashboard Phòng Hành Chính UMC**
        
        **🎯 Chức năng:**
        - 📊 Dashboard số liệu hành chính
        - 🚗 Dashboard quản lý tổ xe
        - 🏥 Dashboard UMC Multi-Department
        - 📈 Báo cáo và phân tích dữ liệu
        - 💾 Xuất báo cáo Excel/CSV
        
        **🔧 Hỗ trợ kỹ thuật:**
        - Email: quang.dh@umc.edu.vn
        - Email cá nhân: huuquang.data@gmail.com
        - SĐT cá nhân: 0789 106 201
        
                Phát triển bởi Dương Hữu Quang - Chuyên viên Hành chính Tổng hợp, Phòng Hành chính, Bệnh viện Đại học Y Dược TP. Hồ Chí Minh
                    
        **📅 Phiên bản:** 1.0.0
        
        **📅 Ngày phát hành:** 01/08/2025

        **📁 Tài liệu:** github.com/corner-25
        

        """)

def create_header():
    """Tạo header cho trang chính"""
    # Thử load logo
    logo_base64 = ""
    try:
        script_dir = Path(__file__).parent
        logo_paths = [
            script_dir / "logo.png",
            script_dir / "assets" / "logo.png"
        ]
        
        for logo_path in logo_paths:
            if logo_path.exists():
                with open(logo_path, "rb") as f:
                    logo_base64 = base64.b64encode(f.read()).decode()
                break
    except:
        pass
    
    # Tạo header
    if logo_base64:
        logo_html = f'<img src="data:image/png;base64,{logo_base64}" style="height:120px; width:auto; margin-right:20px;" />'
    else:
        logo_html = '<div style="font-size:4rem; margin-right:20px;">🏥</div>'
    
    header_html = f"""
    <div class='main-header'>
        <div style='display:flex; align-items:center; justify-content:center;'>
            {logo_html}
            <div>
                <div class='main-title'>Dashboard Phòng Hành Chính</div>
                <div class='main-subtitle'>Bệnh viện Đại học Y Dược TP. Hồ Chí Minh</div>
            </div>
        </div>
    </div>
    """
    
    st.markdown(header_html, unsafe_allow_html=True)

def dashboard_selection_page():
    """Trang chọn dashboard"""
    create_header()
    
    # Thông tin người dùng
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown(f"""
        <div class='user-info'>
            <span class='status-indicator status-online'></span>
            <strong>Xin chào, {st.session_state.username}!</strong><br>
            <small>Đăng nhập lúc: {st.session_state.login_time.strftime('%d/%m/%Y %H:%M:%S')}</small>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        if st.button("🚪 Đăng xuất", use_container_width=True, key="logout_btn"):
            for key in ['authenticated', 'username', 'login_time', 'selected_dashboard']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    
    # Menu chọn dashboard - BUTTON ĐƠN GIẢN
    st.markdown("## 📊 Chọn Dashboard")
    st.markdown("*Chọn dashboard bạn muốn sử dụng:*")
    
    # CSS ĐẶC BIỆT CHỈ CHỞ BUTTON NÀY
    st.markdown("""
    <style>
    /* ÉP BUTTON DASHBOARD TO TO */
    div[data-testid="column"] button[kind="primary"] {
        height: 150px !important;
        font-size: 2rem !important;
        font-weight: bold !important;
        border-radius: 25px !important;
        margin: 20px 0 !important;
        padding: 25px !important;
        box-shadow: 0 8px 25px rgba(0,0,0,0.3) !important;
    }
    
    /* MÀU Y TẾ CHO DASHBOARD */
    div[data-testid="column"]:nth-child(1) button[kind="primary"] {
        background: linear-gradient(135deg, #5dade2 0%, #3498db 100%) !important;
        color: white !important;
    }
    
    div[data-testid="column"]:nth-child(2) button[kind="primary"] {
        background: linear-gradient(135deg, #58d68d 0%, #27ae60 100%) !important;
        color: white !important;
    }
    
    div[data-testid="column"]:nth-child(3) button[kind="primary"] {
        background: linear-gradient(135deg, #bb8fce 0%, #8e44ad 100%) !important;
        color: white !important;
    }
    
    /* BUTTON ĐĂNG XUẤT NHỎ LẠI */
    .stButton button:not([kind="primary"]) {
        height: 40px !important;
        font-size: 0.9rem !important;
        border-radius: 8px !important;
        margin: 5px 0 !important;
        padding: 8px 16px !important;
        background: #e74c3c !important;
        color: white !important;
        box-shadow: 0 2px 8px rgba(231, 76, 60, 0.3) !important;
    }
    
    /* ĐẢM BẢO BUTTON ĐĂNG XUẤT KHÔNG BỊ ẢNH HƯỞNG */
    .stButton button[data-testid*="logout"] {
        height: 40px !important;
        font-size: 0.9rem !important;
        font-weight: normal !important;
        border-radius: 8px !important;
        margin: 5px 0 !important;
        padding: 8px 16px !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📋 Dashboard Hành Chính", 
                    use_container_width=True, 
                    type="primary",
                    key="dashboard_admin_main"):
            st.session_state.selected_dashboard = "admin"
            st.rerun()
    
    with col2:
        if st.button("🚗 Dashboard Tổ Xe", 
                    use_container_width=True, 
                    type="primary",
                    key="dashboard_fleet_main"):
            st.session_state.selected_dashboard = "fleet"
            st.rerun()
    
    with col3:
        if st.button("🏥 Dashboard UMC Multi", 
                    use_container_width=True, 
                    type="primary",
                    key="dashboard_umc_main"):
            st.session_state.selected_dashboard = "umc"
            st.rerun()
    
    # Thống kê hệ thống
    st.markdown("---")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="👤 Người dùng online",
            value="1",
            help="Số người đang sử dụng hệ thống"
        )
    
    with col2:
        st.metric(
            label="📊 Dashboard khả dụng",
            value="3",
            help="Số dashboard đang hoạt động"
        )
    
    with col3:
        st.metric(
            label="⏱️ Thời gian hoạt động",
            value="24/7",
            help="Hệ thống hoạt động liên tục"
        )
    
    with col4:
        st.metric(
            label="🔄 Cập nhật cuối",
            value="Hôm nay",
            help="Lần cập nhật dữ liệu gần nhất"
        )
    
    # MÔ TẢ CHI TIẾT Ở DƯỚI
    st.markdown("## 📋 Mô tả chi tiết các Dashboard")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class='feature-list'>
            <h4>📋 Dashboard Hành Chính</h4>
            <div class='feature-item'>
                <span class='feature-icon'>📊</span>
                <span>Pivot table với 13 danh mục ưu tiên</span>
            </div>
            <div class='feature-item'>
                <span class='feature-icon'>📈</span>
                <span>Biến động tuần (%) hiển thị inline</span>
            </div>
            <div class='feature-item'>
                <span class='feature-icon'>🔍</span>
                <span>Sparkline xu hướng chi tiết</span>
            </div>
            <div class='feature-item'>
                <span class='feature-icon'>💾</span>
                <span>Xuất Excel đa sheet</span>
            </div>
            <div class='feature-item'>
                <span class='feature-icon'>☁️</span>
                <span>Sync tự động với GitHub</span>
            </div>
            <div class='feature-item'>
                <span class='feature-icon'>📄</span>
                <span>Quản lý văn bản đến/đi</span>
            </div>
            <div class='feature-item'>
                <span class='feature-icon'>🎉</span>
                <span>Sự kiện và lễ tân</span>
            </div>
            <div class='feature-item'>
                <span class='feature-icon'>📞</span>
                <span>Tổng đài và khách VIP</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class='feature-list'>
            <h4>🚗 Dashboard Tổ Xe</h4>
            <div class='feature-item'>
                <span class='feature-icon'>🚛</span>
                <span>Theo dõi realtime các chuyến xe</span>
            </div>
            <div class='feature-item'>
                <span class='feature-icon'>⛽</span>
                <span>Phân tích tiêu thụ nhiên liệu</span>
            </div>
            <div class='feature-item'>
                <span class='feature-icon'>👨‍💼</span>
                <span>Đánh giá hiệu suất tài xế</span>
            </div>
            <div class='feature-item'>
                <span class='feature-icon'>💰</span>
                <span>Báo cáo doanh thu chi tiết</span>
            </div>
            <div class='feature-item'>
                <span class='feature-icon'>📱</span>
                <span>Giao diện responsive mobile</span>
            </div>
            <div class='feature-item'>
                <span class='feature-icon'>🛣️</span>
                <span>Quản lý lộ trình và khoảng cách</span>
            </div>
            <div class='feature-item'>
                <span class='feature-icon'>🔧</span>
                <span>Theo dõi bảo dưỡng định kỳ</span>
            </div>
            <div class='feature-item'>
                <span class='feature-icon'>📊</span>
                <span>Phân tích chi phí vận hành</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class='feature-list'>
            <h4>🏥 Dashboard UMC Multi</h4>
            <div class='feature-item'>
                <span class='feature-icon'>🔧</span>
                <span>7 phòng ban tích hợp</span>
            </div>
            <div class='feature-item'>
                <span class='feature-icon'>📊</span>
                <span>Báo cáo 6 tháng chi tiết</span>
            </div>
            <div class='feature-item'>
                <span class='feature-icon'>📈</span>
                <span>Biểu đồ đa dạng & tương tác</span>
            </div>
            <div class='feature-item'>
                <span class='feature-icon'>💻</span>
                <span>Giao diện thân thiện</span>
            </div>
            <div class='feature-item'>
                <span class='feature-icon'>🎯</span>
                <span>KPI theo dõi hiệu quả</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

def run_admin_dashboard():
    """Chạy dashboard hành chính"""
    try:
        # Kiểm tra file tồn tại
        if not os.path.exists("dash_phonghc.py"):
            st.error("❌ Không tìm thấy file dash_phonghc.py")
            st.info("📁 Files hiện có:")
            for f in os.listdir("."):
                if f.endswith(".py"):
                    st.write(f"- {f}")
            back_to_menu()
            return
        
        # Import và chạy dashboard hành chính
        import importlib.util
        
        # Thử load module dash_phonghc
        spec = importlib.util.spec_from_file_location("dash_phonghc", "dash_phonghc.py")
        if spec and spec.loader:
            dash_phonghc = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(dash_phonghc)
            
            # Kiểm tra function main
            if hasattr(dash_phonghc, 'main'):
                # Chạy main function
                dash_phonghc.main()
            else:
                st.error("❌ Không tìm thấy function main() trong dash_phonghc.py")
                st.info("💡 Hãy đảm bảo file có function main()")
                back_to_menu()
        else:
            st.error("❌ Không thể tạo spec cho dash_phonghc.py")
            back_to_menu()
            
    except Exception as e:
        st.error(f"❌ Lỗi khi tải Dashboard Hành Chính:")
        st.code(str(e))
        st.info("💡 Có thể do thiếu secrets hoặc lỗi import")
        back_to_menu()

def run_fleet_dashboard():
    """Chạy dashboard tổ xe - FIXED"""
    try:
        # FIXED: Set bypass flag trước khi import
        st.session_state['authenticated'] = True
        st.session_state['skip_child_login'] = True
        
        # FIXED: Import trực tiếp thay vì dùng importlib
        if "dashboard-to-xe" not in sys.modules:
            # Add current directory to Python path
            current_dir = os.path.dirname(os.path.abspath(__file__))
            if current_dir not in sys.path:
                sys.path.insert(0, current_dir)
        
        # FIXED: Đổi tên file để tránh dấu gạch ngang
        import dashboard_to_xe as fleet_module
        
        # Chạy main function
        if hasattr(fleet_module, 'main'):
            fleet_module.main()
        else:
            st.error("❌ Không tìm thấy function main()")
            back_to_menu()
            
    except Exception as e:
        st.error(f"❌ Lỗi khi tải Dashboard Tổ Xe: {str(e)}")
        back_to_menu()

def run_umc_dashboard():
    """Chạy dashboard UMC Multi-Department"""
    try:
        # Kiểm tra file tồn tại
        if not os.path.exists("dash-umc.py"):
            st.error("❌ Không tìm thấy file dash-umc.py")
            st.info("📁 Files hiện có:")
            for f in os.listdir("."):
                if f.endswith(".py"):
                    st.write(f"- {f}")
            back_to_menu()
            return
        
        # Import và chạy dashboard UMC
        import importlib.util
        
        # Thử load module dash-umc.py
        spec = importlib.util.spec_from_file_location("dash-umc", "dash-umc.py")
        if spec and spec.loader:            
            dash_umc = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(dash_umc)
            
            # Dashboard UMC không cần function main, chỉ cần chạy
            # Vì nó đã có đầy đủ code Streamlit
            
        else:
            st.error("❌ Không thể tạo spec cho dash-umc.py")
            back_to_menu()
            
    except Exception as e:
        st.error(f"❌ Lỗi khi tải Dashboard UMC:")
        st.code(str(e))
        st.info("💡 Có thể do thiếu thư viện hoặc lỗi import")
        st.info("💡 Đảm bảo đã cài đặt: plotly, pandas, numpy")
        back_to_menu()

def back_to_menu():
    """Quay lại menu chính"""
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col2:
        if st.button("🏠 Quay lại Menu chính", use_container_width=True):
            if 'selected_dashboard' in st.session_state:
                del st.session_state['selected_dashboard']
            st.rerun()

def main():
    """Hàm main của dashboard tổng hợp"""

    # Điều hướng nhanh nếu người dùng nhấp thẳng vào thẻ dashboard
    query_params = st.query_params
    nav_value = query_params.get('nav')
    if nav_value:
        nav_target = nav_value[0] if isinstance(nav_value, list) else nav_value
        if nav_target in ('admin', 'fleet', 'umc'):
            st.session_state.selected_dashboard = nav_target
            # Xóa query param để tránh lặp vô hạn
            st.query_params.clear()

    # Kiểm tra xác thực
    if not check_authentication():
        login_page()
        return

    # Kiểm tra dashboard được chọn
    if 'selected_dashboard' not in st.session_state:
        dashboard_selection_page()
        return

    # Sidebar navigation
    with st.sidebar:
        # Sidebar‑specific CSS to isolate its buttons from global styles
        st.markdown("""
        <style>
        /* RESET and customize only sidebar buttons */
        div[data-testid="stSidebar"] .stButton > button {
            height: 40px !important;
            font-size: 0.9rem !important;
            font-weight: normal !important;
            border-radius: 8px !important;
            margin: 6px 0 !important;
            padding: 6px 14px !important;
            box-shadow: none !important;
            background: #f0f2f6 !important;
            color: #333 !important;
        }

        /* Primary‑type buttons inside sidebar */
        div[data-testid="stSidebar"] .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #5dade2 0%, #3498db 100%) !important;
            color: #fff !important;
        }
        </style>
        """, unsafe_allow_html=True)
        st.markdown("## 🧭 Điều hướng")

        current_dashboard = st.session_state.selected_dashboard

        if current_dashboard == "admin":
            st.success("📋 **Dashboard Hành Chính**")
            st.info("Đang xem dashboard số liệu hành chính")
        elif current_dashboard == "fleet":
            st.success("🚗 **Dashboard Tổ Xe**")
            st.info("Đang xem dashboard quản lý tổ xe")
        elif current_dashboard == "umc":
            st.success("🏥 **Dashboard UMC Multi**")
            st.info("Đang xem dashboard multi-department")

        st.markdown("---")

        # Menu điều hướng
        if st.button("🏠 Menu chính", use_container_width=True):
            if 'selected_dashboard' in st.session_state:
                del st.session_state['selected_dashboard']
            st.rerun()

        if st.button("📋 Dashboard Hành Chính", use_container_width=True):
            st.session_state.selected_dashboard = "admin"
            st.rerun()

        if st.button("🚗 Dashboard Tổ Xe", use_container_width=True):
            st.session_state.selected_dashboard = "fleet"
            st.rerun()

        if st.button("🏥 Dashboard UMC Multi", use_container_width=True):
            st.session_state.selected_dashboard = "umc"
            st.rerun()

        st.markdown("---")

        if st.button("🚪 Đăng xuất", use_container_width=True):
            for key in ['authenticated', 'username', 'login_time', 'selected_dashboard']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

        # Thông tin người dùng
        st.markdown("### 👤 Thông tin")
        st.success(f"**User:** {st.session_state.username}")
        st.info(f"**Login:** {st.session_state.login_time.strftime('%H:%M:%S')}")

    # Chạy dashboard tương ứng
    if st.session_state.selected_dashboard == "admin":
        run_admin_dashboard()
    elif st.session_state.selected_dashboard == "fleet":
        run_fleet_dashboard()
    elif st.session_state.selected_dashboard == "umc":
        run_umc_dashboard()
    else:
        st.error("❌ Dashboard không hợp lệ!")
        back_to_menu()

if __name__ == "__main__":
    main()
