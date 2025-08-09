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
    
    # Core time fields
    'start_time': 'start_time',
    'end_time': 'end_time', 
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
    if 'duration_hours' not in df.columns:
        return df
    
    # Kiểm tra xem cột đã là numeric chưa
    if not pd.api.types.is_numeric_dtype(df['duration_hours']):
        # Nếu chưa, parse từ string
        df['duration_hours'] = df['duration_hours'].apply(parse_duration_to_hours)
    else:
        # Nếu đã là numeric nhưng có thể có NaN, fill 0
        df['duration_hours'] = df['duration_hours'].fillna(0)
    
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
        if 'duration_hours' in df.columns:
            df['duration_hours'] = df['duration_hours'].apply(parse_duration_to_hours)
        
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

        # STEP 5: Prefix vehicle_id based on vehicle_type
        if 'vehicle_id' in df.columns and 'vehicle_type' in df.columns:
            def _add_prefix(vid, vtype):
                """Return vehicle_id with type prefix (HC_ or CT_)."""
                if pd.isna(vid):
                    return vid
                vid_str = str(vid)
                if vtype == 'Hành chính' and not vid_str.startswith('HC_'):
                    return f'HC_{vid_str}'
                if vtype == 'Cứu thương' and not vid_str.startswith('CT_'):
                    return f'CT_{vid_str}'
                return vid_str
            # Apply prefixing
            df['vehicle_id'] = df.apply(lambda r: _add_prefix(r['vehicle_id'], r['vehicle_type']), axis=1)
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
    # Tháng này (current month)
        if st.button("Tháng này", use_container_width=True, key="btn_this_month"):
            today = datetime.now().date()
            st.session_state.date_filter_start = today.replace(day=1)
            st.session_state.date_filter_end = min(today, max_date)
            st.rerun()

        # Tháng trước (previous month)
        if st.button("Tháng trc", use_container_width=True, key="btn_prev_month"):
            today = datetime.now().date()
            first_day_current_month = today.replace(day=1)
            last_day_prev_month = first_day_current_month - pd.Timedelta(days=1)
            first_day_prev_month = last_day_prev_month.replace(day=1)
            st.session_state.date_filter_start = first_day_prev_month
            st.session_state.date_filter_end = min(last_day_prev_month, max_date)
            st.rerun()

    with col2:
        # Tuần này (current week)
        if st.button("Tuần này", use_container_width=True, key="btn_this_week"):
            today = datetime.now().date()
            start_of_week = today - pd.Timedelta(days=today.weekday())  # Monday as first day
            st.session_state.date_filter_start = start_of_week
            st.session_state.date_filter_end = min(today, max_date)
            st.rerun()

        # Tất cả (all available data)
        if st.button("Tất cả", use_container_width=True, key="btn_all_data"):
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

def create_metrics_overview(df):
    """Create overview metrics using English column names"""
    if df.empty:
        st.warning("⚠️ Không có dữ liệu để hiển thị")
        return
    
    st.markdown("## 📊 Tổng quan hoạt động")
    
    # FIXED: Ensure duration is properly parsed
    df = ensure_duration_parsed(df)
    
    # Use ALL data without any filtering for total trips
    total_trips = len(df)
    
    # FIXED: Vehicle count - only count valid vehicle IDs
    if 'vehicle_id' in df.columns:
        valid_vehicles = df[
            df['vehicle_id'].notna() & 
            (df['vehicle_id'].astype(str).str.strip() != '') & 
            (df['vehicle_id'] != 'nan') &
            (df['vehicle_id'] != 'NaN')
        ]
        total_vehicles = valid_vehicles['vehicle_id'].nunique()
    else:
        total_vehicles = 0
    
    # FIXED: Driver count - only count valid driver names
    if 'driver_name' in df.columns:
        valid_drivers = df[
            df['driver_name'].notna() & 
            (df['driver_name'].astype(str).str.strip() != '') & 
            (df['driver_name'] != 'nan') &
            (df['driver_name'] != 'NaN')
        ]
        total_drivers = valid_drivers['driver_name'].nunique()
    else:
        total_drivers = 0
    
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
    if 'duration_hours' in df.columns:
        # Filter out invalid time data (negative or extremely large values)
        valid_time_data = df[
            df['duration_hours'].notna() & 
            (df['duration_hours'] >= 0) & 
            (df['duration_hours'] <= 24)  # Reasonable daily limit
        ]
        total_hours = valid_time_data['duration_hours'].sum()
        avg_hours_per_trip = valid_time_data['duration_hours'].mean() if len(valid_time_data) > 0 else 0
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
    if 'duration_hours' not in df.columns:
        df['duration_hours'] = 0
        
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
            vehicle_data['duration_hours'].notna() & 
            (vehicle_data['duration_hours'] >= 0) & 
            (vehicle_data['duration_hours'] <= 24)
        ]
        total_hours = float(valid_duration_data['duration_hours'].sum())
        
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
    
    # Ensure date parsing with correct format
    if 'record_date' in revenue_data.columns:
        # Parse dd/mm/yyyy format specifically
        revenue_data['record_date'] = pd.to_datetime(revenue_data['record_date'], format='%d/%m/%Y', errors='coerce')
        revenue_data['date'] = revenue_data['record_date'].dt.date
        revenue_data['parsed_date'] = revenue_data['record_date']  # Keep datetime for week calculations
    else:
        revenue_data['parsed_date'] = None
    
    # Create daily_revenue for later use
    daily_revenue = pd.DataFrame()
    if 'date' in revenue_data.columns and revenue_data['date'].notna().any():
        daily_revenue = revenue_data.groupby('date')['revenue_vnd'].sum().reset_index()
        daily_revenue = daily_revenue.sort_values('date')
    
    # =================== OVERVIEW METRICS ===================
    st.markdown("#### 📊 Tổng quan doanh thu")
    
    total_revenue = revenue_data['revenue_vnd'].sum()
    avg_revenue_per_trip = revenue_data['revenue_vnd'].mean()
    total_revenue_trips = len(revenue_data)
    unique_vehicles = revenue_data['vehicle_id'].nunique() if 'vehicle_id' in revenue_data.columns else 0
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("💰 Tổng doanh thu", f"{total_revenue:,.0f} VNĐ")
    with col2:
        st.metric("📊 TB/chuyến", f"{avg_revenue_per_trip:,.0f} VNĐ")
    with col3:
        st.metric("🚗 Số chuyến có DT", f"{total_revenue_trips:,}")
    with col4:
        st.metric("🚙 Xe tham gia", f"{unique_vehicles}")
    
    # =================== MAIN CHARTS ===================
    st.markdown("#### 📊 Biểu đồ phân tích chính")
    
    # Row 1: Top vehicles and time trend
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("##### 📊 Doanh thu theo xe")
        if 'vehicle_id' in revenue_data.columns:
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
            fig_vehicle.update_xaxes(tickangle=45)
            st.plotly_chart(fig_vehicle, use_container_width=True)
        else:
            st.info("Không có dữ liệu xe")
    
    with col2:
        st.markdown("##### 📈 Xu hướng doanh thu theo thời gian")
        if not daily_revenue.empty:
            # Add moving average
            daily_revenue_plot = daily_revenue.copy()
            daily_revenue_plot['MA_7'] = daily_revenue_plot['revenue_vnd'].rolling(window=7, min_periods=1).mean()
            
            fig_time = go.Figure()
            fig_time.add_trace(go.Scatter(
                x=daily_revenue_plot['date'],
                y=daily_revenue_plot['revenue_vnd'],
                mode='lines+markers',
                name='Doanh thu hàng ngày',
                line=dict(color='lightblue', width=1),
                marker=dict(size=4)
            ))
            fig_time.add_trace(go.Scatter(
                x=daily_revenue_plot['date'],
                y=daily_revenue_plot['MA_7'],
                mode='lines',
                name='Đường xu hướng (7 ngày)',
                line=dict(color='red', width=2)
            ))
            fig_time.update_layout(
                title="Xu hướng doanh thu theo ngày",
                xaxis_title="Ngày",
                yaxis_title="Doanh thu (VNĐ)",
                height=400
            )
            st.plotly_chart(fig_time, use_container_width=True)
        else:
            st.info("Không thể parse dữ liệu thời gian từ record_date (format dd/mm/yyyy)")
    
    # =================== GROWTH ANALYSIS ===================
    st.markdown("#### 📈 Phân tích tăng trưởng doanh thu")
    
    if not daily_revenue.empty and len(daily_revenue) > 1:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### 📊 Tăng trưởng theo ngày")
            
            # Calculate daily growth
            daily_revenue_sorted = daily_revenue.sort_values('date').copy()
            daily_revenue_sorted['prev_revenue'] = daily_revenue_sorted['revenue_vnd'].shift(1)
            daily_revenue_sorted['growth_amount'] = daily_revenue_sorted['revenue_vnd'] - daily_revenue_sorted['prev_revenue']
            daily_revenue_sorted['growth_percent'] = (daily_revenue_sorted['growth_amount'] / daily_revenue_sorted['prev_revenue'] * 100).fillna(0)
            
            # Filter out extreme values for better visualization
            growth_data = daily_revenue_sorted[
                (daily_revenue_sorted['growth_percent'].abs() <= 500) & 
                (daily_revenue_sorted['growth_percent'].notna())
            ]
            
            if not growth_data.empty:
                fig_growth = px.bar(
                    growth_data,
                    x='date',
                    y='growth_percent',
                    title="Tăng trưởng doanh thu (% so với ngày trước)",
                    labels={'growth_percent': 'Tăng trưởng (%)', 'date': 'Ngày'},
                    color='growth_percent',
                    color_continuous_scale='RdYlGn',
                    color_continuous_midpoint=0
                )
                fig_growth.add_hline(y=0, line_dash="dash", line_color="black")
                fig_growth.update_layout(height=400)
                st.plotly_chart(fig_growth, use_container_width=True)
                
                # Growth stats
                avg_growth = growth_data['growth_percent'].mean()
                positive_days = len(growth_data[growth_data['growth_percent'] > 0])
                negative_days = len(growth_data[growth_data['growth_percent'] < 0])
                
                st.info(f"""
                **📊 Thống kê tăng trưởng:**
                - Tăng trưởng TB: {avg_growth:.1f}%/ngày
                - Ngày tăng: {positive_days} | Ngày giảm: {negative_days}
                - Tỷ lệ ngày tăng: {positive_days/(positive_days+negative_days)*100:.1f}%
                """)
            else:
                st.info("Không đủ dữ liệu để tính tăng trưởng")
        
        with col2:
            st.markdown("##### 📊 So sánh theo khoảng thời gian")
            
            # Check if we have valid parsed dates
            if 'parsed_date' in revenue_data.columns and revenue_data['parsed_date'].notna().any():
                # Weekly comparison using properly parsed dates
                valid_date_data = revenue_data[revenue_data['parsed_date'].notna()].copy()
                valid_date_data['week'] = valid_date_data['parsed_date'].dt.isocalendar().week
                valid_date_data['year'] = valid_date_data['parsed_date'].dt.year
                valid_date_data['year_week'] = valid_date_data['year'].astype(str) + '-W' + valid_date_data['week'].astype(str).str.zfill(2)
                
                weekly_revenue = valid_date_data.groupby('year_week')['revenue_vnd'].sum().reset_index()
                weekly_revenue = weekly_revenue.sort_values('year_week')
                
                if len(weekly_revenue) >= 2:
                    weekly_revenue['prev_week'] = weekly_revenue['revenue_vnd'].shift(1)
                    weekly_revenue['week_growth'] = ((weekly_revenue['revenue_vnd'] - weekly_revenue['prev_week']) / weekly_revenue['prev_week'] * 100).fillna(0)
                    
                    fig_weekly = px.bar(
                        weekly_revenue.tail(8),  # Last 8 weeks
                        x='year_week',
                        y='week_growth',
                        title="Tăng trưởng doanh thu theo tuần (%)",
                        labels={'week_growth': 'Tăng trưởng (%)', 'year_week': 'Tuần'},
                        color='week_growth',
                        color_continuous_scale='RdYlGn',
                        color_continuous_midpoint=0
                    )
                    fig_weekly.add_hline(y=0, line_dash="dash", line_color="black")
                    fig_weekly.update_layout(height=400)
                    fig_weekly.update_xaxes(tickangle=45)
                    st.plotly_chart(fig_weekly, use_container_width=True)
                    
                    # Weekly stats
                    avg_weekly_growth = weekly_revenue['week_growth'].mean()
                    positive_weeks = len(weekly_revenue[weekly_revenue['week_growth'] > 0])
                    negative_weeks = len(weekly_revenue[weekly_revenue['week_growth'] < 0])
                    
                    st.info(f"""
                    **📊 Thống kê theo tuần:**
                    - Tăng trưởng TB: {avg_weekly_growth:.1f}%/tuần
                    - Tuần tăng: {positive_weeks} | Tuần giảm: {negative_weeks}
                    - Có dữ liệu: {len(weekly_revenue)} tuần
                    """)
                else:
                    st.info("Không đủ dữ liệu cho phân tích theo tuần (cần ít nhất 2 tuần)")
            else:
                st.warning("⚠️ Không thể parse ngày từ record_date (format dd/mm/yyyy) để phân tích theo tuần")
    
    # =================== ADVANCED ANALYSIS ===================
    st.markdown("#### 🔍 Phân tích chuyên sâu")
    
    # Row 3: Distribution and comparison
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("##### 📊 Phân bố doanh thu mỗi chuyến")
        
        # Create histogram with statistics
        fig_dist = px.histogram(
            revenue_data,
            x='revenue_vnd',
            nbins=25,
            title="Phân bố doanh thu mỗi chuyến",
            labels={'revenue_vnd': 'Doanh thu (VNĐ)', 'count': 'Số chuyến'}
        )
        
        # Add statistics lines
        mean_revenue = revenue_data['revenue_vnd'].mean()
        median_revenue = revenue_data['revenue_vnd'].median()
        q75_revenue = revenue_data['revenue_vnd'].quantile(0.75)
        
        fig_dist.add_vline(x=mean_revenue, line_dash="dash", line_color="red",
                          annotation_text=f"TB: {mean_revenue:,.0f}")
        fig_dist.add_vline(x=median_revenue, line_dash="dash", line_color="blue",
                          annotation_text=f"Trung vị: {median_revenue:,.0f}")
        fig_dist.add_vline(x=q75_revenue, line_dash="dash", line_color="green",
                          annotation_text=f"Q75: {q75_revenue:,.0f}")
        
        fig_dist.update_layout(height=400)
        st.plotly_chart(fig_dist, use_container_width=True)
    
    with col2:
        st.markdown("##### 🎯 Doanh thu theo loại xe")
        if 'vehicle_type' in revenue_data.columns:
            type_revenue = revenue_data.groupby('vehicle_type').agg({
                'revenue_vnd': ['sum', 'mean', 'count']
            }).round(0)
            type_revenue.columns = ['Tổng DT', 'TB DT/chuyến', 'Số chuyến']
            type_revenue = type_revenue.reset_index()
            
            # Pie chart
            fig_type_pie = px.pie(
                type_revenue,
                values='Tổng DT',
                names='vehicle_type',
                title="Phân bố doanh thu theo loại xe",
                color_discrete_map={'Cứu thương': '#ff6b6b', 'Hành chính': '#4ecdc4'}
            )
            fig_type_pie.update_layout(height=300)
            st.plotly_chart(fig_type_pie, use_container_width=True)
            
            # Stats table
            st.dataframe(type_revenue, use_container_width=True, hide_index=True)
        else:
            st.info("Không có dữ liệu loại xe")
    
    # Row 4: Performance analysis
    col3, col4 = st.columns(2)
    
    with col3:
        st.markdown("##### 💼 Top tài xế theo doanh thu")
        if 'driver_name' in revenue_data.columns:
            # Filter valid drivers
            valid_drivers = revenue_data[
                revenue_data['driver_name'].notna() & 
                (revenue_data['driver_name'].str.strip() != '') & 
                (revenue_data['driver_name'] != 'nan')
            ]
            
            if not valid_drivers.empty:
                driver_revenue = valid_drivers.groupby('driver_name').agg({
                    'revenue_vnd': ['sum', 'count', 'mean']
                }).round(0)
                driver_revenue.columns = ['Tổng DT', 'Số chuyến', 'TB DT/chuyến']
                driver_revenue = driver_revenue.reset_index().sort_values('Tổng DT', ascending=False)
                
                # Bar chart top 10
                fig_driver = px.bar(
                    driver_revenue.head(10),
                    x='driver_name',
                    y='Tổng DT',
                    title="Top 10 tài xế theo doanh thu",
                    labels={'Tổng DT': 'Tổng doanh thu (VNĐ)', 'driver_name': 'Tài xế'},
                    color='Tổng DT',
                    color_continuous_scale='Viridis'
                )
                fig_driver.update_layout(height=400)
                fig_driver.update_xaxes(tickangle=45)
                st.plotly_chart(fig_driver, use_container_width=True)
            else:
                st.info("Không có dữ liệu tài xế hợp lệ")
        else:
            st.info("Không có dữ liệu tài xế")
    
    with col4:
        st.markdown("##### 🫧 Bubble Chart: Số chuyến vs Doanh thu")
        if 'vehicle_id' in revenue_data.columns:
            bubble_data = revenue_data.groupby('vehicle_id').agg({
                'revenue_vnd': ['sum', 'mean'],
                'vehicle_id': 'count'
            }).reset_index()
            bubble_data.columns = ['vehicle_id', 'total_revenue', 'avg_revenue', 'trip_count']
            
            # Add vehicle type if available
            if 'vehicle_type' in revenue_data.columns:
                vehicle_types = revenue_data.groupby('vehicle_id')['vehicle_type'].first().reset_index()
                bubble_data = bubble_data.merge(vehicle_types, on='vehicle_id', how='left')
                color_col = 'vehicle_type'
            else:
                color_col = None
            
            fig_bubble = px.scatter(
                bubble_data,
                x='trip_count',
                y='total_revenue',
                size='avg_revenue',
                color=color_col,
                hover_data=['vehicle_id'],
                title="Số chuyến vs Tổng DT (size = TB DT/chuyến)",
                labels={'trip_count': 'Số chuyến', 'total_revenue': 'Tổng doanh thu (VNĐ)'},
                size_max=30
            )
            fig_bubble.update_layout(height=400)
            st.plotly_chart(fig_bubble, use_container_width=True)
        else:
            st.info("Không có dữ liệu xe")
    
    # =================== HEATMAP ANALYSIS ===================
    if 'start_time' in revenue_data.columns and 'parsed_date' in revenue_data.columns:
        st.markdown("##### 🔥 Heatmap: Doanh thu theo ngày và giờ")
        
        # Only proceed if we have valid parsed dates
        if revenue_data['parsed_date'].notna().any():
            # Parse time data
            revenue_data['start_time'] = pd.to_datetime(revenue_data['start_time'], errors='coerce')
            revenue_data['hour'] = revenue_data['start_time'].dt.hour
            revenue_data['day_of_week'] = revenue_data['parsed_date'].dt.day_name()
            
            # Create heatmap data - only use rows with valid hour and day_of_week
            valid_heatmap_data = revenue_data[
                revenue_data['hour'].notna() & 
                revenue_data['day_of_week'].notna()
            ]
            
            if not valid_heatmap_data.empty:
                heatmap_data = valid_heatmap_data.groupby(['day_of_week', 'hour'])['revenue_vnd'].sum().reset_index()
                
                if not heatmap_data.empty:
                    heatmap_pivot = heatmap_data.pivot(index='day_of_week', columns='hour', values='revenue_vnd').fillna(0)
                    
                    # Reorder days
                    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                    heatmap_pivot = heatmap_pivot.reindex([day for day in day_order if day in heatmap_pivot.index])
                    
                    fig_heatmap = px.imshow(
                        heatmap_pivot,
                        title="Doanh thu theo ngày trong tuần và giờ",
                        labels={'x': 'Giờ', 'y': 'Ngày trong tuần', 'color': 'Doanh thu (VNĐ)'},
                        color_continuous_scale='Viridis',
                        aspect='auto'
                    )
                    fig_heatmap.update_layout(height=400)
                    st.plotly_chart(fig_heatmap, use_container_width=True)
                else:
                    st.info("Không có dữ liệu hợp lệ cho heatmap")
            else:
                st.info("Không có dữ liệu thời gian hợp lệ cho heatmap")
        else:
            st.info("Không thể tạo heatmap do lỗi parse ngày tháng")
    
    # =================== SUMMARY TABLE ===================
    st.markdown("#### 📋 Bảng thống kê tổng hợp")
    
    revenue_stats = pd.DataFrame({
        'Chỉ số': [
            'Tổng doanh thu', 
            'Doanh thu TB/chuyến', 
            'Doanh thu cao nhất/chuyến',
            'Doanh thu thấp nhất/chuyến',
            'Trung vị doanh thu/chuyến',
            'Số chuyến có doanh thu',
            'Số xe tham gia',
            'Số tài xế (nếu có)'
        ],
        'Giá trị': [
            f"{total_revenue:,.0f} VNĐ",
            f"{avg_revenue_per_trip:,.0f} VNĐ",
            f"{revenue_data['revenue_vnd'].max():,.0f} VNĐ",
            f"{revenue_data['revenue_vnd'].min():,.0f} VNĐ",
            f"{revenue_data['revenue_vnd'].median():,.0f} VNĐ",
            f"{total_revenue_trips:,} chuyến",
            f"{unique_vehicles} xe",
            f"{revenue_data['driver_name'].nunique() if 'driver_name' in revenue_data.columns else 'N/A'}"
        ]
    })
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.dataframe(revenue_stats, use_container_width=True, hide_index=True)
    
    with col2:
        # Quick insights
        if not daily_revenue.empty and len(daily_revenue) > 1:
            recent_trend = daily_revenue.tail(7)['revenue_vnd'].mean()
            overall_avg = daily_revenue['revenue_vnd'].mean()
            trend_direction = "📈 Tăng" if recent_trend > overall_avg else "📉 Giảm"
            
            st.markdown("**🎯 Insights nhanh:**")
            st.info(f"""
            • Xu hướng 7 ngày gần nhất: {trend_direction}
            • DT TB 7 ngày: {recent_trend:,.0f} VNĐ
            • DT TB tổng thể: {overall_avg:,.0f} VNĐ
            • Chênh lệch: {(recent_trend-overall_avg)/overall_avg*100:+.1f}%
            """)
        else:
            st.markdown("**⚠️ Lưu ý:**")
            st.warning("Không thể tính insights do dữ liệu ngày tháng không hợp lệ hoặc không đủ")

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
        total_hours = vehicle_data['duration_hours'].sum() if 'duration_hours' in vehicle_data.columns else 0
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
    """Tab 3: Phân tích quá tải và tối ưu hóa"""
    st.markdown("### ⚡ Phân tích quá tải hệ thống xe")
    
    if df.empty:
        st.warning("⚠️ Không có dữ liệu để phân tích")
        return
    
    # Kiểm tra dữ liệu cần thiết
    if 'vehicle_type' not in df.columns or 'vehicle_id' not in df.columns:
        st.error("❌ Thiếu dữ liệu phân loại xe hoặc mã xe")
        return
    
    # =================== THIẾT LẬP NGƯỠNG ===================
    st.markdown("#### 🎯 Thiết lập ngưỡng cảnh báo")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        max_hours_per_day = st.number_input("Max giờ/ngày mỗi xe", value=10.0, min_value=1.0, max_value=24.0)
    with col2:
        max_trips_per_day = st.number_input("Max chuyến/ngày mỗi xe", value=8, min_value=1, max_value=20)
    with col3:
        utilization_threshold = st.slider("Ngưỡng quá tải hệ thống (%)", value=80, min_value=50, max_value=100)
    
    # Xử lý dữ liệu ngày
    if 'date' not in df.columns:
        if 'record_date' in df.columns:
            df['record_date'] = pd.to_datetime(df['record_date'], errors='coerce')
            df['date'] = df['record_date'].dt.date
        else:
            st.error("❌ Không có dữ liệu ngày để phân tích")
            return
    
    # Phân loại xe
    xe_hanh_chinh = df[df['vehicle_type'] == 'Hành chính']['vehicle_id'].unique()
    xe_cuu_thuong = df[df['vehicle_type'] == 'Cứu thương']['vehicle_id'].unique()
    
    total_xe_hanh_chinh = len(xe_hanh_chinh)
    total_xe_cuu_thuong = len(xe_cuu_thuong)
    total_xe = total_xe_hanh_chinh + total_xe_cuu_thuong
    
    st.info(f"🚗 **Tổng đội xe:** {total_xe} xe ({total_xe_hanh_chinh} hành chính + {total_xe_cuu_thuong} cứu thương)")
    
    # =================== XE VƯỢT NGƯỠNG GIỜ LÀM VIỆC - FIXED ===================
    
    st.markdown("#### 🚨 Xe vượt ngưỡng giờ làm việc")
    
    # Tính toán workload hàng ngày cho từng xe
    vehicle_daily = df.groupby(['vehicle_id', 'date']).agg({
        'duration_hours': 'sum',
        'distance_km': 'sum', 
        'vehicle_type': 'first'
    }).reset_index()
    vehicle_daily.columns = ['vehicle_id', 'date', 'daily_hours', 'daily_distance', 'vehicle_type']
    vehicle_daily['daily_trips'] = df.groupby(['vehicle_id', 'date']).size().values
    
    # Xe vượt ngưỡng
    vehicle_overload = vehicle_daily[
        (vehicle_daily['daily_hours'] > max_hours_per_day) |
        (vehicle_daily['daily_trips'] > max_trips_per_day)
    ]
    
    # BIỂU ĐỒ SCATTER THEO BIỂN SỐ XE - FIXED
    # Tạo color map cho từng xe
    unique_vehicles = vehicle_daily['vehicle_id'].unique()
    colors = px.colors.qualitative.Plotly + px.colors.qualitative.Set3 + px.colors.qualitative.Pastel
    vehicle_color_map = {vehicle: colors[i % len(colors)] for i, vehicle in enumerate(unique_vehicles)}
    
    fig_overload = px.scatter(
        vehicle_daily,
        x='daily_trips',
        y='daily_hours', 
        color='vehicle_id',  # Thay đổi từ 'vehicle_type' thành 'vehicle_id'
        color_discrete_map=vehicle_color_map,
        title=f"Tải công việc hàng ngày - {total_xe} xe (theo biển số)",
        labels={'daily_trips': 'Chuyến/ngày', 'daily_hours': 'Giờ làm việc/ngày'},
        hover_data=['vehicle_type', 'date']  # Thêm vehicle_type vào hover
    )
    
    # Ngưỡng cảnh báo
    fig_overload.add_hline(y=max_hours_per_day, line_dash="dash", line_color="red", 
                         annotation_text=f"Max {max_hours_per_day}h/ngày")
    fig_overload.add_vline(x=max_trips_per_day, line_dash="dash", line_color="red",
                         annotation_text=f"Max {max_trips_per_day} chuyến/ngày")
    fig_overload.update_layout(height=500)
    st.plotly_chart(fig_overload, use_container_width=True)
    
    # Thống kê xe quá tải
    if not vehicle_overload.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.error(f"🚨 **{len(vehicle_overload)}** lần xe vượt ngưỡng")
            overload_freq = vehicle_overload['vehicle_id'].value_counts().head(5)
            for vehicle, count in overload_freq.items():
                vehicle_type = df[df['vehicle_id'] == vehicle]['vehicle_type'].iloc[0]
                icon = "🏢" if vehicle_type == "Hành chính" else "🚑"
                st.warning(f"{icon} **{vehicle}**: {count} lần")
        
        with col2:
            st.markdown("**📅 Ngày quá tải gần nhất:**")
            recent = vehicle_overload.sort_values('date', ascending=False).head(5)
            for _, row in recent.iterrows():
                icon = "🏢" if row['vehicle_type'] == "Hành chính" else "🚑"
                st.info(f"{icon} {row['vehicle_id']} ({row['date']}): {row['daily_hours']:.1f}h")
    else:
        st.success("✅ Không có xe nào vượt ngưỡng!")
    
    # =================== PHÂN TÍCH THEO KHUNG GIỜ ===================
    
    st.markdown("#### ⏰ Phân tích theo khung giờ")
    
    if 'start_time' in df.columns and 'end_time' in df.columns:
        # Parse thời gian
        df_time = df.copy()
        df_time['start_time'] = pd.to_datetime(df_time['start_time'], errors='coerce')
        df_time['end_time'] = pd.to_datetime(df_time['end_time'], errors='coerce')
        df_time['start_hour'] = df_time['start_time'].dt.hour
        df_time['end_hour'] = df_time['end_time'].dt.hour
        
        # Color map cho loại xe ở phần này vẫn giữ nguyên
        color_map = {'Hành chính': 'blue', 'Cứu thương': 'red'}
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Giờ bắt đầu
            start_data = df_time[df_time['start_hour'].notna()]
            if not start_data.empty:
                start_counts = start_data.groupby(['start_hour', 'vehicle_type']).size().reset_index(name='count')
                
                fig_start = px.bar(
                    start_counts,
                    x='start_hour',
                    y='count',
                    color='vehicle_type',
                    color_discrete_map=color_map,
                    title="Giờ bắt đầu chuyến",
                    labels={'start_hour': 'Giờ', 'count': 'Số chuyến'},
                    barmode='group'
                )
                fig_start.update_layout(height=400)
                st.plotly_chart(fig_start, use_container_width=True)
                
                # Top giờ cao điểm
                peak_hours = start_data['start_hour'].value_counts().head(3)
                st.markdown("**🔥 Giờ cao điểm:**")
                for hour, count in peak_hours.items():
                    st.info(f"⏰ {int(hour):02d}:00 - {count} chuyến")
        
        with col2:
            # Giờ kết thúc
            end_data = df_time[df_time['end_hour'].notna()]
            if not end_data.empty:
                end_counts = end_data.groupby(['end_hour', 'vehicle_type']).size().reset_index(name='count')
                
                fig_end = px.bar(
                    end_counts,
                    x='end_hour',
                    y='count',
                    color='vehicle_type',
                    color_discrete_map=color_map,
                    title="Giờ kết thúc chuyến",
                    labels={'end_hour': 'Giờ', 'count': 'Số chuyến'},
                    barmode='group'
                )
                fig_end.update_layout(height=400)
                st.plotly_chart(fig_end, use_container_width=True)
        
        # Phân tích ca làm việc
        if not start_data.empty:
            def get_shift(hour):
                if pd.isna(hour): return 'Không xác định'
                if 6 <= hour < 14: return 'Ca sáng (6h-14h)'
                elif 14 <= hour < 22: return 'Ca chiều (14h-22h)'
                else: return 'Ca đêm (22h-6h)'
            
            start_data['shift'] = start_data['start_hour'].apply(get_shift)
            shift_stats = start_data.groupby(['shift', 'vehicle_type']).size().reset_index(name='count')
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Pie chart tổng hợp
                shift_total = start_data['shift'].value_counts()
                fig_pie = px.pie(
                    values=shift_total.values,
                    names=shift_total.index,
                    title="Phân bố theo ca làm việc"
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col2:
                # Bar chart theo loại xe
                fig_shift = px.bar(
                    shift_stats,
                    x='shift',
                    y='count',
                    color='vehicle_type',
                    color_discrete_map=color_map,
                    title="Ca làm việc theo loại xe"
                )
                fig_shift.update_xaxes(tickangle=45)
                st.plotly_chart(fig_shift, use_container_width=True)
    else:
        st.warning("⚠️ Không có dữ liệu start_time/end_time để phân tích khung giờ")
    
    # =================== PHÂN TÍCH TỶ LỆ SỬ DỤNG THEO LOẠI XE ===================
    
    st.markdown("#### 📈 Tỷ lệ sử dụng xe theo ngày")
    
    # Tính toán cho từng ngày
    daily_analysis = []
    unique_dates = sorted(df['date'].dropna().unique())
    
    for date in unique_dates:
        daily_data = df[df['date'] == date]
        
        xe_hc = daily_data[daily_data['vehicle_type'] == 'Hành chính']['vehicle_id'].nunique()
        xe_ct = daily_data[daily_data['vehicle_type'] == 'Cứu thương']['vehicle_id'].nunique()
        
        ty_le_hc = (xe_hc / total_xe_hanh_chinh * 100) if total_xe_hanh_chinh > 0 else 0
        ty_le_ct = (xe_ct / total_xe_cuu_thuong * 100) if total_xe_cuu_thuong > 0 else 0
        
        daily_analysis.append({
            'date': date,
            'xe_hc': xe_hc,
            'xe_ct': xe_ct,
            'ty_le_hc': ty_le_hc,
            'ty_le_ct': ty_le_ct,
            'qua_tai_hc': ty_le_hc >= utilization_threshold,
            'qua_tai_ct': ty_le_ct >= utilization_threshold,
            'chuyen_hc': len(daily_data[daily_data['vehicle_type'] == 'Hành chính']),
            'chuyen_ct': len(daily_data[daily_data['vehicle_type'] == 'Cứu thương'])
        })
    
    daily_df = pd.DataFrame(daily_analysis)
    
    if not daily_df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            # Xe hành chính
            st.markdown("##### 🏢 XE HÀNH CHÍNH")
            
            fig_hc = go.Figure()
            fig_hc.add_trace(go.Scatter(
                x=daily_df['date'],
                y=daily_df['ty_le_hc'],
                mode='lines+markers',
                name='Tỷ lệ sử dụng',
                line=dict(color='blue', width=3),
                fill='tonexty'
            ))
            
            fig_hc.add_hline(y=utilization_threshold, line_dash="dash", line_color="orange",
                           annotation_text=f"Ngưỡng {utilization_threshold}%")
            
            fig_hc.update_layout(
                title=f"Tỷ lệ sử dụng xe hành chính ({total_xe_hanh_chinh} xe)",
                yaxis_title="Tỷ lệ (%)",
                height=400,
                yaxis=dict(range=[0, 100])
            )
            st.plotly_chart(fig_hc, use_container_width=True)
            
            # Thống kê
            ngay_qua_tai_hc = daily_df[daily_df['qua_tai_hc'] == True]
            avg_hc = daily_df['ty_le_hc'].mean()
            
            if not ngay_qua_tai_hc.empty:
                st.error(f"🚨 {len(ngay_qua_tai_hc)} ngày quá tải")
            else:
                st.success("✅ Không quá tải")
            
            st.info(f"📊 TB sử dụng: {avg_hc:.1f}%")
        
        with col2:
            # Xe cứu thương
            st.markdown("##### 🚑 XE CỨU THƯƠNG")
            
            fig_ct = go.Figure()
            fig_ct.add_trace(go.Scatter(
                x=daily_df['date'],
                y=daily_df['ty_le_ct'],
                mode='lines+markers',
                name='Tỷ lệ sử dụng',
                line=dict(color='red', width=3),
                fill='tonexty'
            ))
            
            fig_ct.add_hline(y=utilization_threshold, line_dash="dash", line_color="orange",
                           annotation_text=f"Ngưỡng {utilization_threshold}%")
            
            fig_ct.update_layout(
                title=f"Tỷ lệ sử dụng xe cứu thương ({total_xe_cuu_thuong} xe)",
                yaxis_title="Tỷ lệ (%)",
                height=400,
                yaxis=dict(range=[0, 100])
            )
            st.plotly_chart(fig_ct, use_container_width=True)
            
            # Thống kê
            ngay_qua_tai_ct = daily_df[daily_df['qua_tai_ct'] == True]
            avg_ct = daily_df['ty_le_ct'].mean()
            
            if not ngay_qua_tai_ct.empty:
                st.error(f"🚨 {len(ngay_qua_tai_ct)} ngày quá tải")
            else:
                st.success("✅ Không quá tải")
            
            st.info(f"📊 TB sử dụng: {avg_ct:.1f}%")
        
        # =================== SO SÁNH VÀ KHUYẾN NGHỊ ===================
        
        st.markdown("#### 💡 Tổng quan và Khuyến nghị")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### 📊 So sánh")
            
            if avg_hc > avg_ct:
                diff = avg_hc - avg_ct
                st.warning(f"🏢 Xe hành chính sử dụng cao hơn {diff:.1f}%")
            elif avg_ct > avg_hc:
                diff = avg_ct - avg_hc
                st.warning(f"🚑 Xe cứu thương sử dụng cao hơn {diff:.1f}%")
            else:
                st.success("⚖️ Cân bằng giữa 2 loại xe")
            
            st.write(f"• Hành chính: {avg_hc:.1f}%")
            st.write(f"• Cứu thương: {avg_ct:.1f}%")
        
        with col2:
            st.markdown("##### 🎯 Khuyến nghị")
            
            max_avg = max(avg_hc, avg_ct)
            
            if max_avg > utilization_threshold:
                st.error("🚨 **Quá tải nghiêm trọng!**")
                st.write("• 🚗 Tăng cường xe dự phòng")
                st.write("• ⏰ Điều chỉnh ca làm việc")
                st.write("• 🔄 Cân nhắc thuê xe ngoài")
            elif max_avg > utilization_threshold - 10:
                st.warning("⚠️ **Gần ngưỡng quá tải!**")
                st.write("• 📊 Theo dõi sát sao")
                st.write("• 🔄 Chuẩn bị phương án dự phòng")
            else:
                st.success("✅ **Hoạt động ổn định**")
                st.write("• 📈 Có thể tối ưu hóa thêm")
                st.write("• 🔧 Bảo trì định kỳ")
    
    # =================== BẢNG CHI TIẾT ===================
    
    with st.expander("📋 Dữ liệu chi tiết theo ngày"):
        if not daily_df.empty:
            display_df = daily_df.copy()
            display_df['Ngày'] = display_df['date']
            display_df['HC: Xe'] = display_df['xe_hc']
            display_df['HC: Tỷ lệ (%)'] = display_df['ty_le_hc'].round(1)
            display_df['HC: Chuyến'] = display_df['chuyen_hc']
            display_df['CT: Xe'] = display_df['xe_ct']
            display_df['CT: Tỷ lệ (%)'] = display_df['ty_le_ct'].round(1)
            display_df['CT: Chuyến'] = display_df['chuyen_ct']
            
            cols_show = ['Ngày', 'HC: Xe', 'HC: Tỷ lệ (%)', 'HC: Chuyến', 
                        'CT: Xe', 'CT: Tỷ lệ (%)', 'CT: Chuyến']
            
            st.dataframe(display_df[cols_show].sort_values('Ngày', ascending=False), 
                        use_container_width=True, height=400)
        else:
            st.info("Không có dữ liệu để hiển thị")

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
    
    # NEW: Boxplot and Scatter plot
    col3, col4 = st.columns(2)
    
    with col3:
        st.markdown("#### 📦 Phân bố quãng đường theo xe (Boxplot)")
        # Use all vehicles, sorted by vehicle_id for better organization
        sorted_vehicles = sorted(distance_data['vehicle_id'].unique())
        boxplot_data = distance_data.copy()
        
        fig_boxplot = px.box(
            boxplot_data,
            x='vehicle_id',
            y='distance_km',
            title=f"Phân bố quãng đường - Tất cả {len(sorted_vehicles)} xe",
            labels={'distance_km': 'Quãng đường (km)', 'vehicle_id': 'Mã xe'},
            category_orders={'vehicle_id': sorted_vehicles}
        )
        fig_boxplot.update_xaxes(tickangle=90, tickfont=dict(size=10))
        fig_boxplot.update_layout(
            height=500,  # Tăng chiều cao để dễ đọc hơn
            margin=dict(b=120)  # Tăng margin bottom cho labels
        )
        st.plotly_chart(fig_boxplot, use_container_width=True)
    
    with col4:
        st.markdown("#### 🎯 Quan hệ Quãng đường - Thời gian")
        if 'duration_hours' in distance_data.columns:
            # Filter out extreme values for better visualization
            scatter_data = distance_data[
                (distance_data['duration_hours'] > 0) & 
                (distance_data['duration_hours'] < 12) &  # reasonable trip duration
                (distance_data['distance_km'] < 200)  # reasonable distance
            ]
            
            fig_scatter = px.scatter(
                scatter_data,
                x='duration_hours',
                y='distance_km',
                color='vehicle_type' if 'vehicle_type' in scatter_data.columns else None,
                title="Quãng đường vs Thời gian",
                labels={'duration_hours': 'Thời gian (giờ)', 'distance_km': 'Quãng đường (km)'},
                opacity=0.6
            )
            fig_scatter.update_layout(height=400)
            st.plotly_chart(fig_scatter, use_container_width=True)
        else:
            st.info("Không có dữ liệu thời gian")
    
    # Distance distribution and efficiency
    col5, col6 = st.columns(2)
    
    with col5:
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
    
    with col6:
        st.markdown("#### 🎯 Hiệu suất quãng đường theo xe")
        # Distance efficiency: km per hour
        if 'duration_hours' in distance_data.columns:
            # Create a copy to avoid modifying original data
            efficiency_data = distance_data.copy()
            efficiency_data['km_per_hour'] = efficiency_data['distance_km'] / efficiency_data['duration_hours']
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
    
    # NEW: Additional analysis options
    st.markdown("#### 🔍 Phân tích bổ sung")
    
    analysis_options = st.multiselect(
        "Chọn các phân tích bổ sung:",
        [
            "Violin Plot - Phân bố chi tiết theo xe",
            "Heatmap - Quãng đường theo ngày/giờ", 
            "Bubble Chart - 3D Analysis",
            "So sánh theo loại xe",
            "Xu hướng trung bình theo thời gian"
        ]
    )
    
    if "Violin Plot - Phân bố chi tiết theo xe" in analysis_options:
        st.markdown("##### 🎻 Violin Plot - Phân bố chi tiết")
        col_v1, col_v2 = st.columns([2, 1])
        
        with col_v1:
            # Horizontal violin plot for better readability
            fig_violin = px.violin(
                distance_data,
                y='vehicle_id',  # Swap x and y for horizontal
                x='distance_km',
                color='vehicle_type' if 'vehicle_type' in distance_data.columns else None,
                title=f"Phân bố chi tiết quãng đường - Tất cả {len(distance_data['vehicle_id'].unique())} xe",
                labels={'distance_km': 'Quãng đường (km)', 'vehicle_id': 'Mã xe'},
                category_orders={'vehicle_id': sorted(distance_data['vehicle_id'].unique(), reverse=True)},  # Reverse for top-to-bottom
                orientation='h'  # Horizontal orientation
            )
            fig_violin.update_layout(
                height=max(400, len(distance_data['vehicle_id'].unique()) * 25),  # Dynamic height based on number of vehicles
                margin=dict(l=120, r=20, t=50, b=50)
            )
            st.plotly_chart(fig_violin, use_container_width=True)
        
        with col_v2:
            st.markdown("**Giải thích Violin Plot:**")
            st.info("🎻 Violin Plot cho thấy:\n"
                   "• Độ rộng = mật độ phân bố\n"
                   "• Đường giữa = median\n"
                   "• Hình dạng = tần suất các giá trị")
    
    if "Heatmap - Quãng đường theo ngày/giờ" in analysis_options and 'start_time' in distance_data.columns:
        st.markdown("##### 🔥 Heatmap - Patterns theo thời gian")
        
        # Parse time data
        time_data = distance_data.copy()
        time_data['start_time'] = pd.to_datetime(time_data['start_time'], errors='coerce')
        time_data['hour'] = time_data['start_time'].dt.hour
        time_data['day_of_week'] = time_data['start_time'].dt.day_name()
        
        if not time_data['hour'].isna().all():
            # Create heatmap data
            heatmap_data = time_data.groupby(['day_of_week', 'hour'])['distance_km'].mean().reset_index()
            heatmap_pivot = heatmap_data.pivot(index='day_of_week', columns='hour', values='distance_km')
            
            fig_heatmap = px.imshow(
                heatmap_pivot,
                title="Quãng đường trung bình theo ngày/giờ",
                labels={'x': 'Giờ', 'y': 'Ngày trong tuần', 'color': 'Km TB'},
                color_continuous_scale='Viridis'
            )
            st.plotly_chart(fig_heatmap, use_container_width=True)
    
    if "Bubble Chart - 3D Analysis" in analysis_options:
        st.markdown("##### 🫧 Bubble Chart - Phân tích 3 chiều")
        
        bubble_data = distance_data.groupby('vehicle_id').agg({
            'distance_km': ['sum', 'mean'],
            'duration_hours': 'sum' if 'duration_hours' in distance_data.columns else 'count'
        }).reset_index()
        bubble_data.columns = ['vehicle_id', 'total_km', 'avg_km', 'total_hours']
        bubble_data['trip_count'] = distance_data['vehicle_id'].value_counts().values
        
        fig_bubble = px.scatter(
            bubble_data.head(20),
            x='total_km',
            y='avg_km',
            size='trip_count',
            hover_data=['vehicle_id'],
            title="Tổng KM vs TB KM vs Số chuyến (bubble size)",
            labels={'total_km': 'Tổng km', 'avg_km': 'TB km/chuyến'}
        )
        st.plotly_chart(fig_bubble, use_container_width=True)
    
    if "So sánh theo loại xe" in analysis_options and 'vehicle_type' in distance_data.columns:
        st.markdown("##### 🚗 So sánh theo loại xe")
        
        col_comp1, col_comp2 = st.columns(2)
        
        with col_comp1:
            type_stats = distance_data.groupby('vehicle_type')['distance_km'].agg(['sum', 'mean', 'count']).reset_index()
            type_stats.columns = ['Loại xe', 'Tổng km', 'TB km', 'Số chuyến']
            
            fig_type = px.bar(
                type_stats,
                x='Loại xe',
                y='Tổng km',
                title="Tổng quãng đường theo loại xe",
                color='Loại xe'
            )
            st.plotly_chart(fig_type, use_container_width=True)
        
        with col_comp2:
            st.dataframe(type_stats, use_container_width=True, hide_index=True)
    
    if "Xu hướng trung bình theo thời gian" in analysis_options and 'date' in distance_data.columns:
        st.markdown("##### 📈 Xu hướng quãng đường trung bình")
        
        daily_avg = distance_data.groupby('date')['distance_km'].mean().reset_index()
        daily_avg = daily_avg.sort_values('date')
        
        # Add moving average
        daily_avg['MA_7'] = daily_avg['distance_km'].rolling(window=7, min_periods=1).mean()
        
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(
            x=daily_avg['date'],
            y=daily_avg['distance_km'],
            mode='lines+markers',
            name='Quãng đường TB',
            line=dict(color='lightblue', width=1)
        ))
        fig_trend.add_trace(go.Scatter(
            x=daily_avg['date'],
            y=daily_avg['MA_7'],
            mode='lines',
            name='Đường xu hướng (7 ngày)',
            line=dict(color='red', width=2)
        ))
        fig_trend.update_layout(
            title="Xu hướng quãng đường trung bình theo thời gian",
            xaxis_title="Ngày",
            yaxis_title="Quãng đường TB (km)"
        )
        st.plotly_chart(fig_trend, use_container_width=True)
    
    # Area analysis
    if 'area_type' in distance_data.columns:
        col7, col8 = st.columns(2)
        
        with col7:
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
        
        with col8:
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
    """Tab 5: Phân tích nhiên liệu chi tiết - Enhanced Version"""
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
    
    # BƯỚC 1: Clean dữ liệu cơ bản
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
    
    # BƯỚC 2: Tính toán cho từng xe
    vehicle_analysis = []
    all_vehicles = sorted(df_clean['vehicle_id'].unique())
    
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
    
    # BƯỚC 3: Hiển thị overview
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
    
    # BƯỚC 4: Biểu đồ phân tích
    st.markdown("#### 📊 Biểu đồ phân tích tiêu thụ")
    
    # Chỉ 2 biểu đồ chính
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("##### 📊 So sánh tiêu thụ vs định mức")
        chart_data = vehicle_fuel_df[
            (vehicle_fuel_df['avg_consumption'] > 0) & 
            (vehicle_fuel_df['standard'] > 0)
        ].copy()
        
        if not chart_data.empty:
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
            fig_comparison.update_xaxes(tickangle=45)
            
            st.plotly_chart(fig_comparison, use_container_width=True)
        else:
            st.info("Không có xe nào có đủ dữ liệu để so sánh")
    
    with col2:
        st.markdown("##### 🎯 Ma trận: Định mức vs Thực tế")
        if not chart_data.empty:
            fig_scatter = px.scatter(
                chart_data,
                x='standard',
                y='avg_consumption',
                hover_data=['vehicle_id', 'total_trips'],
                title="Định mức vs Thực tế",
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
            st.info("Không có dữ liệu để so sánh")
    
    # BƯỚC 5: Xe cần chú ý
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
    
    # BƯỚC 6: Bảng chi tiết xe
    st.markdown("#### 📋 Bảng chi tiết tất cả xe")
    
    # Sắp xếp: xe có dữ liệu trước, theo mức tiêu thụ
    display_df = vehicle_fuel_df.copy()
    display_df['sort_key'] = display_df.apply(lambda x: (
        0 if x['avg_consumption'] > 0 else 1,
        -x['avg_consumption']
    ), axis=1)
    display_df = display_df.sort_values(['sort_key', 'vehicle_id'])
    
    # Tạo bảng hiển thị
    display_table = pd.DataFrame({
        'Mã xe': display_df['vehicle_id'],
        'Tổng chuyến': display_df['total_trips'],
        'Tổng fuel (L)': display_df['total_fuel'].round(1),
        'Tổng distance (km)': display_df['total_distance'].round(1),
        'Tiêu thụ (L/100km)': display_df['avg_consumption'].round(2),
        'Định mức (L/100km)': display_df['standard'],
        'Chênh lệch': display_df['deviation'].round(2),
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
        height=400
    )
    
    # BƯỚC 7: Chi phí nhiên liệu
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

    # FIXED: Filter out empty/null driver names
    valid_df = df[
        df['driver_name'].notna() & 
        (df['driver_name'].str.strip() != '') & 
        (df['driver_name'] != 'nan') &
        (df['driver_name'] != 'NaN')
    ].copy()
    
    if valid_df.empty:
        st.warning("⚠️ Không có dữ liệu tài xế hợp lệ")
        return
    
    # Calculate metrics per driver
    drivers = valid_df['driver_name'].unique()
    results = []
    
    for driver in drivers:
        driver_data = valid_df[valid_df['driver_name'] == driver]
        
        # Basic metrics
        total_trips = len(driver_data)
        total_revenue = float(driver_data['revenue_vnd'].sum())
        
        # FIXED: Duration calculation - filter out invalid values
        valid_duration_data = driver_data[
            driver_data['duration_hours'].notna() & 
            (driver_data['duration_hours'] >= 0) & 
            (driver_data['duration_hours'] <= 24)
        ]
        total_hours = float(valid_duration_data['duration_hours'].sum())
        
        # Days calculation
        if 'date' in driver_data.columns:
            active_days = driver_data['date'].nunique()
        else:
            active_days = 30  # Default
        
        # FIXED: Only include drivers with meaningful data
        # Skip if no trips or no meaningful activity
        if total_trips == 0:
            continue
            
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
    
    # FIXED: Check if we have any valid results
    if not results:
        st.warning("⚠️ Không có dữ liệu tài xế hợp lệ để hiển thị")
        return
    
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
