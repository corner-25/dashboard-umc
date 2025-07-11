#!/usr/bin/env python3
"""
Fleet Management Dashboard - Complete Version with Date Filters
Dashboard with proper column mapping, date filtering, and all analysis features
"""

import streamlit as st
import pandas as pd
import numpy as np
import requests
import subprocess
from io import BytesIO
import os
from dotenv import load_dotenv
import sys
from datetime import datetime
import json
import base64
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --------------------------------------------------------------------
# Bypass login nếu đã authenticated ở dashboard tổng
if 'authenticated' in st.session_state and st.session_state.authenticated:
    def check_authentication():
        """Luôn True khi đã đăng nhập ở dashboard chính."""
        return True

    def login_page():   # Nếu file gọi hàm này, ta vô hiệu hóa
        st.session_state['skip_child_login'] = True
        return
# --------------------------------------------------------------------

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
        padding: 1rem;
        background: #ffffff;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .metric-container {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
        margin: 0.5rem 0;
    }

    /* Centered header container and text */
    .header-container {
        text-align: center;
        display: flex;
        flex-direction: row;
        align-items: center;
        justify-content: center;
        margin-bottom: 2rem;
    }

    .header-text {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-top: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# COLUMN MAPPING - Vietnamese to English
COLUMN_MAPPING = {
    # Drop these columns (set to None to ignore)
    'Timestamp': None,  # Ignore timestamp
    'Email Address': None,  # Already converted to driver name
    'Ghi chú': None,  # Notes - not used for KPI
    'Chỉ số đồng hồ sau khi kết thúc chuyến xe': None,  # Odometer - already processed
    'Ghi nhận chi tiết chuyến xe': None,  # Trip details - only for reporting
    
    # Core time fields
    'Thời gian bắt đầu': 'start_time',
    'Thời gian kết thúc': 'end_time', 
    'Thời gian': 'duration_hours',  # Duration in hours (hh:mm format)
    
    # Location and classification
    'Điểm đến': 'destination',
    'Phân loại công tác': 'work_category',
    'Nội thành/ngoại thành': 'area_type',  # Urban/suburban
    
    # Date and numeric metrics
    'Ngày ghi nhận': 'record_date',  # mm/dd/yyyy format
    'Quãng đường': 'distance_km',
    'Đổ nhiên liệu': 'fuel_liters',
    
    # Revenue (ambulance only)
    'Doanh thu': 'revenue_vnd',
    'Chi tiết chuyến xe': 'trip_details',
    
    # Vehicle and driver info (added during sync)
    'Mã xe': 'vehicle_id',
    'Tên tài xế': 'driver_name',
    'Loại xe': 'vehicle_type'  # 'Hành chính' or 'Cứu thương'
}

def get_github_token():
    """Get GitHub token for private repo access"""
    # Priority 1: Read from sync_config.json
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and 'GITHUB_TOKEN' in st.secrets:
            return st.secrets['GITHUB_TOKEN']
    except:
        pass
    
    # Priority 2: Environment variable (.env file)
    token = os.getenv('GITHUB_TOKEN')
    if token and len(token) > 10:
        return token
    
    # Priority 3: File (backward compatibility)
    if os.path.exists("github_token.txt"):
        try:
            with open("github_token.txt", 'r') as f:
                token = f.read().strip()
            if token and token != "YOUR_TOKEN_HERE" and len(token) > 10:
                return token
        except:
            pass
    
    return None

def parse_duration_to_hours(duration_str):
    """
    Chuyển đổi thời gian từ format h:mm sang số giờ (float)
    
    Args:
        duration_str (str): Thời gian format h:mm hoặc h:mm:ss
    
    Returns:
        float: Số giờ
    """
    if not duration_str or duration_str == "":
        return 0.0
    
    # Loại bỏ khoảng trắng và các ký tự không mong muốn
    duration_str = str(duration_str).strip()
    
    # Xử lý các format khác nhau
    # Format: "2:20:00 AM" -> chỉ lấy phần thời gian
    if "AM" in duration_str or "PM" in duration_str:
        duration_str = duration_str.split()[0]
    
    try:
        # Split theo dấu ":"
        parts = duration_str.split(":")
        
        if len(parts) == 2:  # h:mm
            hours = int(parts[0])
            minutes = int(parts[1])
            return hours + minutes / 60.0
        elif len(parts) == 3:  # h:mm:ss
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = int(parts[2])
            return hours + minutes / 60.0 + seconds / 3600.0
        else:
            return 0.0
    except (ValueError, IndexError):
        return 0.0

def ensure_duration_parsed(df):
    """
    Đảm bảo cột duration_hours được parse đúng trong toàn bộ DataFrame
    """
    if 'Thời gian' not in df.columns:
        return df
    
    # Kiểm tra xem cột đã là numeric chưa
    if not pd.api.types.is_numeric_dtype(df['Thời gian']):
        # Nếu chưa, parse từ string
        df['Thời gian'] = df['Thời gian'].apply(parse_duration_to_hours)
    else:
        # Nếu đã là numeric nhưng có thể có NaN, fill 0
        df['Thời gian'] = df['Thời gian'].fillna(0)
    
    return df

def parse_distance(distance_str):
    """
    Convert various distance inputs to kilometres (float).

    Handles:
    • Thousand separators “.” or “,”
    • Vietnamese decimal comma
    • Values tagged with “km” or “m”
    • Raw metre readings (converts metres → km when 1 000 < value < 1 000 000)
    Filters out clearly impossible per‑trip values (≤ 0 km or > 1 000 km).

    Returns:
        float: distance in km (0.0 if parsing fails or value is out of bounds)
    """
    # Empty / NaN
    if pd.isna(distance_str) or str(distance_str).strip() == "":
        return 0.0

    # Normalise string
    s = str(distance_str).lower().strip()

    # Remove textual units
    for unit in ["km", "kilomet", "kilometer", "kilometre", "m", "meter", "metre"]:
        s = s.replace(unit, "")
    # Handle Vietnamese decimal comma & thousand dots, e.g. "1.234,5"
    if "," in s and "." not in s:
        s = s.replace(".", "")       # remove thousand separators
        s = s.replace(",", ".")      # comma decimal → dot
    # Remove any leftover thousand separators
    s = s.replace(",", "").replace(" ", "")

    # Attempt conversion
    try:
        dist = float(s)
    except ValueError:
        return 0.0

    # Convert metres → km if it looks like a metre value
    if 1_000 < dist < 1_000_000:
        dist = dist / 1_000.0

    # Guard rails: ignore negative / ridiculous values
    if dist <= 0 or dist > 1_000:
        return 0.0

    return round(dist, 2)

@st.cache_data(ttl=60)
def load_data_from_github():
    """Load data from GitHub repository - Large file support"""
    github_token = get_github_token()
    
    if not github_token:
        st.sidebar.error("❌ Cần GitHub token để truy cập private repo")
        return pd.DataFrame()
    
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'Fleet-Dashboard-App'
    }
    
    # Try Contents API first
    api_url = "https://api.github.com/repos/corner-25/vehicle-storage/contents/data/latest/fleet_data_latest.json"
    
    try:
        response = requests.get(api_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            api_response = response.json()
            
            # Check if file is too large for Contents API (>1MB)
            if api_response.get('size', 0) > 1000000:
                return load_large_file_via_git_api(headers)
            
            # Normal Contents API flow
            content = base64.b64decode(api_response['content']).decode('utf-8')
            
            if not content.strip():
                return load_large_file_via_git_api(headers)
            
            data = json.loads(content)
            df = pd.DataFrame(data)
            return process_dataframe(df)
        else:
            return load_large_file_via_git_api(headers)
            
    except Exception:
        return load_large_file_via_git_api(headers)

def load_large_file_via_git_api(headers):
    """Load large file using Git API"""
    try:
        # Get latest commit
        commits_url = "https://api.github.com/repos/corner-25/vehicle-storage/commits/main"
        commits_response = requests.get(commits_url, headers=headers, timeout=30)
        
        if commits_response.status_code != 200:
            return pd.DataFrame()
        
        latest_commit = commits_response.json()
        tree_sha = latest_commit['commit']['tree']['sha']
        
        # Navigate to data/latest/fleet_data_latest.json via tree API
        tree_url = f"https://api.github.com/repos/corner-25/vehicle-storage/git/trees/{tree_sha}"
        tree_response = requests.get(tree_url, headers=headers, timeout=30)
        
        if tree_response.status_code != 200:
            return pd.DataFrame()
        
        # Find data folder
        tree_data = tree_response.json()
        data_folder = None
        for item in tree_data.get('tree', []):
            if item['path'] == 'data' and item['type'] == 'tree':
                data_folder = item['sha']
                break
        
        if not data_folder:
            return pd.DataFrame()
        
        # Get data folder tree
        data_tree_url = f"https://api.github.com/repos/corner-25/vehicle-storage/git/trees/{data_folder}"
        data_tree_response = requests.get(data_tree_url, headers=headers, timeout=30)
        
        if data_tree_response.status_code != 200:
            return pd.DataFrame()
        
        # Find latest folder
        data_tree_data = data_tree_response.json()
        latest_folder = None
        for item in data_tree_data.get('tree', []):
            if item['path'] == 'latest' and item['type'] == 'tree':
                latest_folder = item['sha']
                break
        
        if not latest_folder:
            return pd.DataFrame()
        
        # Get latest folder tree
        latest_tree_url = f"https://api.github.com/repos/corner-25/vehicle-storage/git/trees/{latest_folder}"
        latest_tree_response = requests.get(latest_tree_url, headers=headers, timeout=30)
        
        if latest_tree_response.status_code != 200:
            return pd.DataFrame()
        
        # Find JSON file
        latest_tree_data = latest_tree_response.json()
        file_blob = None
        for item in latest_tree_data.get('tree', []):
            if item['path'] == 'fleet_data_latest.json' and item['type'] == 'blob':
                file_blob = item['sha']
                break
        
        if not file_blob:
            return pd.DataFrame()
        
        # Get file content via blob API
        blob_url = f"https://api.github.com/repos/corner-25/vehicle-storage/git/blobs/{file_blob}"
        blob_response = requests.get(blob_url, headers=headers, timeout=60)
        
        if blob_response.status_code != 200:
            return pd.DataFrame()
        
        blob_data = blob_response.json()
        content = base64.b64decode(blob_data['content']).decode('utf-8')
        
        if not content.strip():
            return pd.DataFrame()
        
        data = json.loads(content)
        df = pd.DataFrame(data)
        return process_dataframe(df)
        
    except Exception:
        return pd.DataFrame()

def parse_revenue(revenue_str):
    """
    Parse revenue string and handle both formats: 600000 and 600,000
    Also handles negative values and various edge cases
    """
    if pd.isna(revenue_str) or revenue_str == '':
        return 0.0
    
    try:
        # Convert to string and clean
        revenue_str = str(revenue_str).strip()
        
        # Remove commas from the string
        revenue_str = revenue_str.replace(',', '')
        
        # Remove any currency symbols (VNĐ, đ, etc.)
        revenue_str = revenue_str.replace('VNĐ', '').replace('đ', '').replace('VND', '')
        
        # Remove any extra spaces
        revenue_str = revenue_str.strip()
        
        # Convert to float
        revenue = float(revenue_str)
        
        # Handle negative values (convert to positive)
        return abs(revenue) if revenue < 0 else revenue
        
    except (ValueError, TypeError):
        # If conversion fails, return 0
        return 0.0
        
def process_dataframe(df):
    """Process DataFrame - Apply column mapping and clean data"""
    if df.empty:
        return df
    
    try:
        
        # STEP 1: Apply column mapping
        # Create a reverse mapping for flexibility
        reverse_mapping = {}
        for viet_col, eng_col in COLUMN_MAPPING.items():
            if eng_col is not None:  # Only map non-None columns
                # Handle partial matches for long Vietnamese column names
                for col in df.columns:
                    if viet_col in col:
                        reverse_mapping[col] = eng_col
                        break
        
        # Rename columns
        df = df.rename(columns=reverse_mapping)
        
        # STEP 2: Drop unnecessary columns (those mapped to None)
        drop_columns = []
        for viet_col in COLUMN_MAPPING.keys():
            if COLUMN_MAPPING[viet_col] is None:
                # Find columns that contain this Vietnamese text
                for col in df.columns:
                    if viet_col in col:
                        drop_columns.append(col)
        
        df = df.drop(columns=drop_columns, errors='ignore')
        
        # STEP 3: Handle duplicate columns by merging them
        df = df.loc[:, ~df.columns.duplicated()]
        
        # STEP 4: Process data types
        
        # FIXED: Process duration - Convert to decimal hours using correct function name
        if 'Thời gian' in df.columns:
            df['Thời gian'] = df['Thời gian'].apply(parse_duration_to_hours)
        
        # Process distance - Handle negative values but keep all rows
        if 'distance_km' in df.columns:
            df['distance_km'] = df['distance_km'].apply(parse_distance)
        
        # Process revenue - Convert to numeric but keep all rows
        if 'revenue_vnd' in df.columns:
            df['revenue_vnd'] = df['revenue_vnd'].apply(parse_revenue)
        
        # Process fuel consumption
        if 'fuel_liters' in df.columns:
            df['fuel_liters'] = pd.to_numeric(df['fuel_liters'], errors='coerce').fillna(0)
        
        # Process datetime columns - Handle mm/dd/yyyy format
        if 'record_date' in df.columns:
            df['record_date'] = pd.to_datetime(df['record_date'], errors='coerce')  # Tự động detect format
            # Create helper columns
            df['date'] = df['record_date'].dt.date
            df['month'] = df['record_date'].dt.to_period('M').astype(str)
        return df
        
    except Exception as e:
        st.sidebar.error(f"❌ Error processing data: {e}")
        return df

def run_sync_script():
    """Execute sync script"""
    try:
        if not os.path.exists("manual_fleet_sync.py"):
            st.error("❌ Không tìm thấy file manual_fleet_sync.py")
            return False
        
        token = get_github_token()
        if not token:
            st.error("❌ Không tìm thấy GitHub token!")
            return False
        
        with st.spinner("🔄 Đang chạy sync script..."):
            try:
                if 'manual_fleet_sync' in sys.modules:
                    del sys.modules['manual_fleet_sync']
                
                import manual_fleet_sync
                sync_engine = manual_fleet_sync.ManualFleetSync()
                
                if sync_engine.config['github']['token'] == "YOUR_TOKEN_HERE":
                    st.error("❌ GitHub token chưa được load!")
                    return False
                
                success = sync_engine.sync_now()
                
                if success:
                    st.success("✅ Sync hoàn thành!")
                    st.session_state.last_sync = datetime.now()
                    return True
                else:
                    st.error("❌ Sync thất bại!")
                    return False
                    
            except Exception:
                result = subprocess.run([
                    sys.executable, "manual_fleet_sync.py", "--sync-only"
                ], capture_output=True, text=True, timeout=300)
                
                if result.returncode == 0:
                    st.success("✅ Sync hoàn thành!")
                    st.session_state.last_sync = datetime.now()
                    return True
                else:
                    st.error(f"❌ Sync thất bại: {result.stderr}")
                    return False
                    
    except Exception as e:
        st.error(f"❌ Lỗi chạy sync: {e}")
        return False

def filter_data_by_date_range(df, start_date, end_date):
    """Filter dataframe by date range - FIXED to not drop invalid dates"""
    if df.empty or 'record_date' not in df.columns:
        return df
    
    try:
        # Ensure record_date is datetime
        df['record_date'] = pd.to_datetime(df['record_date'], format='%m/%d/%Y', errors='coerce')
        
        # Count invalid dates for debugging
        invalid_count = df['record_date'].isna().sum()
        if invalid_count > 0:
            st.sidebar.warning(f"⚠️ Found {invalid_count} records with invalid dates - keeping them!")
        
        # FIXED: Include records with invalid dates in filter
        # For invalid dates, we'll keep them in the result instead of dropping
        valid_mask = (df['record_date'].notna()) & (df['record_date'].dt.date >= start_date) & (df['record_date'].dt.date <= end_date)
        invalid_mask = df['record_date'].isna()
        
        # Keep both valid dates in range AND invalid dates
        combined_mask = valid_mask | invalid_mask
        filtered_df = df[combined_mask].copy()
        
        return filtered_df
        
    except Exception as e:
        st.sidebar.error(f"❌ Lỗi lọc dữ liệu: {e}")
        return df

def get_date_range_from_data(df):
    """Get min and max dates from data"""
    if df.empty or 'record_date' not in df.columns:
        return datetime.now().date(), datetime.now().date()
    
    try:
        df['record_date'] = pd.to_datetime(df['record_date'], format='%m/%d/%Y', errors='coerce')
        valid_dates = df[df['record_date'].notna()]
        
        if valid_dates.empty:
            return datetime.now().date(), datetime.now().date()
        
        min_date = valid_dates['record_date'].min().date()
        max_date = valid_dates['record_date'].max().date()
        
        return min_date, max_date
        
    except Exception:
        return datetime.now().date(), datetime.now().date()

def create_date_filter_sidebar(df):
    """Create date range filter in sidebar"""
    st.sidebar.markdown("### 📅 Bộ lọc thời gian")
    
    # Get data date range
    min_date, max_date = get_date_range_from_data(df)
    
    # Show data range info
    st.sidebar.info(f"📊 Dữ liệu có: {min_date.strftime('%d/%m/%Y')} - {max_date.strftime('%d/%m/%Y')}")
    
    # FIXED: Reset session state if current values are outside new data range
    reset_needed = False
    if 'date_filter_start' in st.session_state:
        if st.session_state.date_filter_start < min_date or st.session_state.date_filter_start > max_date:
            reset_needed = True
    if 'date_filter_end' in st.session_state:
        if st.session_state.date_filter_end < min_date or st.session_state.date_filter_end > max_date:
            reset_needed = True
    
    if reset_needed:
        st.sidebar.warning("⚠️ Đã reset bộ lọc ngày do dữ liệu thay đổi")
        if 'date_filter_start' in st.session_state:
            del st.session_state.date_filter_start
        if 'date_filter_end' in st.session_state:
            del st.session_state.date_filter_end
    
    # Initialize session state for date filters if not exists or after reset
    if 'date_filter_start' not in st.session_state:
        st.session_state.date_filter_start = min_date
    if 'date_filter_end' not in st.session_state:
        st.session_state.date_filter_end = max_date
    
    # Ensure session state values are within valid range
    if st.session_state.date_filter_start < min_date:
        st.session_state.date_filter_start = min_date
    if st.session_state.date_filter_start > max_date:
        st.session_state.date_filter_start = max_date
    if st.session_state.date_filter_end < min_date:
        st.session_state.date_filter_end = min_date
    if st.session_state.date_filter_end > max_date:
        st.session_state.date_filter_end = max_date
    
    # Date range selector
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        start_date = st.date_input(
            "Từ ngày:",
            value=st.session_state.date_filter_start,
            min_value=min_date,
            max_value=max_date,
            key="start_date_input"
        )
    
    with col2:
        end_date = st.date_input(
            "Đến ngày:",
            value=st.session_state.date_filter_end,
            min_value=min_date,
            max_value=max_date,
            key="end_date_input"
        )
    
    # Update session state when inputs change
    if start_date != st.session_state.date_filter_start:
        st.session_state.date_filter_start = start_date
    if end_date != st.session_state.date_filter_end:
        st.session_state.date_filter_end = end_date
    
    # Validate date range
    if start_date > end_date:
        st.sidebar.error("❌ Ngày bắt đầu phải nhỏ hơn ngày kết thúc!")
        return df, min_date, max_date
    
    # Quick filter buttons
    st.sidebar.markdown("**🚀 Bộ lọc nhanh:**")
    
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("📅 7 ngày gần nhất", use_container_width=True, key="btn_7_days"):
            st.session_state.date_filter_start = max_date - pd.Timedelta(days=6)
            st.session_state.date_filter_end = max_date
            st.rerun()
        
        if st.button("📅 Tháng này", use_container_width=True, key="btn_this_month"):
            today = datetime.now().date()
            st.session_state.date_filter_start = today.replace(day=1)
            st.session_state.date_filter_end = min(today, max_date)
            st.rerun()
    
    with col2:
        if st.button("📅 30 ngày gần nhất", use_container_width=True, key="btn_30_days"):
            st.session_state.date_filter_start = max_date - pd.Timedelta(days=29)
            st.session_state.date_filter_end = max_date
            st.rerun()
        
        if st.button("📅 Tất cả", use_container_width=True, key="btn_all_data"):
            st.session_state.date_filter_start = min_date
            st.session_state.date_filter_end = max_date
            st.rerun()
    
    # Use the session state values for filtering
    filter_start = st.session_state.date_filter_start
    filter_end = st.session_state.date_filter_end
    
    # Filter data
    filtered_df = filter_data_by_date_range(df, filter_start, filter_end)
    
    # Show filtered data info
    if not filtered_df.empty:
        days_selected = (filter_end - filter_start).days + 1
        active_days = filtered_df['record_date'].dt.date.nunique() if 'record_date' in filtered_df.columns else 0
        
        st.sidebar.success(f"✅ Đã chọn: {days_selected} ngày")

        if len(filtered_df) == 0:
            st.sidebar.warning("⚠️ Không có dữ liệu trong khoảng thời gian này")
    
    return filtered_df, filter_start, filter_end

def create_vehicle_filter_sidebar(df):
    """Create vehicle and driver filters in sidebar"""
    st.sidebar.markdown("### 🚗 Bộ lọc xe và tài xế")
    
    if df.empty:
        return df
    
    # Vehicle type filter
    if 'vehicle_type' in df.columns:
        vehicle_types = ['Tất cả'] + list(df['vehicle_type'].unique())
        selected_type = st.sidebar.selectbox(
            "Loại xe:",
            options=vehicle_types,
            index=0
        )
        
        if selected_type != 'Tất cả':
            df = df[df['vehicle_type'] == selected_type]
    
    # Vehicle ID filter (multiselect)
    if 'vehicle_id' in df.columns:
        vehicle_ids = list(df['vehicle_id'].unique())
        selected_vehicles = st.sidebar.multiselect(
            "Chọn xe (để trống = tất cả):",
            options=vehicle_ids,
            default=[]
        )
        
        if selected_vehicles:
            df = df[df['vehicle_id'].isin(selected_vehicles)]
    
    # Driver filter (multiselect)
    if 'driver_name' in df.columns:
        drivers = list(df['driver_name'].unique())
        selected_drivers = st.sidebar.multiselect(
            "Chọn tài xế (để trống = tất cả):",
            options=drivers,
            default=[]
        )
        
        if selected_drivers:
            df = df[df['driver_name'].isin(selected_drivers)]
    
    # Work category filter
    if 'work_category' in df.columns:
        work_categories = ['Tất cả'] + list(df['work_category'].dropna().unique())
        selected_category = st.sidebar.selectbox(
            "Phân loại công tác:",
            options=work_categories,
            index=0
        )
        
        if selected_category != 'Tất cả':
            df = df[df['work_category'] == selected_category]
    
    # Area type filter
    if 'area_type' in df.columns:
        area_types = ['Tất cả'] + list(df['area_type'].dropna().unique())
        selected_area = st.sidebar.selectbox(
            "Khu vực:",
            options=area_types,
            index=0
        )
        
        if selected_area != 'Tất cả':
            df = df[df['area_type'] == selected_area]
    
    return df

# FIXED: create_metrics_overview() - ensure duration is parsed
def create_metrics_overview(df):
    """Create overview metrics using English column names"""
    if df.empty:
        st.warning("⚠️ Không có dữ liệu để hiển thị")
        return
    
    st.markdown("## 📊 Tổng quan hoạt động")
    
    # FIXED: Ensure duration is properly parsed
    df = ensure_duration_parsed(df)
    
    # Use ALL data without any filtering
    total_trips = len(df)
    total_vehicles = df['vehicle_id'].nunique() if 'vehicle_id' in df.columns else 0
    
    # Driver count
    total_drivers = df['driver_name'].nunique() if 'driver_name' in df.columns else 0
    
    # Revenue calculation
    if 'revenue_vnd' in df.columns:
        df['revenue_vnd'] = pd.to_numeric(df['revenue_vnd'], errors='coerce').fillna(0)
        total_revenue = df['revenue_vnd'].sum()
        revenue_records = df[df['revenue_vnd'] > 0]
        avg_revenue_per_trip = revenue_records['revenue_vnd'].mean() if len(revenue_records) > 0 else 0
    else:
        total_revenue = 0
        avg_revenue_per_trip = 0
    
    # FIXED: Time calculation - ensure proper parsing
    if 'Thời gian' in df.columns:
        # Filter out invalid time data (negative or extremely large values)
        valid_time_data = df[
            df['Thời gian'].notna() & 
            (df['Thời gian'] >= 0) & 
            (df['Thời gian'] <= 24)  # Reasonable daily limit
        ]
        total_hours = valid_time_data['Thời gian'].sum()
        avg_hours_per_trip = valid_time_data['Thời gian'].mean() if len(valid_time_data) > 0 else 0
    else:
        total_hours = 0
        avg_hours_per_trip = 0
    
    # Distance calculation
    if 'distance_km' in df.columns:
        df['distance_km'] = df['distance_km'].apply(parse_distance)
        valid_distance_data = df[df['distance_km'].notna() & (df['distance_km'] >= 0)]
        total_distance = valid_distance_data['distance_km'].sum()
        avg_distance = valid_distance_data['distance_km'].mean() if len(valid_distance_data) > 0 else 0
    else:
        total_distance = 0
        avg_distance = 0
    
    # Display metrics in 4-4 layout
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="🚗 Tổng chuyến",
            value=f"{total_trips:,}",
            help="Tổng số chuyến đã thực hiện"
        )
    
    with col2:
        st.metric(
            label="🏥 Số xe hoạt động", 
            value=f"{total_vehicles}",
            help="Số xe đang hoạt động"
        )
    
    with col3:
        st.metric(
            label="👨‍💼 Số tài xế",
            value=f"{total_drivers}",
            help="Số tài xế đang làm việc"
        )
    
    with col4:
        st.metric(
            label="💰 Tổng doanh thu",
            value=f"{total_revenue:,.0f} VNĐ",
            help="Tổng doanh thu từ xe cứu thương"
        )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col5, col6, col7, col8 = st.columns(4)
    
    with col5:
        st.metric(
            label="⏱️ Tổng giờ chạy",
            value=f"{total_hours:,.1f} giờ",
            help="Tổng thời gian vận hành"
        )
    
    with col6:
        st.metric(
            label="🛣️ Tổng quãng đường",
            value=f"{total_distance:,.1f} km",
            help="Tổng quãng đường đã di chuyển"
        )
    
    with col7:
        st.metric(
            label="💵 TB doanh thu/chuyến",
            value=f"{avg_revenue_per_trip:,.0f} VNĐ",
            help="Doanh thu trung bình mỗi chuyến (xe cứu thương)"
        )
    
    with col8:
        st.metric(
            label="⏰ TB giờ/chuyến", 
            value=f"{avg_hours_per_trip:.1f} giờ",
            help="Thời gian trung bình mỗi chuyến"
        )


def create_frequency_metrics(df):
    """Create frequency and activity metrics using English columns"""
    st.markdown("## 🎯 Chỉ số tần suất hoạt động")
    
    if df.empty or 'record_date' not in df.columns:
        st.warning("⚠️ Không có dữ liệu thời gian")
        return
    
    try:
        df['record_date'] = pd.to_datetime(df['record_date'], format='%m/%d/%Y', errors='coerce')
        df['date'] = df['record_date'].dt.date
        
        # Filter out invalid dates
        valid_dates = df[df['record_date'].notna()]
        invalid_count = df['record_date'].isna().sum()
        
        if invalid_count > 0:
            st.sidebar.info(f"ℹ️ {invalid_count} records có ngày không hợp lệ (vẫn tính trong tổng)")
        
        if valid_dates.empty:
            st.warning("⚠️ Không có dữ liệu ngày hợp lệ")
            return
        
        # FIXED: Calculate actual active days (only days with trips)
        active_days = valid_dates['date'].nunique()  # Only days with actual trips
        total_date_range = (valid_dates['record_date'].max() - valid_dates['record_date'].min()).days + 1
        
        # Daily trip counts
        daily_trips = valid_dates.groupby('date')['vehicle_id'].count()
        
        # Vehicle utilization
        total_vehicles = df['vehicle_id'].nunique() if 'vehicle_id' in df.columns else 1
        daily_active_vehicles = valid_dates.groupby('date')['vehicle_id'].nunique()
        
        
    except Exception as e:
        st.error(f"❌ Lỗi xử lý ngày tháng: {e}")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # FIXED: Use actual active days instead of total date range
        avg_trips_per_day = len(valid_dates) / active_days if active_days > 0 else 0
        st.metric(
            label="📈 Chuyến TB/ngày",
            value=f"{avg_trips_per_day:.1f}",
            help=f"Số chuyến trung bình mỗi ngày hoạt động ({active_days} ngày có chuyến)"
        )
    
    with col2:
        # FIXED: Use active days for utilization calculation too
        avg_utilization = (daily_active_vehicles.mean() / total_vehicles * 100) if total_vehicles > 0 else 0
        st.metric(
            label="🚗 Tỷ lệ sử dụng xe TB",
            value=f"{avg_utilization:.1f}%",
            help=f"Tỷ lệ xe hoạt động trung bình ({total_vehicles} xe tổng)"
        )
    
    with col3:
        peak_day_trips = daily_trips.max() if not daily_trips.empty else 0
        peak_date = daily_trips.idxmax() if not daily_trips.empty else None
        st.metric(
            label="⬆️ Ngày cao điểm",
            value=f"{peak_day_trips} chuyến",
            help=f"Ngày có nhiều chuyến nhất: {peak_date}" if peak_date else "Ngày có nhiều chuyến nhất"
        )
    
    with col4:
        low_day_trips = daily_trips.min() if not daily_trips.empty else 0
        low_date = daily_trips.idxmin() if not daily_trips.empty else None
        st.metric(
            label="⬇️ Ngày thấp điểm",
            value=f"{low_day_trips} chuyến",
            help=f"Ngày có ít chuyến nhất: {low_date}" if low_date else "Ngày có ít chuyến nhất"
        )
    
    # Additional metrics row - NEW
    st.markdown("<br>", unsafe_allow_html=True)
    col5, col6, col7, col8 = st.columns(4)
    
    with col5:
        utilization_rate = (active_days / total_date_range * 100) if total_date_range > 0 else 0
        st.metric(
            label="📅 Tỷ lệ ngày hoạt động",
            value=f"{utilization_rate:.1f}%",
            help=f"{active_days}/{total_date_range} ngày có hoạt động"
        )
    
    with col6:
        avg_trips_per_active_day = daily_trips.mean() if not daily_trips.empty else 0
        st.metric(
            label="📊 TB chuyến/ngày hoạt động",
            value=f"{avg_trips_per_active_day:.1f}",
            help="Trung bình số chuyến trong những ngày có hoạt động"
        )
    
    with col7:
        max_vehicles_per_day = daily_active_vehicles.max() if not daily_active_vehicles.empty else 0
        st.metric(
            label="🚛 Max xe/ngày",
            value=f"{max_vehicles_per_day}",
            help="Số xe tối đa hoạt động trong 1 ngày"
        )
    
    with col8:
        avg_vehicles_per_day = daily_active_vehicles.mean() if not daily_active_vehicles.empty else 0
        st.metric(
            label="🚗 TB xe/ngày",
            value=f"{avg_vehicles_per_day:.1f}",
            help="Trung bình số xe hoạt động mỗi ngày"
        )

def create_vehicle_performance_table(df):
    """Create detailed vehicle performance table using English columns"""
    st.markdown("## 📋 Hiệu suất chi tiết từng xe")
    
    if df.empty or 'vehicle_id' not in df.columns:
        st.warning("⚠️ Không có dữ liệu xe")
        return
    
    # FIXED: Ensure duration is properly parsed
    df = ensure_duration_parsed(df)
    
    # Ensure datetime conversion
    try:
        if 'record_date' in df.columns:
            df['record_date'] = pd.to_datetime(df['record_date'], format='%m/%d/%Y', errors='coerce')
            df['date'] = df['record_date'].dt.date
            
            valid_dates = df[df['record_date'].notna()]
            if not valid_dates.empty:
                total_days = (valid_dates['record_date'].max() - valid_dates['record_date'].min()).days + 1
            else:
                total_days = 30
        else:
            total_days = 30
    except:
        total_days = 30
    
    # Ensure numeric columns
    if 'revenue_vnd' in df.columns:
        df['revenue_vnd'] = pd.to_numeric(df['revenue_vnd'], errors='coerce').fillna(0)
    else:
        df['revenue_vnd'] = 0
        
    # FIXED: Duration is already parsed by ensure_duration_parsed()
    if 'Thời gian' not in df.columns:
        df['Thời gian'] = 0
        
    if 'distance_km' in df.columns:
        df['distance_km'] = df['distance_km'].apply(parse_distance)
    else:
        df['distance_km'] = 0
        
    if 'fuel_liters' in df.columns:
        df['fuel_liters'] = pd.to_numeric(df['fuel_liters'], errors='coerce').fillna(0)
    else:
        df['fuel_liters'] = 0
    
    # Calculate metrics per vehicle
    vehicles = df['vehicle_id'].unique()
    results = []
    
    for vehicle in vehicles:
        vehicle_data = df[df['vehicle_id'] == vehicle]
        
        # Basic metrics
        total_trips = len(vehicle_data)
        total_revenue = float(vehicle_data['revenue_vnd'].sum())
        avg_revenue = float(vehicle_data['revenue_vnd'].mean()) if total_trips > 0 else 0.0
        
        # FIXED: Duration calculation - filter out invalid values
        valid_duration_data = vehicle_data[
            vehicle_data['Thời gian'].notna() & 
            (vehicle_data['Thời gian'] >= 0) & 
            (vehicle_data['Thời gian'] <= 24)
        ]
        total_hours = float(valid_duration_data['Thời gian'].sum())
        
        total_distance = float(vehicle_data['distance_km'].sum())
        total_fuel = float(vehicle_data['fuel_liters'].sum())
        
        # Days calculation
        if 'date' in vehicle_data.columns:
            active_days = vehicle_data['date'].nunique()
        else:
            active_days = total_days
        
        # Derived metrics
        fuel_per_100km = (total_fuel / total_distance * 100.0) if total_distance > 0 else 0.0
        trips_per_day = (float(total_trips) / float(active_days)) if active_days > 0 else 0.0
        utilization = (float(active_days) / float(total_days) * 100.0) if total_days > 0 else 0.0
        
        # Performance rating
        if trips_per_day >= 2 and utilization >= 70:
            performance = 'Cao'
        elif trips_per_day >= 1 and utilization >= 50:
            performance = 'Trung bình'
        else:
            performance = 'Thấp'
        
        results.append({
            'Mã xe': vehicle,
            'Tổng chuyến': total_trips,
            'Tổng doanh thu': round(total_revenue, 0),
            'Doanh thu TB/chuyến': round(avg_revenue, 0),
            'Tổng giờ chạy': round(total_hours, 1),
            'Số ngày hoạt động': active_days,
            'Tổng quãng đường': round(total_distance, 1),
            'Nhiên liệu tiêu thụ': round(total_fuel, 1),
            'Nhiên liệu/100km': round(fuel_per_100km, 2),
            'Chuyến/ngày': round(trips_per_day, 1),
            'Tỷ lệ sử dụng (%)': round(utilization, 1),
            'Hiệu suất': performance
        })
    
    # Create DataFrame
    vehicle_display = pd.DataFrame(results)
    vehicle_display = vehicle_display.set_index('Mã xe').sort_values('Tổng doanh thu', ascending=False)
    
    # Display table
    st.dataframe(
        vehicle_display.style.format({
            'Tổng doanh thu': '{:,.0f}',
            'Doanh thu TB/chuyến': '{:,.0f}',
            'Tổng giờ chạy': '{:.1f}',
            'Tổng quãng đường': '{:.1f}',
            'Nhiên liệu tiêu thụ': '{:.1f}',
            'Nhiên liệu/100km': '{:.2f}',
            'Chuyến/ngày': '{:.1f}',
            'Tỷ lệ sử dụng (%)': '{:.1f}'
        }),
        use_container_width=True,
        height=400
    )

def create_revenue_analysis_tab(df):
    """Tab 1: Phân tích doanh thu"""
    st.markdown("### 💰 Phân tích doanh thu chi tiết")
    
    if df.empty or 'revenue_vnd' not in df.columns:
        st.warning("⚠️ Không có dữ liệu doanh thu")
        return
    
    # Ensure proper data types
    df['revenue_vnd'] = pd.to_numeric(df['revenue_vnd'], errors='coerce').fillna(0)
    revenue_data = df[df['revenue_vnd'] > 0].copy()
    
    if revenue_data.empty:
        st.warning("⚠️ Không có chuyến xe có doanh thu")
        return
    
    # Revenue by vehicle chart
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📊 Doanh thu theo xe")
        vehicle_revenue = revenue_data.groupby('vehicle_id')['revenue_vnd'].agg(['sum', 'count', 'mean']).reset_index()
        vehicle_revenue.columns = ['vehicle_id', 'total_revenue', 'trip_count', 'avg_revenue']
        vehicle_revenue = vehicle_revenue.sort_values('total_revenue', ascending=False)
        
        fig_vehicle = px.bar(
            vehicle_revenue.head(10),
            x='vehicle_id',
            y='total_revenue',
            title="Top 10 xe có doanh thu cao nhất",
            labels={'total_revenue': 'Doanh thu (VNĐ)', 'vehicle_id': 'Mã xe'},
            color='total_revenue',
            color_continuous_scale='Blues'
        )
        fig_vehicle.update_layout(height=400)
        st.plotly_chart(fig_vehicle, use_container_width=True)
    
    with col2:
        st.markdown("#### 📈 Doanh thu theo thời gian")
        if 'record_date' in revenue_data.columns:
            daily_revenue = revenue_data.groupby('date')['revenue_vnd'].sum().reset_index()
            daily_revenue = daily_revenue.sort_values('date')
            
            fig_time = px.line(
                daily_revenue,
                x='date',
                y='revenue_vnd',
                title="Xu hướng doanh thu theo ngày",
                labels={'revenue_vnd': 'Doanh thu (VNĐ)', 'date': 'Ngày'}
            )
            fig_time.update_layout(height=400)
            st.plotly_chart(fig_time, use_container_width=True)
        else:
            st.info("Không có dữ liệu thời gian để hiển thị xu hướng")
    
    # Revenue distribution
    col3, col4 = st.columns(2)
    
    with col3:
        st.markdown("#### 📊 Phân bố doanh thu mỗi chuyến")
        fig_dist = px.histogram(
            revenue_data,
            x='revenue_vnd',
            nbins=20,
            title="Phân bố doanh thu mỗi chuyến",
            labels={'revenue_vnd': 'Doanh thu (VNĐ)', 'count': 'Số chuyến'}
        )
        fig_dist.update_layout(height=400)
        st.plotly_chart(fig_dist, use_container_width=True)
    
    with col4:
        st.markdown("#### 👨‍💼 Doanh thu theo tài xế")
        if 'driver_name' in revenue_data.columns:
            driver_revenue = revenue_data.groupby('driver_name')['revenue_vnd'].sum().reset_index()
            driver_revenue = driver_revenue.sort_values('revenue_vnd', ascending=False).head(10)
            
            fig_driver = px.pie(
                driver_revenue,
                values='revenue_vnd',
                names='driver_name',
                title="Top 10 tài xế theo doanh thu"
            )
            fig_driver.update_layout(height=400)
            st.plotly_chart(fig_driver, use_container_width=True)
        else:
            st.info("Không có dữ liệu tài xế")
    
    # Revenue metrics table
    st.markdown("#### 📋 Bảng thống kê doanh thu")
    revenue_stats = pd.DataFrame({
        'Chỉ số': ['Tổng doanh thu', 'Doanh thu TB/chuyến', 'Doanh thu cao nhất', 'Doanh thu thấp nhất', 'Số chuyến có doanh thu'],
        'Giá trị': [
            f"{revenue_data['revenue_vnd'].sum():,.0f} VNĐ",
            f"{revenue_data['revenue_vnd'].mean():,.0f} VNĐ",
            f"{revenue_data['revenue_vnd'].max():,.0f} VNĐ",
            f"{revenue_data['revenue_vnd'].min():,.0f} VNĐ",
            f"{len(revenue_data):,} chuyến"
        ]
    })
    st.dataframe(revenue_stats, use_container_width=True, hide_index=True)

def create_vehicle_efficiency_tab(df):
    """Tab 2: Hiệu suất xe"""
    st.markdown("### 🚗 Phân tích hiệu suất xe")
    
    if df.empty or 'vehicle_id' not in df.columns:
        st.warning("⚠️ Không có dữ liệu xe")
        return
    
    # Calculate efficiency metrics per vehicle
    vehicle_stats = []
    for vehicle in df['vehicle_id'].unique():
        vehicle_data = df[df['vehicle_id'] == vehicle]
        
        # Basic metrics
        total_trips = len(vehicle_data)
        total_hours = vehicle_data['Thời gian'].sum() if 'Thời gian' in vehicle_data.columns else 0
        total_distance = vehicle_data['distance_km'].sum() if 'distance_km' in vehicle_data.columns else 0
        total_revenue = vehicle_data['revenue_vnd'].sum() if 'revenue_vnd' in vehicle_data.columns else 0
        
        # Active days
        active_days = vehicle_data['date'].nunique() if 'date' in vehicle_data.columns else 1
        
        # Efficiency metrics
        trips_per_day = total_trips / active_days if active_days > 0 else 0
        hours_per_trip = total_hours / total_trips if total_trips > 0 else 0
        distance_per_trip = total_distance / total_trips if total_trips > 0 else 0
        revenue_per_hour = total_revenue / total_hours if total_hours > 0 else 0
        
        vehicle_stats.append({
            'vehicle_id': vehicle,
            'total_trips': total_trips,
            'active_days': active_days,
            'trips_per_day': trips_per_day,
            'hours_per_trip': hours_per_trip,
            'distance_per_trip': distance_per_trip,
            'revenue_per_hour': revenue_per_hour,
            'total_hours': total_hours,
            'total_distance': total_distance,
            'total_revenue': total_revenue
        })
    
    efficiency_df = pd.DataFrame(vehicle_stats)
    
    # Efficiency charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📊 Chuyến/ngày theo xe")
        fig_trips = px.bar(
            efficiency_df.sort_values('trips_per_day', ascending=False).head(15),
            x='vehicle_id',
            y='trips_per_day',
            title="Số chuyến trung bình mỗi ngày",
            labels={'trips_per_day': 'Chuyến/ngày', 'vehicle_id': 'Mã xe'},
            color='trips_per_day',
            color_continuous_scale='Greens'
        )
        fig_trips.update_layout(height=400)
        st.plotly_chart(fig_trips, use_container_width=True)
    
    with col2:
        st.markdown("#### ⏱️ Thời gian trung bình mỗi chuyến")
        fig_hours = px.bar(
            efficiency_df.sort_values('hours_per_trip', ascending=False).head(15),
            x='vehicle_id',
            y='hours_per_trip',
            title="Giờ trung bình mỗi chuyến",
            labels={'hours_per_trip': 'Giờ/chuyến', 'vehicle_id': 'Mã xe'},
            color='hours_per_trip',
            color_continuous_scale='Oranges'
        )
        fig_hours.update_layout(height=400)
        st.plotly_chart(fig_hours, use_container_width=True)
    
    # Scatter plot: Efficiency comparison
    col3, col4 = st.columns(2)
    
    with col3:
        st.markdown("#### 🎯 Hiệu suất: Chuyến/ngày vs Doanh thu/giờ")
        fig_scatter = px.scatter(
            efficiency_df,
            x='trips_per_day',
            y='revenue_per_hour',
            size='total_trips',
            hover_data=['vehicle_id', 'active_days'],
            title="Ma trận hiệu suất xe",
            labels={'trips_per_day': 'Chuyến/ngày', 'revenue_per_hour': 'Doanh thu/giờ (VNĐ)'}
        )
        fig_scatter.update_layout(height=400)
        st.plotly_chart(fig_scatter, use_container_width=True)
    
    with col4:
        st.markdown("#### 📏 Quãng đường trung bình mỗi chuyến")
        fig_distance = px.bar(
            efficiency_df.sort_values('distance_per_trip', ascending=False).head(15),
            x='vehicle_id',
            y='distance_per_trip',
            title="Km trung bình mỗi chuyến",
            labels={'distance_per_trip': 'Km/chuyến', 'vehicle_id': 'Mã xe'},
            color='distance_per_trip',
            color_continuous_scale='Blues'
        )
        fig_distance.update_layout(height=400)
        st.plotly_chart(fig_distance, use_container_width=True)
    
    # Top performers table
    st.markdown("#### 🏆 Top xe hiệu suất cao")
    top_performers = efficiency_df.nlargest(10, 'trips_per_day')[['vehicle_id', 'trips_per_day', 'hours_per_trip', 'distance_per_trip', 'revenue_per_hour']]
    top_performers.columns = ['Mã xe', 'Chuyến/ngày', 'Giờ/chuyến', 'Km/chuyến', 'Doanh thu/giờ']
    st.dataframe(top_performers.round(2), use_container_width=True, hide_index=True)

def create_overload_analysis_tab(df):
    """Tab 3: Phân tích quá tải"""
    st.markdown("### ⚡ Phân tích quá tải và tối ưu hóa")
    
    if df.empty:
        st.warning("⚠️ Không có dữ liệu để phân tích")
        return
    
    # Define overload thresholds
    st.markdown("#### 🎯 Thiết lập ngưỡng cảnh báo")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        max_hours_per_day = st.number_input("Max giờ/ngày", value=10.0, min_value=1.0, max_value=24.0)
    with col2:
        max_trips_per_day = st.number_input("Max chuyến/ngày", value=8, min_value=1, max_value=20)
    with col3:
        max_distance_per_trip = st.number_input("Max km/chuyến", value=100.0, min_value=1.0, max_value=500.0)
    
    # Calculate daily workload per vehicle and driver
    if 'date' in df.columns:
        # Vehicle daily workload
        vehicle_daily = df.groupby(['vehicle_id', 'date']).agg({
            'Thời gian': 'sum',
            'distance_km': 'sum',
            'revenue_vnd': 'count'  # count trips - use different column to avoid conflict
        }).reset_index()
        vehicle_daily.columns = ['vehicle_id', 'date', 'daily_hours', 'daily_distance', 'daily_trips']
        
        # Driver daily workload
        if 'driver_name' in df.columns:
            driver_daily = df.groupby(['driver_name', 'date']).agg({
                'Thời gian': 'sum',
                'distance_km': 'sum',
                'revenue_vnd': 'count'  # count trips - use different column to avoid conflict
            }).reset_index()
            driver_daily.columns = ['driver_name', 'date', 'daily_hours', 'daily_distance', 'daily_trips']
        
        # Identify overloaded days
        vehicle_overload = vehicle_daily[
            (vehicle_daily['daily_hours'] > max_hours_per_day) |
            (vehicle_daily['daily_trips'] > max_trips_per_day)
        ]
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🚨 Xe vượt ngưỡng giờ làm việc")
            if not vehicle_overload.empty:
                fig_overload = px.scatter(
                    vehicle_daily,
                    x='daily_trips',
                    y='daily_hours',
                    color='vehicle_id',
                    title="Phân tích tải công việc hàng ngày",
                    labels={'daily_trips': 'Số chuyến/ngày', 'daily_hours': 'Giờ làm việc/ngày'}
                )
                # Add threshold lines
                fig_overload.add_hline(y=max_hours_per_day, line_dash="dash", line_color="red", 
                                     annotation_text=f"Max {max_hours_per_day}h/ngày")
                fig_overload.add_vline(x=max_trips_per_day, line_dash="dash", line_color="red",
                                     annotation_text=f"Max {max_trips_per_day} chuyến/ngày")
                fig_overload.update_layout(height=400)
                st.plotly_chart(fig_overload, use_container_width=True)
            else:
                st.success("✅ Không có xe nào vượt ngưỡng!")
        
        with col2:
            st.markdown("#### 📊 Phân bố tải công việc")
            # Heatmap of workload by day and vehicle
            if len(vehicle_daily) > 0:
                pivot_hours = vehicle_daily.pivot_table(
                    values='daily_hours', 
                    index='vehicle_id', 
                    columns='date', 
                    aggfunc='mean'
                ).fillna(0)
                
                if not pivot_hours.empty:
                    fig_heatmap = px.imshow(
                        pivot_hours.values,
                        labels=dict(x="Ngày", y="Xe", color="Giờ/ngày"),
                        y=pivot_hours.index,
                        title="Bản đồ nhiệt tải công việc"
                    )
                    fig_heatmap.update_layout(height=400)
                    st.plotly_chart(fig_heatmap, use_container_width=True)
        
        # Distance analysis
        col3, col4 = st.columns(2)
        
        with col3:
            st.markdown("#### 🛣️ Phân tích quãng đường nguy hiểm")
            if 'distance_km' in df.columns:
                long_trips = df[df['distance_km'] > max_distance_per_trip]
                
                if not long_trips.empty:
                    fig_distance = px.histogram(
                        df,
                        x='distance_km',
                        nbins=30,
                        title="Phân bố quãng đường chuyến xe",
                        labels={'distance_km': 'Quãng đường (km)', 'count': 'Số chuyến'}
                    )
                    fig_distance.add_vline(x=max_distance_per_trip, line_dash="dash", line_color="red",
                                         annotation_text=f"Ngưỡng {max_distance_per_trip}km")
                    fig_distance.update_layout(height=400)
                    st.plotly_chart(fig_distance, use_container_width=True)
                else:
                    st.success("✅ Không có chuyến xe nào vượt ngưỡng km!")
        
        with col4:
            st.markdown("#### ⚠️ Cảnh báo quá tải")
            
            # Overload summary
            overload_summary = []
            
            # Vehicle overload count
            vehicle_overload_count = len(vehicle_overload)
            if vehicle_overload_count > 0:
                overload_summary.append(f"🚨 {vehicle_overload_count} lần xe vượt ngưỡng")
            
            # Long distance trips
            if 'distance_km' in df.columns:
                long_trips_count = len(df[df['distance_km'] > max_distance_per_trip])
                if long_trips_count > 0:
                    overload_summary.append(f"🛣️ {long_trips_count} chuyến vượt ngưỡng km")
            
            if overload_summary:
                for warning in overload_summary:
                    st.warning(warning)
            else:
                st.success("✅ Hệ thống hoạt động trong ngưỡng an toàn!")
            
            # Top overloaded vehicles
            if not vehicle_overload.empty:
                st.markdown("**Xe hay bị quá tải:**")
                overload_freq = vehicle_overload['vehicle_id'].value_counts().head(5)
                for vehicle, count in overload_freq.items():
                    st.error(f"🚗 {vehicle}: {count} lần")
    
    else:
        st.info("ℹ️ Cần dữ liệu ngày để phân tích quá tải chi tiết")

def create_distance_analysis_tab(df):
    """Tab 4: Phân tích quãng đường"""
    st.markdown("### 🛣️ Phân tích quãng đường chi tiết")
    
    if df.empty or 'distance_km' not in df.columns:
        st.warning("⚠️ Không có dữ liệu quãng đường")
        return
    
    # Ensure proper data types
    df['distance_km'] = df['distance_km'].apply(parse_distance)
    distance_data = df[df['distance_km'] > 0].copy()
    
    if distance_data.empty:
        st.warning("⚠️ Không có dữ liệu quãng đường hợp lệ")
        return
    
    # Distance by vehicle
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📊 Tổng quãng đường theo xe")
        vehicle_distance = distance_data.groupby('vehicle_id')['distance_km'].agg(['sum', 'count', 'mean']).reset_index()
        vehicle_distance.columns = ['vehicle_id', 'total_distance', 'trip_count', 'avg_distance']
        vehicle_distance = vehicle_distance.sort_values('total_distance', ascending=False)
        
        fig_vehicle_dist = px.bar(
            vehicle_distance.head(15),
            x='vehicle_id',
            y='total_distance',
            title="Top 15 xe chạy xa nhất",
            labels={'total_distance': 'Tổng quãng đường (km)', 'vehicle_id': 'Mã xe'},
            color='total_distance',
            color_continuous_scale='Viridis'
        )
        fig_vehicle_dist.update_layout(height=400)
        st.plotly_chart(fig_vehicle_dist, use_container_width=True)
    
    with col2:
        st.markdown("#### 📈 Xu hướng quãng đường theo thời gian")
        if 'date' in distance_data.columns:
            daily_distance = distance_data.groupby('date')['distance_km'].sum().reset_index()
            daily_distance = daily_distance.sort_values('date')
            
            fig_time_dist = px.line(
                daily_distance,
                x='date',
                y='distance_km',
                title="Tổng quãng đường theo ngày",
                labels={'distance_km': 'Quãng đường (km)', 'date': 'Ngày'}
            )
            fig_time_dist.update_layout(height=400)
            st.plotly_chart(fig_time_dist, use_container_width=True)
        else:
            st.info("Không có dữ liệu thời gian")
    
    # Distance distribution and efficiency
    col3, col4 = st.columns(2)
    
    with col3:
        st.markdown("#### 📊 Phân bố quãng đường mỗi chuyến")
        fig_dist_hist = px.histogram(
            distance_data,
            x='distance_km',
            nbins=25,
            title="Phân bố quãng đường chuyến xe",
            labels={'distance_km': 'Quãng đường (km)', 'count': 'Số chuyến'}
        )
        
        # Add statistics lines
        mean_distance = distance_data['distance_km'].mean()
        median_distance = distance_data['distance_km'].median()
        
        fig_dist_hist.add_vline(x=mean_distance, line_dash="dash", line_color="red",
                               annotation_text=f"TB: {mean_distance:.1f}km")
        fig_dist_hist.add_vline(x=median_distance, line_dash="dash", line_color="blue",
                               annotation_text=f"Trung vị: {median_distance:.1f}km")
        fig_dist_hist.update_layout(height=400)
        st.plotly_chart(fig_dist_hist, use_container_width=True)
    
    with col4:
        st.markdown("#### 🎯 Hiệu suất quãng đường theo xe")
        # Distance efficiency: km per hour
        if 'Thời gian' in distance_data.columns:
            # Create a copy to avoid modifying original data
            efficiency_data = distance_data.copy()
            efficiency_data['km_per_hour'] = efficiency_data['distance_km'] / efficiency_data['Thời gian']
            efficiency_data['km_per_hour'] = efficiency_data['km_per_hour'].replace([np.inf, -np.inf], np.nan)
            
            vehicle_efficiency = efficiency_data.groupby('vehicle_id')['km_per_hour'].mean().reset_index()
            vehicle_efficiency = vehicle_efficiency.sort_values('km_per_hour', ascending=False).head(15)
            
            fig_efficiency = px.bar(
                vehicle_efficiency,
                x='vehicle_id',
                y='km_per_hour',
                title="Tốc độ trung bình (km/h)",
                labels={'km_per_hour': 'Km/giờ', 'vehicle_id': 'Mã xe'},
                color='km_per_hour',
                color_continuous_scale='RdYlGn'
            )
            fig_efficiency.update_layout(height=400)
            st.plotly_chart(fig_efficiency, use_container_width=True)
        else:
            st.info("Không có dữ liệu thời gian để tính hiệu suất")
    
    # Area analysis
    if 'area_type' in distance_data.columns:
        col5, col6 = st.columns(2)
        
        with col5:
            st.markdown("#### 🏙️ Phân tích theo khu vực")
            area_stats = distance_data.groupby('area_type').agg({
                'distance_km': ['sum', 'mean', 'count']
            }).round(2)
            area_stats.columns = ['Tổng km', 'TB km/chuyến', 'Số chuyến']
            area_stats = area_stats.reset_index()
            
            fig_area = px.pie(
                area_stats,
                values='Tổng km',
                names='area_type',
                title="Phân bố quãng đường theo khu vực"
            )
            fig_area.update_layout(height=400)
            st.plotly_chart(fig_area, use_container_width=True)
        
        with col6:
            st.markdown("#### 📋 Thống kê theo khu vực")
            st.dataframe(area_stats, use_container_width=True, hide_index=True)
    
    # Distance statistics summary
    st.markdown("#### 📊 Tổng quan thống kê quãng đường")
    distance_stats = pd.DataFrame({
        'Chỉ số': [
            'Tổng quãng đường',
            'Quãng đường TB/chuyến',
            'Quãng đường dài nhất',
            'Quãng đường ngắn nhất',
            'Số chuyến có dữ liệu km'
        ],
        'Giá trị': [
            f"{distance_data['distance_km'].sum():,.1f} km",
            f"{distance_data['distance_km'].mean():,.1f} km",
            f"{distance_data['distance_km'].max():,.1f} km",
            f"{distance_data['distance_km'].min():,.1f} km",
            f"{len(distance_data):,} chuyến"
        ]
    })
    st.dataframe(distance_stats, use_container_width=True, hide_index=True)
    
def create_fuel_analysis_tab(df):
    """Tab 5: Phân tích nhiên liệu chi tiết - COMPLETELY REWRITTEN VERSION"""
    st.markdown("### ⛽ Phân tích nhiên liệu và định mức tiêu thụ")
    
    if df.empty:
        st.warning("⚠️ Không có dữ liệu để phân tích")
        return
    
    # Định mức nhiên liệu theo xe (lít/100km)
    FUEL_STANDARDS = {
        "50M-004.37": 18,
        "50M-002.19": 18,
        "50A-009.44": 16,
        "50A-007.39": 16,
        "50A-010.67": 17,
        "50A-018.35": 15,
        "51B-509.51": 17,
        "50A-019.90": 13,
        "50A-007.20": 20,
        "50A-004.55": 22,
        "50A-012.59": 10,
        "51B-330.67": 29
    }
    
    # Kiểm tra cột cần thiết
    if 'vehicle_id' not in df.columns:
        st.error("❌ Thiếu cột vehicle_id")
        return
        
    if 'fuel_liters' not in df.columns and 'distance_km' not in df.columns:
        st.error("❌ Thiếu cột fuel_liters hoặc distance_km")
        return
    
    # BƯỚC 1: Clean dữ liệu cơ bản - KHÔNG loại bỏ xe nào
    df_clean = df.copy()
    
    # Đảm bảo có cột fuel_liters và distance_km
    if 'fuel_liters' not in df_clean.columns:
        df_clean['fuel_liters'] = 0
    if 'distance_km' not in df_clean.columns:
        df_clean['distance_km'] = 0
        
    # Clean fuel_liters: chuyển về numeric, thay NaN = 0, loại bỏ giá trị âm và quá lớn
    df_clean['fuel_liters'] = pd.to_numeric(df_clean['fuel_liters'], errors='coerce').fillna(0)
    df_clean['fuel_liters'] = df_clean['fuel_liters'].apply(lambda x: max(0, min(x, 1000)) if pd.notna(x) else 0)
    
    # Clean distance_km: tương tự
    df_clean['distance_km'] = pd.to_numeric(df_clean['distance_km'], errors='coerce').fillna(0)
    df_clean['distance_km'] = df_clean['distance_km'].apply(lambda x: max(0, min(x, 5000)) if pd.notna(x) else 0)
    
    # BƯỚC 2: Tính toán cho từng xe - KHÔNG loại bỏ xe nào
    st.markdown("#### 📊 Debug - Thông tin dữ liệu")
    total_records = len(df_clean)
    total_vehicles = df_clean['vehicle_id'].nunique()
    records_with_fuel = len(df_clean[df_clean['fuel_liters'] > 0])
    records_with_distance = len(df_clean[df_clean['distance_km'] > 0])
    
    st.info(f"""
    **📊 Tổng quan dữ liệu:**
    - Tổng số records: {total_records:,}
    - Tổng số xe: {total_vehicles}
    - Records có fuel > 0: {records_with_fuel:,} ({records_with_fuel/total_records*100:.1f}%)
    - Records có distance > 0: {records_with_distance:,} ({records_with_distance/total_records*100:.1f}%)
    """)
    
    # BƯỚC 3: Tính toán cho từng xe
    vehicle_analysis = []
    all_vehicles = sorted(df_clean['vehicle_id'].unique())
    
    st.markdown(f"#### 🔍 Phân tích {len(all_vehicles)} xe")
    
    for vehicle_id in all_vehicles:
        vehicle_data = df_clean[df_clean['vehicle_id'] == vehicle_id].copy()
        
        # Thông tin cơ bản
        total_trips = len(vehicle_data)
        total_fuel = float(vehicle_data['fuel_liters'].sum())
        total_distance = float(vehicle_data['distance_km'].sum())
        
        # Số chuyến có fuel và distance
        trips_with_fuel = len(vehicle_data[vehicle_data['fuel_liters'] > 0])
        trips_with_distance = len(vehicle_data[vehicle_data['distance_km'] > 0])
        trips_with_both = len(vehicle_data[(vehicle_data['fuel_liters'] > 0) & (vehicle_data['distance_km'] > 0)])
        
        # Tính mức tiêu thụ
        if total_distance > 0 and total_fuel > 0:
            # Công thức đơn giản: tổng fuel / tổng distance * 100
            avg_consumption = (total_fuel / total_distance) * 100
        else:
            avg_consumption = 0.0
        
        # So sánh với định mức
        standard = FUEL_STANDARDS.get(vehicle_id, None)
        if standard and avg_consumption > 0:
            deviation = avg_consumption - standard
            deviation_percent = (deviation / standard) * 100
            
            if deviation > 2:
                status = "🔴 Vượt định mức"
                status_color = "red"
            elif deviation < -1:
                status = "🟢 Tiết kiệm"
                status_color = "green"
            else:
                status = "🟡 Trong định mức"
                status_color = "orange"
        else:
            deviation = 0
            deviation_percent = 0
            if standard is None:
                status = "⚪ Chưa có định mức"
            elif total_fuel == 0:
                status = "⚫ Không có dữ liệu fuel"
            elif total_distance == 0:
                status = "⚫ Không có dữ liệu distance"
            else:
                status = "⚫ Không có dữ liệu"
            status_color = "gray"
        
        # Thêm vào danh sách
        vehicle_analysis.append({
            'vehicle_id': vehicle_id,
            'total_trips': total_trips,
            'total_fuel': total_fuel,
            'total_distance': total_distance,
            'trips_with_fuel': trips_with_fuel,
            'trips_with_distance': trips_with_distance,
            'trips_with_both': trips_with_both,
            'avg_consumption': avg_consumption,
            'standard': standard if standard else 0,
            'deviation': deviation,
            'deviation_percent': deviation_percent,
            'status': status,
            'status_color': status_color
        })
    
    # Chuyển thành DataFrame
    vehicle_fuel_df = pd.DataFrame(vehicle_analysis)
    
    # BƯỚC 4: Hiển thị overview
    st.markdown("#### 📊 Tổng quan tiêu thụ nhiên liệu")
    
    # Chỉ tính cho xe có dữ liệu
    vehicles_with_data = vehicle_fuel_df[
        (vehicle_fuel_df['total_fuel'] > 0) & 
        (vehicle_fuel_df['total_distance'] > 0)
    ]
    
    total_fuel_fleet = vehicles_with_data['total_fuel'].sum()
    total_distance_fleet = vehicles_with_data['total_distance'].sum()
    avg_consumption_fleet = (total_fuel_fleet / total_distance_fleet * 100) if total_distance_fleet > 0 else 0
    
    vehicles_over_standard = len(vehicle_fuel_df[vehicle_fuel_df['deviation'] > 2])
    vehicles_efficient = len(vehicle_fuel_df[vehicle_fuel_df['deviation'] < -1])
    vehicles_no_data = len(vehicle_fuel_df[vehicle_fuel_df['avg_consumption'] == 0])
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="⛽ Tổng nhiên liệu",
            value=f"{total_fuel_fleet:,.1f} lít",
            help=f"Tổng lượng nhiên liệu của {len(vehicles_with_data)} xe có dữ liệu"
        )
    
    with col2:
        st.metric(
            label="📊 TB tiêu thụ đội xe", 
            value=f"{avg_consumption_fleet:.1f} L/100km",
            help="Mức tiêu thụ trung bình (tổng fuel / tổng km)"
        )
    
    with col3:
        st.metric(
            label="🔴 Xe vượt định mức",
            value=f"{vehicles_over_standard}",
            help="Xe tiêu thụ vượt định mức > 2L/100km"
        )
    
    with col4:
        st.metric(
            label="⚫ Xe thiếu dữ liệu",
            value=f"{vehicles_no_data}",
            help="Xe không có dữ liệu fuel hoặc distance"
        )
    
    # BƯỚC 5: Bảng chi tiết TẤT CẢ xe
    st.markdown("#### 📋 Bảng chi tiết TẤT CẢ xe")
    
    # Sắp xếp: xe có dữ liệu trước, theo mức tiêu thụ
    display_df = vehicle_fuel_df.copy()
    display_df['sort_key'] = display_df.apply(lambda x: (
        0 if x['avg_consumption'] > 0 else 1,  # Xe có dữ liệu trước
        -x['avg_consumption']  # Tiêu thụ cao trước
    ), axis=1)
    display_df = display_df.sort_values(['sort_key', 'vehicle_id'])
    
    # Tạo bảng hiển thị
    display_table = pd.DataFrame({
        'Mã xe': display_df['vehicle_id'],
        'Tổng chuyến': display_df['total_trips'],
        'Chuyến có fuel': display_df['trips_with_fuel'],
        'Chuyến có distance': display_df['trips_with_distance'],
        'Tổng fuel (L)': display_df['total_fuel'].round(1),
        'Tổng distance (km)': display_df['total_distance'].round(1),
        'Tiêu thụ (L/100km)': display_df['avg_consumption'].round(2),
        'Định mức (L/100km)': display_df['standard'],
        'Chênh lệch (L/100km)': display_df['deviation'].round(2),
        'Trạng thái': display_df['status']
    })
    
    # Style cho bảng
    def highlight_status(val):
        if '🔴' in str(val):
            return 'background-color: #ffebee'
        elif '🟢' in str(val):
            return 'background-color: #e8f5e8'
        elif '🟡' in str(val):
            return 'background-color: #fff8e1'
        elif '⚫' in str(val):
            return 'background-color: #f5f5f5'
        return ''
    
    st.dataframe(
        display_table.style.applymap(highlight_status, subset=['Trạng thái']),
        use_container_width=True,
        height=500
    )
    
    # BƯỚC 6: Biểu đồ so sánh
    st.markdown("#### 📊 Biểu đồ so sánh với định mức")
    
    # Chỉ hiển thị xe có cả dữ liệu và định mức
    chart_data = vehicle_fuel_df[
        (vehicle_fuel_df['avg_consumption'] > 0) & 
        (vehicle_fuel_df['standard'] > 0)
    ].copy()
    
    if not chart_data.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            # Biểu đồ so sánh
            fig_comparison = go.Figure()
            
            # Cột định mức
            fig_comparison.add_trace(go.Bar(
                name='Định mức',
                x=chart_data['vehicle_id'],
                y=chart_data['standard'],
                marker_color='lightblue',
                opacity=0.7
            ))
            
            # Cột thực tế với màu theo trạng thái
            colors = chart_data['status_color'].map({
                'red': 'red',
                'green': 'green',
                'orange': 'orange',
                'gray': 'gray'
            })
            
            fig_comparison.add_trace(go.Bar(
                name='Thực tế',
                x=chart_data['vehicle_id'],
                y=chart_data['avg_consumption'],
                marker_color=colors
            ))
            
            fig_comparison.update_layout(
                title="So sánh tiêu thụ thực tế vs định mức",
                xaxis_title="Mã xe",
                yaxis_title="L/100km",
                barmode='group',
                height=400
            )
            
            st.plotly_chart(fig_comparison, use_container_width=True)
        
        with col2:
            # Biểu đồ phân tán
            fig_scatter = px.scatter(
                chart_data,
                x='standard',
                y='avg_consumption',
                hover_data=['vehicle_id', 'total_trips'],
                title="Ma trận: Định mức vs Thực tế",
                labels={'standard': 'Định mức (L/100km)', 'avg_consumption': 'Thực tế (L/100km)'},
                color='status_color',
                color_discrete_map={'red': 'red', 'green': 'green', 'orange': 'orange'}
            )
            
            # Thêm đường y=x (lý tưởng)
            max_val = max(chart_data['standard'].max(), chart_data['avg_consumption'].max())
            fig_scatter.add_shape(
                type="line",
                x0=0, y0=0, x1=max_val, y1=max_val,
                line=dict(color="black", dash="dash"),
            )
            
            fig_scatter.update_layout(height=400)
            st.plotly_chart(fig_scatter, use_container_width=True)
    else:
        st.info("Không có xe nào có đủ dữ liệu và định mức để so sánh")
    
    # BƯỚC 7: Danh sách xe cần chú ý
    st.markdown("#### ⚠️ Xe cần chú ý")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🔴 Xe vượt định mức:**")
        over_vehicles = vehicle_fuel_df[vehicle_fuel_df['deviation'] > 2].sort_values('deviation', ascending=False)
        if not over_vehicles.empty:
            for _, vehicle in over_vehicles.iterrows():
                st.error(
                    f"🚗 **{vehicle['vehicle_id']}**: {vehicle['avg_consumption']:.1f}L/100km "
                    f"(định mức: {vehicle['standard']}L/100km, vượt: +{vehicle['deviation']:.1f}L)"
                )
        else:
            st.success("✅ Không có xe nào vượt định mức đáng kể!")
    
    with col2:
        st.markdown("**⚫ Xe thiếu dữ liệu:**")
        no_data_vehicles = vehicle_fuel_df[vehicle_fuel_df['avg_consumption'] == 0]
        if not no_data_vehicles.empty:
            for _, vehicle in no_data_vehicles.iterrows():
                st.warning(
                    f"🚗 **{vehicle['vehicle_id']}**: {vehicle['status']} "
                    f"(fuel: {vehicle['trips_with_fuel']}/{vehicle['total_trips']}, "
                    f"distance: {vehicle['trips_with_distance']}/{vehicle['total_trips']})"
                )
        else:
            st.success("✅ Tất cả xe đều có dữ liệu!")
    
    # BƯỚC 8: Chi phí nhiên liệu
    st.markdown("#### 💰 Ước tính chi phí nhiên liệu")
    
    fuel_price = st.number_input(
        "Giá nhiên liệu (VNĐ/lít):",
        value=25000,
        min_value=20000,
        max_value=35000,
        step=1000
    )
    
    total_fuel_cost = total_fuel_fleet * fuel_price
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label="💰 Tổng chi phí nhiên liệu",
            value=f"{total_fuel_cost:,.0f} VNĐ",
            help=f"Dựa trên {total_fuel_fleet:.1f}L × {fuel_price:,} VNĐ/L"
        )
    
    with col2:
        if total_distance_fleet > 0:
            cost_per_100km = (total_fuel_cost / total_distance_fleet) * 100
            st.metric(
                label="📊 Chi phí/100km",
                value=f"{cost_per_100km:,.0f} VNĐ",
                help="Chi phí nhiên liệu trung bình cho 100km"
            )
    
    with col3:
        # Tính tiết kiệm nếu đạt định mức
        potential_savings = 0
        for _, vehicle in vehicles_with_data.iterrows():
            if vehicle['standard'] > 0 and vehicle['deviation'] > 0:
                excess_consumption = (vehicle['deviation'] / 100) * vehicle['total_distance']
                potential_savings += excess_consumption * fuel_price
        
        st.metric(
            label="💸 Tiết kiệm tiềm năng",
            value=f"{potential_savings:,.0f} VNĐ",
            help="Số tiền có thể tiết kiệm nếu xe vượt định mức về đúng mức"
        )
    
    # BƯỚC 9: Debug chi tiết
    if st.checkbox("🔧 Debug - Xem tính toán chi tiết"):
        st.markdown("### 🔧 Debug - Tính toán chi tiết")
        
        selected_vehicle = st.selectbox(
            "Chọn xe để xem chi tiết:",
            options=all_vehicles,
            index=0
        )
        
        if selected_vehicle:
            vehicle_detail = df_clean[df_clean['vehicle_id'] == selected_vehicle].copy()
            vehicle_summary = vehicle_fuel_df[vehicle_fuel_df['vehicle_id'] == selected_vehicle].iloc[0]
            
            st.write(f"**Chi tiết xe {selected_vehicle}:**")
            st.write(f"- Tổng chuyến: {vehicle_summary['total_trips']}")
            st.write(f"- Chuyến có fuel > 0: {vehicle_summary['trips_with_fuel']}")
            st.write(f"- Chuyến có distance > 0: {vehicle_summary['trips_with_distance']}")
            st.write(f"- Tổng fuel: {vehicle_summary['total_fuel']:.1f}L")
            st.write(f"- Tổng distance: {vehicle_summary['total_distance']:.1f}km")
            st.write(f"- Tính toán: {vehicle_summary['total_fuel']:.1f} ÷ {vehicle_summary['total_distance']:.1f} × 100 = {vehicle_summary['avg_consumption']:.2f}L/100km")
            st.write(f"- Định mức: {vehicle_summary['standard']}L/100km")
            st.write(f"- Trạng thái: {vehicle_summary['status']}")
            
            st.markdown("**Sample dữ liệu thô:**")
            sample_data = vehicle_detail[['fuel_liters', 'distance_km']].head(10)
            st.dataframe(sample_data)

def create_export_report_tab(df, start_date, end_date):
    """Tab 6: Xuất báo cáo theo từng xe"""
    st.markdown("### 📊 Báo cáo theo từng xe")
    st.markdown(f"**📅 Khoảng thời gian:** {start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}")
    
    if df.empty:
        st.warning("⚠️ Không có dữ liệu để xuất báo cáo")
        return
    
    # Tính toán báo cáo cho từng xe
    vehicle_report = []
    
    for vehicle_id in sorted(df['vehicle_id'].unique()):
        vehicle_data = df[df['vehicle_id'] == vehicle_id].copy()
        
        # Đảm bảo dữ liệu đúng kiểu
        vehicle_data['revenue_vnd'] = pd.to_numeric(vehicle_data['revenue_vnd'], errors='coerce').fillna(0)
        vehicle_data['distance_km'] = pd.to_numeric(vehicle_data['distance_km'], errors='coerce').fillna(0)
        vehicle_data['fuel_liters'] = pd.to_numeric(vehicle_data['fuel_liters'], errors='coerce').fillna(0)
        
        # 1. BSX
        bsx = vehicle_id
        
        # 2. Tổng km
        total_km = vehicle_data['distance_km'].sum()
        
        # Phân loại theo nội/ngoại thành và có/không thu tiền
        # Nội thành
        noi_thanh = vehicle_data[vehicle_data['Nội thành/Ngoại thành'] == 'Nội thành'] if 'Nội thành/Ngoại thành' in vehicle_data.columns else pd.DataFrame()
        ngoai_thanh = vehicle_data[vehicle_data['Nội thành/Ngoại thành'] == 'Ngoại thành'] if 'Nội thành/Ngoại thành' in vehicle_data.columns else pd.DataFrame()
        
        # 3. Số chuyến nội thành không thu tiền (revenue = 0)
        chuyen_noi_thanh_ko_thu = len(noi_thanh[noi_thanh['revenue_vnd'] == 0]) if not noi_thanh.empty else 0
        
        # 4. Số chuyến nội thành có thu tiền (revenue > 0)
        chuyen_noi_thanh_co_thu = len(noi_thanh[noi_thanh['revenue_vnd'] > 0]) if not noi_thanh.empty else 0
        
        # 5. Số chuyến ngoại thành không thu tiền (revenue = 0)
        chuyen_ngoai_thanh_ko_thu = len(ngoai_thanh[ngoai_thanh['revenue_vnd'] == 0]) if not ngoai_thanh.empty else 0
        
        # 6. Số chuyến ngoại thành có thu tiền (revenue > 0)
        chuyen_ngoai_thanh_co_thu = len(ngoai_thanh[ngoai_thanh['revenue_vnd'] > 0]) if not ngoai_thanh.empty else 0
        
        # 7. Số tiền thu từ các chuyến nội thành
        tien_thu_noi_thanh = noi_thanh['revenue_vnd'].sum() if not noi_thanh.empty else 0
        
        # 8. Số tiền thu từ các chuyến ngoại thành
        tien_thu_ngoai_thanh = ngoai_thanh['revenue_vnd'].sum() if not ngoai_thanh.empty else 0
        
        # 9. Tổng tiền thu (nội + ngoại thành)
        tong_tien_thu = tien_thu_noi_thanh + tien_thu_ngoai_thanh
        
        # 10. Tổng nhiên liệu
        tong_nhien_lieu = vehicle_data['fuel_liters'].sum()
        
        vehicle_report.append({
            'BSX': bsx,
            'Tổng km': round(total_km, 1),
            'Chuyến nội thành (không thu tiền)': chuyen_noi_thanh_ko_thu,
            'Chuyến nội thành (có thu tiền)': chuyen_noi_thanh_co_thu,
            'Chuyến ngoại thành (không thu tiền)': chuyen_ngoai_thanh_ko_thu,
            'Chuyến ngoại thành (có thu tiền)': chuyen_ngoai_thanh_co_thu,
            'Tiền thu nội thành (VNĐ)': round(tien_thu_noi_thanh, 0),
            'Tiền thu ngoại thành (VNĐ)': round(tien_thu_ngoai_thanh, 0),
            'Tổng tiền thu (VNĐ)': round(tong_tien_thu, 0),
            'Tổng nhiên liệu (Lít)': round(tong_nhien_lieu, 1)
        })
    
    # Tạo DataFrame báo cáo
    report_df = pd.DataFrame(vehicle_report)
    
    if report_df.empty:
        st.warning("⚠️ Không có dữ liệu để tạo báo cáo")
        return
    
    # Sắp xếp theo BSX
    report_df = report_df.sort_values('BSX')
    
    # Hiển thị bảng báo cáo
    st.markdown("#### 📋 Bảng báo cáo chi tiết")
    
    # Format hiển thị
    styled_df = report_df.style.format({
        'Tổng km': '{:.1f}',
        'Tiền thu nội thành (VNĐ)': '{:,.0f}',
        'Tiền thu ngoại thành (VNĐ)': '{:,.0f}',
        'Tổng tiền thu (VNĐ)': '{:,.0f}',
        'Tổng nhiên liệu (Lít)': '{:.1f}'
    })
    
    st.dataframe(styled_df, use_container_width=True, height=400)
    
    # Thống kê tổng hợp
    st.markdown("#### 📊 Thống kê tổng hợp")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="🚗 Tổng số xe",
            value=f"{len(report_df)}",
            help="Số xe có hoạt động trong khoảng thời gian"
        )
    
    with col2:
        st.metric(
            label="🛣️ Tổng km",
            value=f"{report_df['Tổng km'].sum():,.1f} km",
            help="Tổng quãng đường của tất cả xe"
        )
    
    with col3:
        st.metric(
            label="💰 Tổng doanh thu",
            value=f"{report_df['Tổng tiền thu (VNĐ)'].sum():,.0f} VNĐ",
            help="Tổng doanh thu của tất cả xe"
        )
    
    with col4:
        st.metric(
            label="⛽ Tổng nhiên liệu",
            value=f"{report_df['Tổng nhiên liệu (Lít)'].sum():,.1f} L",
            help="Tổng nhiên liệu tiêu thụ của tất cả xe"
        )
    
    # Phân tích theo khu vực
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🏙️ Thống kê chuyến nội thành")
        tong_chuyen_noi_thanh = report_df['Chuyến nội thành (không thu tiền)'].sum() + report_df['Chuyến nội thành (có thu tiền)'].sum()
        tong_tien_noi_thanh = report_df['Tiền thu nội thành (VNĐ)'].sum()
        
        st.info(f"""
        📈 **Chuyến không thu tiền:** {report_df['Chuyến nội thành (không thu tiền)'].sum():,}
        💰 **Chuyến có thu tiền:** {report_df['Chuyến nội thành (có thu tiền)'].sum():,}
        📊 **Tổng chuyến:** {tong_chuyen_noi_thanh:,}
        💵 **Tổng doanh thu:** {tong_tien_noi_thanh:,.0f} VNĐ
        """)
    
    with col2:
        st.markdown("#### 🌆 Thống kê chuyến ngoại thành")
        tong_chuyen_ngoai_thanh = report_df['Chuyến ngoại thành (không thu tiền)'].sum() + report_df['Chuyến ngoại thành (có thu tiền)'].sum()
        tong_tien_ngoai_thanh = report_df['Tiền thu ngoại thành (VNĐ)'].sum()
        
        st.info(f"""
        📈 **Chuyến không thu tiền:** {report_df['Chuyến ngoại thành (không thu tiền)'].sum():,}
        💰 **Chuyến có thu tiền:** {report_df['Chuyến ngoại thành (có thu tiền)'].sum():,}
        📊 **Tổng chuyến:** {tong_chuyen_ngoai_thanh:,}
        💵 **Tổng doanh thu:** {tong_tien_ngoai_thanh:,.0f} VNĐ
        """)
    
    # Biểu đồ so sánh
    st.markdown("#### 📊 Biểu đồ so sánh")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Biểu đồ doanh thu theo xe
        top_10_revenue = report_df.nlargest(10, 'Tổng tiền thu (VNĐ)')
        
        if not top_10_revenue.empty:
            fig_revenue = px.bar(
                top_10_revenue,
                x='BSX',
                y='Tổng tiền thu (VNĐ)',
                title="Top 10 xe có doanh thu cao nhất",
                labels={'Tổng tiền thu (VNĐ)': 'Doanh thu (VNĐ)', 'BSX': 'Biển số xe'},
                color='Tổng tiền thu (VNĐ)',
                color_continuous_scale='Blues'
            )
            fig_revenue.update_layout(height=400)
            st.plotly_chart(fig_revenue, use_container_width=True)
    
    with col2:
        # Biểu đồ km theo xe
        top_10_km = report_df.nlargest(10, 'Tổng km')
        
        if not top_10_km.empty:
            fig_km = px.bar(
                top_10_km,
                x='BSX',
                y='Tổng km',
                title="Top 10 xe chạy xa nhất",
                labels={'Tổng km': 'Quãng đường (km)', 'BSX': 'Biển số xe'},
                color='Tổng km',
                color_continuous_scale='Greens'
            )
            fig_km.update_layout(height=400)
            st.plotly_chart(fig_km, use_container_width=True)
    
    # Xuất file
    st.markdown("#### 💾 Xuất báo cáo")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Xuất Excel
        excel_filename = f"bao_cao_xe_{start_date.strftime('%d%m%Y')}_{end_date.strftime('%d%m%Y')}.xlsx"
        
        try:
            from io import BytesIO
            output = BytesIO()
            
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                # Sheet chính - báo cáo chi tiết
                report_df.to_excel(writer, sheet_name='Báo cáo chi tiết', index=False)
                
                # Sheet tổng hợp
                summary_data = {
                    'Chỉ số': [
                        'Tổng số xe',
                        'Tổng km',
                        'Tổng chuyến nội thành',
                        'Tổng chuyến ngoại thành',
                        'Tổng doanh thu nội thành',
                        'Tổng doanh thu ngoại thành',
                        'Tổng doanh thu',
                        'Tổng nhiên liệu'
                    ],
                    'Giá trị': [
                        len(report_df),
                        f"{report_df['Tổng km'].sum():.1f} km",
                        tong_chuyen_noi_thanh,
                        tong_chuyen_ngoai_thanh,
                        f"{tong_tien_noi_thanh:,.0f} VNĐ",
                        f"{tong_tien_ngoai_thanh:,.0f} VNĐ",
                        f"{report_df['Tổng tiền thu (VNĐ)'].sum():,.0f} VNĐ",
                        f"{report_df['Tổng nhiên liệu (Lít)'].sum():.1f} L"
                    ]
                }
                
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Tổng hợp', index=False)
                
                # Thêm metadata
                metadata = pd.DataFrame({
                    'Thông tin': [
                        'Khoảng thời gian',
                        'Ngày tạo báo cáo',
                        'Số xe có hoạt động',
                        'Tổng chuyến',
                        'Ghi chú'
                    ],
                    'Chi tiết': [
                        f"{start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}",
                        datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                        len(report_df),
                        len(df),
                        'Báo cáo được tạo từ Dashboard Quản lý Tổ Xe'
                    ]
                })
                metadata.to_excel(writer, sheet_name='Thông tin', index=False)
            
            output.seek(0)
            
            st.download_button(
                label="📥 Tải Excel",
                data=output.getvalue(),
                file_name=excel_filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
            
        except Exception as e:
            st.error(f"❌ Lỗi tạo file Excel: {e}")
    
    with col2:
        # Xuất CSV
        csv_filename = f"bao_cao_xe_{start_date.strftime('%d%m%Y')}_{end_date.strftime('%d%m%Y')}.csv"
        csv_data = report_df.to_csv(index=False, encoding='utf-8-sig')
        
        st.download_button(
            label="📥 Tải CSV",
            data=csv_data,
            file_name=csv_filename,
            mime="text/csv",
            use_container_width=True
        )
    
    with col3:
        # In báo cáo
        if st.button("🖨️ In báo cáo", use_container_width=True):
            st.info("💡 Sử dụng Ctrl+P để in trang hoặc xuất PDF từ trình duyệt")

def create_detailed_analysis_section(df):
    """Create detailed analysis section with tabs - UPDATED with Export tab"""
    st.markdown("---")
    st.markdown("## 📈 Phân tích chi tiết và Biểu đồ trực quan")
    
    if df.empty:
        st.warning("⚠️ Không có dữ liệu để phân tích")
        return
    
    # Ensure we have required packages
    try:
        import plotly.express as px
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
    except ImportError:
        st.error("❌ Cần cài đặt plotly: pip install plotly")
        st.info("Chạy lệnh: pip install plotly")
        return
    
    # Create tabs - ADDED 6th tab
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "💰 Doanh thu", 
        "🚗 Hiệu suất xe", 
        "⚡ Phân tích quá tải", 
        "🛣️ Phân tích quãng đường",
        "⛽ Phân tích nhiên liệu",
        "📊 Xuất báo cáo"
    ])
    
    with tab1:
        create_revenue_analysis_tab(df)
    
    with tab2:
        create_vehicle_efficiency_tab(df)
    
    with tab3:
        create_overload_analysis_tab(df)
    
    with tab4:
        create_distance_analysis_tab(df)

    with tab5:
        create_fuel_analysis_tab(df)
    
    with tab6:
        # Get date range from sidebar filters (from session state)
        if 'date_filter_start' in st.session_state and 'date_filter_end' in st.session_state:
            start_date = st.session_state.date_filter_start
            end_date = st.session_state.date_filter_end
        else:
            # Fallback to data range if session state not available
            min_date, max_date = get_date_range_from_data(df)
            start_date = min_date
            end_date = max_date
        
        create_export_report_tab(df, start_date, end_date)

def create_driver_performance_table(df):
    """Create driver performance table using English columns"""
    st.markdown("## 👨‍💼 Hiệu suất tài xế")
    
    if df.empty or 'driver_name' not in df.columns:
        st.warning("⚠️ Không có dữ liệu tài xế")
        return
    
    # FIXED: Ensure duration is properly parsed
    df = ensure_duration_parsed(df)
    
    # Ensure datetime conversion
    try:
        if 'record_date' in df.columns:
            df['record_date'] = pd.to_datetime(df['record_date'], format='%m/%d/%Y', errors='coerce')
            df['date'] = df['record_date'].dt.date
    except:
        pass
    
    # Ensure numeric columns
    if 'revenue_vnd' in df.columns:
        df['revenue_vnd'] = pd.to_numeric(df['revenue_vnd'], errors='coerce').fillna(0)
    else:
        df['revenue_vnd'] = 0

    # FIXED: Duration is already parsed by ensure_duration_parsed()
    # Remove the redundant parsing that was causing issues
    
    # Calculate metrics per driver
    drivers = df['driver_name'].unique()
    results = []
    
    for driver in drivers:
        driver_data = df[df['driver_name'] == driver]
        
        # Basic metrics
        total_trips = len(driver_data)
        total_revenue = float(driver_data['revenue_vnd'].sum())
        
        # FIXED: Duration calculation - filter out invalid values
        valid_duration_data = driver_data[
            driver_data['Thời gian'].notna() & 
            (driver_data['Thời gian'] >= 0) & 
            (driver_data['Thời gian'] <= 24)
        ]
        total_hours = float(valid_duration_data['Thời gian'].sum())
        
        # Days calculation
        if 'date' in driver_data.columns:
            active_days = driver_data['date'].nunique()
        else:
            active_days = 30  # Default
        
        # Derived metrics
        trips_per_day = (float(total_trips) / float(active_days)) if active_days > 0 else 0.0
        hours_per_day = (total_hours / float(active_days)) if active_days > 0 else 0.0
        
        results.append({
            'Tên': driver,
            'Số chuyến': total_trips,
            'Tổng doanh thu': round(total_revenue, 0),
            'Tổng giờ lái': round(total_hours, 1),
            'Số ngày làm việc': active_days,
            'Chuyến/ngày': round(trips_per_day, 1),
            'Giờ lái/ngày': round(hours_per_day, 1)
        })
    
    # Create DataFrame
    driver_display = pd.DataFrame(results)
    driver_display = driver_display.set_index('Tên').sort_values('Tổng doanh thu', ascending=False)
    
    # Display table
    st.dataframe(
        driver_display.style.format({
            'Tổng doanh thu': '{:,.0f}',
            'Tổng giờ lái': '{:.1f}',
            'Chuyến/ngày': '{:.1f}',
            'Giờ lái/ngày': '{:.1f}'
        }),
        use_container_width=True,
        height=400
    )

def main():
    """Main dashboard function - Complete version with all features"""
    # HEADER: logo + title on one line (flexbox)
    try:
        # Encode logo to base64 for inline <img>
        script_dir = os.path.dirname(os.path.abspath(__file__))
        logo_base64 = ""
        # Check for logo.png in current directory first, then in ./assets/
        for p in [
            os.path.join(script_dir, "logo.png"),                      # 1️⃣ same-level logo
            os.path.join(script_dir, "assets", "logo.png")            # 2️⃣ assets folder
        ]:
            if os.path.exists(p):
                with open(p, "rb") as f:
                    logo_base64 = base64.b64encode(f.read()).decode()
                break
    except Exception:
        logo_base64 = ""

    # Build logo HTML (fallback emoji if logo not found)
    if logo_base64:
        logo_html = f"<img src='data:image/png;base64,{logo_base64}' style='height:150px; width:auto;' />"
    else:
        logo_html = "<div style='font-size:2.5rem; margin-right:12px;'>🏥</div>"

    header_html = f"""
    <div style='
        width:100%;
        display:flex;
        align-items:center;
        justify-content:center;
        gap:12px;
        padding:30px 0;
        background:#ffffff;
        border-radius:15px;
        margin-bottom:30px;
    '>
        <h1 style='
            color:#1f77b4;
            margin:0;
            font-size:3.2rem;
            font-weight:bold;
            font-family:"Segoe UI", Arial, sans-serif;
            text-shadow:2px 2px 4px rgba(0,0,0,0.1);
            letter-spacing:1px;
            text-align:center;
        '>Dashboard Quản lý Phương tiện vận chuyển tại Bệnh viện Đại học Y Dược TP. Hồ Chí Minh</h1>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)
    
    # Load data first
    with st.spinner("📊 Đang tải dữ liệu từ GitHub..."):
        df_raw = load_data_from_github()
    
    if df_raw.empty:
        st.warning("⚠️ Không có dữ liệu từ GitHub repository")
        st.info("💡 Click 'Sync dữ liệu mới' để lấy dữ liệu từ Google Sheets")
        return
    
    # Sidebar controls
    st.sidebar.markdown("## 🔧 Điều khiển Dashboard")
    
    # Show column mapping info
    with st.sidebar.expander("📋 Column Mapping Guide"):
        st.write("**Vietnamese → English:**")
        for viet, eng in COLUMN_MAPPING.items():
            if eng is not None:
                st.write(f"• {viet} → `{eng}`")
            else:
                st.write(f"• ~~{viet}~~ → Dropped")
    
    # Sync button
    if st.sidebar.button("🔄 Sync dữ liệu mới", type="primary", use_container_width=True):
        success = run_sync_script()
        if success:
            st.cache_data.clear()
            st.rerun()
    
    # Last sync info
    if 'last_sync' in st.session_state:
        st.sidebar.success(f"🕐 Sync cuối: {st.session_state.last_sync.strftime('%H:%M:%S %d/%m/%Y')}")
    
    # Manual refresh button
    if st.sidebar.button("🔄 Làm mới Dashboard", help="Reload dữ liệu từ GitHub"):
        # Clear date filters when refreshing data
        if 'date_filter_start' in st.session_state:
            del st.session_state.date_filter_start
        if 'date_filter_end' in st.session_state:
            del st.session_state.date_filter_end
        st.cache_data.clear()
        st.rerun()
    
    st.sidebar.markdown("---")
    
    # DATE FILTER - Apply first
    df_filtered, start_date, end_date = create_date_filter_sidebar(df_raw)
    
    st.sidebar.markdown("---")
    
    # VEHICLE & DRIVER FILTERS - Apply second
    df_final = create_vehicle_filter_sidebar(df_filtered)
    
    # Show filtered data stats
    st.sidebar.markdown("### 📊 Kết quả lọc")
    if not df_final.empty:
        vehicles_count = df_final['vehicle_id'].nunique() if 'vehicle_id' in df_final.columns else 0
        drivers_count = df_final['driver_name'].nunique() if 'driver_name' in df_final.columns else 0
        
        st.sidebar.metric("📈 Tổng chuyến", f"{len(df_final):,}")
        st.sidebar.metric("🚗 Số xe", f"{vehicles_count}")
        st.sidebar.metric("👨‍💼 Số tài xế", f"{drivers_count}")
        
        # Show percentage of total data
        percentage = (len(df_final) / len(df_raw) * 100) if len(df_raw) > 0 else 0
        st.sidebar.info(f"📊 {percentage:.1f}% tổng dữ liệu")
    else:
        st.sidebar.error("❌ Không có dữ liệu sau khi lọc")
        st.warning("⚠️ Không có dữ liệu phù hợp với bộ lọc hiện tại")
        return
    
    # Show available columns after filtering
    with st.sidebar.expander("📋 Mapped Columns"):
        for col in df_final.columns:
            non_null_count = df_final[col].notna().sum()
            st.write(f"• `{col}`: {non_null_count}/{len(df_final)}")
    
    # Reset filters button
    if st.sidebar.button("🔄 Reset tất cả bộ lọc", help="Quay về dữ liệu gốc"):
        # Clear session state for filters
        if 'date_filter_start' in st.session_state:
            del st.session_state.date_filter_start
        if 'date_filter_end' in st.session_state:
            del st.session_state.date_filter_end
        st.sidebar.success("✅ Đã reset bộ lọc ngày!")
        st.rerun()
    
    # Dashboard sections with filtered data
    st.markdown(f"## 📊 Báo cáo từ {start_date.strftime('%d/%m/%Y')} đến {end_date.strftime('%d/%m/%Y')}")
    
    create_metrics_overview(df_final)
    
    st.markdown("---")
    
    create_frequency_metrics(df_final)
    
    st.markdown("---")
    
    create_vehicle_performance_table(df_final)
    
    st.markdown("---")
    
    create_driver_performance_table(df_final)
    
    # NEW: Detailed Analysis Section with Tabs
    create_detailed_analysis_section(df_final)
    
    # Debug section for development
    with st.sidebar.expander("🔍 Debug Info"):
        st.write("**Sample Filtered Data (first 3 rows):**")
        if not df_final.empty:
            st.dataframe(df_final.head(3))
        
        st.write("**Column Data Types:**")
        for col in df_final.columns:
            st.write(f"• `{col}`: {df_final[col].dtype}")
        
        st.write("**Filter Summary:**")
        st.write(f"• Raw data: {len(df_raw):,} records")
        st.write(f"• After filters: {len(df_final):,} records")
        st.write(f"• Date range: {start_date} to {end_date}")

if __name__ == "__main__":
    main()
