import pandas as pd
import numpy as np
import requests
import subprocess
import os
from datetime import datetime
import json
import base64

    
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Serif:wght@400;700&display=swap');
    .stDataFrame {
        font-size: 12px;
    }
    .stDataFrame table {
        width: 100% !important;
    }
    .stDataFrame td, .stDataFrame th {
        white-space: nowrap !important;
        overflow: visible !important;
        text-overflow: clip !important;
        max-width: none !important;
        min-width: 120px !important;
    }
    .pivot-table {
        background-color: #f8f9fa;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .metric-card {
        background-color: #e9ecef;
        padding: 15px;
        border-radius: 8px;
        margin: 5px 0;
        text-align: center;
    }
    .sparkline {
        height: 30px;
        margin: 0;
        padding: 0;
    }
    .category-header {
        background-color: #eaf6ff;          /* unify with table cells */
        padding: 12px 15px;
        border-radius: 6px;
        margin: 8px 0 12px 0;
        border-left: 6px solid #1f77b4;
        font-weight: bold;
        font-size: 1.25rem;
        font-family: "IBM Plex Serif", "Times New Roman", serif;
    }
    .sub-category {
        padding-left: 20px;
        margin: 2px 0;
    }
    .positive-change {
        color: #28a745 !important;
        font-weight: bold !important;
        background-color: rgba(40, 167, 69, 0.1) !important;
        padding: 2px 4px !important;
        border-radius: 3px !important;
    }
    .negative-change {
        color: #dc3545 !important;
        font-weight: bold !important;
        background-color: rgba(220, 53, 69, 0.1) !important;
        padding: 2px 4px !important;
        border-radius: 3px !important;
    }
    .no-change {
        color: #6c757d !important;
        font-weight: bold !important;
        background-color: rgba(108, 117, 125, 0.1) !important;
        padding: 2px 4px !important;
        border-radius: 3px !important;
    }
    .full-width-table {
        overflow-x: auto;
        width: 100%;
        position: relative;
    }
    .full-width-table table {
        min-width: 100%;
        table-layout: auto;
    }
    .full-width-table td {
        white-space: nowrap;
        padding: 8px 12px;
        min-width: 150px;
    }
    /* Pivot table font */
    .full-width-table table,
    .full-width-table td,
    .full-width-table th {
        font-family: "IBM Plex Serif", "Times New Roman", serif;
    }
    .full-width-table th:first-child,
    .full-width-table td:first-child {
        position: sticky;
        left: 0;
        background-color: #f8f9fa;
        z-index: 10;
        border-right: 2px solid #dee2e6;
        min-width: 250px !important;
        max-width: 500px !important;
        font-family: "IBM Plex Serif", "Times New Roman", serif;
    }
    .full-width-table th:last-child,
    .full-width-table td:last-child {
        position: sticky;
        right: 0;
        background-color: #e9ecef;
        z-index: 10;
        border-left: 2px solid #dee2e6;
        font-weight: bold;
        min-width: 120px !important;
    }
    .number-cell {
        text-align: right;
        font-family: 'Courier New', monospace;
        font-weight: bold;
    }
    
    /* Mobile optimizations */
    @media (max-width: 768px) {
        .main .block-container {
            padding: 0.5rem;
        }
        
        .stButton > button {
            width: 100%;
            margin: 2px 0;
        }
        
        .stDataFrame {
            font-size: 10px;
        }
    }
    
    /* Upload section styles */
    .upload-section {
        background: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
    }
    
    .status-indicator {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 8px;
    }
    
    .status-online { background-color: #28a745; }
    .status-loading { background-color: #ffc107; }
    .status-offline { background-color: #dc3545; }
</style>
""", unsafe_allow_html=True)

# ================== DATA MANAGER CLASS ==================
class DataManager:
    """
    Quản lý dữ liệu với GitHub storage
    - Load/Save từ GitHub
    - Auto backup
    - Optimized cho storage
    """
    
    def __init__(self):
        self.github_token = st.secrets.get("github_token", None)
        self.github_owner = st.secrets.get("github_owner", None)
        self.github_repo = st.secrets.get("github_repo", None)
        
        # File naming strategy
        self.current_data_file = "current_dashboard_data.json"
        self.metadata_file = "upload_metadata.json"
        self.backup_prefix = "backup_"
        
        # Settings
        self.keep_backups = 2
        self.max_file_size_mb = 25
    
    def check_github_connection(self):
        """Kiểm tra kết nối GitHub"""
        if not all([self.github_token, self.github_owner, self.github_repo]):
            return False, "❌ Chưa cấu hình GitHub credentials"
        
        try:
            url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}"
            headers = {"Authorization": f"token {self.github_token}"}
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return True, "✅ GitHub kết nối thành công"
            else:
                return False, f"❌ GitHub error: {response.status_code}"
                
        except Exception as e:
            return False, f"❌ Lỗi kết nối: {str(e)}"
    
    def get_current_file_info(self):
        """Lấy thông tin file hiện tại"""
        try:
            metadata_url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/contents/{self.metadata_file}"
            headers = {"Authorization": f"token {self.github_token}"}
            
            response = requests.get(metadata_url, headers=headers)
            
            if response.status_code == 200:
                file_data = response.json()
                content = base64.b64decode(file_data['content']).decode()
                metadata = json.loads(content)
                return metadata
            
        except Exception as e:
            st.warning(f"Không thể đọc metadata: {str(e)}")
        
        return None
    
    def create_backup_of_current_file(self):
        """Backup file hiện tại trước khi xóa"""
        try:
            current_url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/contents/{self.current_data_file}"
            headers = {"Authorization": f"token {self.github_token}"}
            
            response = requests.get(current_url, headers=headers)
            
            if response.status_code == 200:
                file_data = response.json()
                
                current_metadata = self.get_current_file_info()
                if current_metadata:
                    upload_time = current_metadata.get('upload_time', datetime.now().isoformat())
                    backup_timestamp = upload_time[:19].replace(':', '-').replace(' ', '_')
                else:
                    backup_timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
                
                backup_filename = f"{self.backup_prefix}{backup_timestamp}.json"
                
                backup_url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/contents/{backup_filename}"
                
                backup_payload = {
                    "message": f"📦 Backup before new upload - {backup_timestamp}",
                    "content": file_data['content'],
                    "branch": "main"
                }
                
                backup_response = requests.put(backup_url, headers=headers, json=backup_payload)
                
                if backup_response.status_code == 201:
                    st.info(f"📦 Đã backup file cũ: {backup_filename}")
                    return backup_filename
                    
        except Exception as e:
            st.warning(f"Không thể backup file cũ: {str(e)}")
        
        return None
    
    def cleanup_old_backups(self):
        """Xóa các backup cũ, chỉ giữ lại số lượng nhất định"""
        try:
            contents_url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/contents"
            headers = {"Authorization": f"token {self.github_token}"}
            
            response = requests.get(contents_url, headers=headers)
            
            if response.status_code == 200:
                files = response.json()
                
                backup_files = [f for f in files if f['name'].startswith(self.backup_prefix)]
                backup_files.sort(key=lambda x: x['name'], reverse=True)
                files_to_delete = backup_files[self.keep_backups:]
                
                deleted_count = 0
                for file_to_delete in files_to_delete:
                    try:
                        delete_url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/contents/{file_to_delete['name']}"
                        
                        delete_payload = {
                            "message": f"🗑️ Auto cleanup old backup: {file_to_delete['name']}",
                            "sha": file_to_delete['sha'],
                            "branch": "main"
                        }
                        
                        delete_response = requests.delete(delete_url, headers=headers, json=delete_payload)
                        
                        if delete_response.status_code == 200:
                            deleted_count += 1
                            
                    except Exception as e:
                        continue
                
                if deleted_count > 0:
                    st.info(f"🗑️ Đã xóa {deleted_count} backup cũ")
                    
        except Exception as e:
            st.warning(f"Không thể cleanup backups: {str(e)}")
    
    def upload_new_file(self, data, filename):
        """Upload file mới với auto-cleanup"""
        
        try:
            connected, message = self.check_github_connection()
            if not connected:
                st.error(message)
                return False
            
            st.info("🔄 Bắt đầu upload file mới...")
            
            with st.spinner("📦 Đang backup file cũ..."):
                backup_filename = self.create_backup_of_current_file()
            
            with st.spinner("📊 Đang chuẩn bị dữ liệu..."):
                new_data_package = {
                    'data': data.to_dict('records'),
                    'columns': list(data.columns),
                    'metadata': {
                        'filename': filename,
                        'upload_time': datetime.now().isoformat(),
                        'week_number': datetime.now().isocalendar()[1],
                        'year': datetime.now().year,
                        'row_count': len(data),
                        'file_size_mb': round(len(str(data)) / (1024*1024), 2),
                        'uploader': 'admin',
                        'replaced_backup': backup_filename
                    }
                }
                
                json_content = json.dumps(new_data_package, ensure_ascii=False, indent=2)
                size_mb = len(json_content.encode()) / (1024*1024)
                
                if size_mb > self.max_file_size_mb:
                    st.error(f"❌ File quá lớn ({size_mb:.1f}MB). Giới hạn {self.max_file_size_mb}MB")
                    return False
            
            with st.spinner("☁️ Đang upload file mới..."):
                content_encoded = base64.b64encode(json_content.encode()).decode()
                
                current_url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/contents/{self.current_data_file}"
                headers = {"Authorization": f"token {self.github_token}"}
                
                current_response = requests.get(current_url, headers=headers)
                current_sha = None
                if current_response.status_code == 200:
                    current_sha = current_response.json()['sha']
                
                upload_payload = {
                    "message": f"📊 Data update - Tuần {new_data_package['metadata']['week_number']}/{new_data_package['metadata']['year']}",
                    "content": content_encoded,
                    "branch": "main"
                }
                
                if current_sha:
                    upload_payload["sha"] = current_sha
                
                upload_response = requests.put(current_url, headers=headers, json=upload_payload)
                
                if upload_response.status_code not in [200, 201]:
                    st.error(f"❌ Lỗi upload: {upload_response.status_code}")
                    return False
            
            with st.spinner("📝 Đang cập nhật metadata..."):
                self.update_metadata(new_data_package['metadata'])
            
            with st.spinner("🗑️ Đang dọn dẹp backup cũ..."):
                self.cleanup_old_backups()
            
            st.success(f"""
            🎉 **UPLOAD THÀNH CÔNG!**
            
            ✅ **File mới:** {filename}
            ✅ **Dữ liệu:** {len(data):,} dòng ({size_mb:.1f}MB)
            ✅ **Tuần:** {new_data_package['metadata']['week_number']}/{new_data_package['metadata']['year']}
            ✅ **Backup:** {backup_filename if backup_filename else 'Không có file cũ'}
            
            📱 **Dữ liệu đã được lưu trên cloud!**
            """)
            
            return True
            
        except Exception as e:
            st.error(f"❌ Lỗi upload: {str(e)}")
            return False
    
    def update_metadata(self, metadata):
        """Cập nhật file metadata"""
        try:
            metadata_url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/contents/{self.metadata_file}"
            headers = {"Authorization": f"token {self.github_token}"}
            
            current_response = requests.get(metadata_url, headers=headers)
            current_sha = None
            if current_response.status_code == 200:
                current_sha = current_response.json()['sha']
            
            metadata_content = json.dumps(metadata, ensure_ascii=False, indent=2)
            content_encoded = base64.b64encode(metadata_content.encode()).decode()
            
            payload = {
                "message": f"📝 Update metadata - Tuần {metadata['week_number']}/{metadata['year']}",
                "content": content_encoded,
                "branch": "main"
            }
            
            if current_sha:
                payload["sha"] = current_sha
            
            requests.put(metadata_url, headers=headers, json=payload)
            
        except Exception as e:
            st.warning(f"Không thể update metadata: {str(e)}")
    
    def load_current_data(self):
        """Load dữ liệu hiện tại"""
        try:
            current_url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/contents/{self.current_data_file}"
            headers = {"Authorization": f"token {self.github_token}"}
            
            response = requests.get(current_url, headers=headers)
            
            if response.status_code == 200:
                file_data = response.json()
                content = base64.b64decode(file_data['content']).decode()
                data_package = json.loads(content)
                
                df = pd.DataFrame(data_package['data'], columns=data_package['columns'])
                
                return df, data_package['metadata']
            
        except Exception as e:
            st.warning(f"Không thể load dữ liệu: {str(e)}")
        
        return None, None
    
    def get_storage_info(self):
        """Lấy thông tin storage usage"""
        try:
            contents_url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/contents"
            headers = {"Authorization": f"token {self.github_token}"}
            
            response = requests.get(contents_url, headers=headers)
            
            if response.status_code == 200:
                files = response.json()
                
                total_size = sum(f.get('size', 0) for f in files)
                backup_files = [f for f in files if f['name'].startswith(self.backup_prefix)]
                
                return {
                    'total_files': len(files),
                    'backup_files': len(backup_files),
                    'total_size_mb': round(total_size / (1024*1024), 2),
                    'files': files
                }
                
        except Exception as e:
            pass
        
        return None

# ================== PIVOT TABLE DASHBOARD CLASS (FULL ORIGINAL) ==================
class PivotTableDashboard:
    def __init__(self):
        self.data = None
        
        # CẤU HÌNH THỨ TỰ ƯU TIÊN CỐ ĐỊNH THEO YÊU CẦU MỚI
        self.category_priority = {
            "Văn bản đến": 1,
            "Văn bản phát hành": 2,
            "Chăm sóc khách vip": 3,
            "Lễ tân": 4,
            "Tiếp khách trong nước": 5,
            "Sự kiện": 6,
            "Đón tiếp khách VIP": 7,
            "Tổ chức cuộc họp trực tuyến": 8,
            "Trang điều hành tác nghiệp": 9,
            "Tổ xe": 10,
            "Tổng đài": 11,
            "Hệ thống thư ký Bệnh viện": 12,
            "Bãi giữ xe": 13
        }
        
        self.content_priority = {
            # Văn bản đến
            "Tổng số văn bản đến, trong đó:": 1,
            "Số văn bản không yêu cầu phản hồi": 2,
            "Số văn bản yêu cầu phản hồi": 3,
            "Xử lý đúng hạn": 4,
            "Xử lý trễ hạn": 5,
            
            # Văn bản phát hành
            "Văn bản đi": 6,
            "Hợp đồng": 7,
            "Quyết định": 8,
            "Quy chế": 9,
            "Quy định": 10,
            "Quy trình": 11,
            
            # Chăm sóc khách vip
            "Tiếp đón, hướng dẫn và phục vụ khách VIP": 12,
            
            # Lễ tân
            "Hỗ trợ lễ tân cho hội nghị/hội thảo": 13,
            
            # Tiếp khách trong nước
            "Tổng số đoàn khách trong nước, trong đó:": 14,
            "Tham quan, học tập": 15,
            "Làm việc": 16,
            
            # Sự kiện
            "Tổng số sự kiện hành chính của Bệnh viện, trong đó:": 17,
            "Phòng Hành chính chủ trì": 18,
            "Phòng Hành chính phối hợp": 19,
            
            # Đón tiếp khách VIP
            "Số lượt khách VIP được lễ tân tiếp đón, hỗ trợ khám chữa bệnh": 20,
            
            # Tổ chức cuộc họp trực tuyến
            "Tổng số cuộc họp trực tuyến do Phòng Hành chính chuẩn bị": 21,
            
            # Trang điều hành tác nghiệp
            "Số lượng tin đăng ĐHTN": 22,
            
            # Tổ xe
            "Số chuyến xe": 23,
            "Tổng số nhiên liệu tiêu thụ": 24,
            "Tổng km chạy": 25,
            "Xe hành chính": 26,
            "Xe cứu thương": 27,
            "Chi phí bảo dưỡng": 28,
            "Doanh thu": 29,
            "Tổ xe": 30,
            "Số phiếu khảo sát hài lòng": 31,
            "Tỷ lệ hài lòng của khách hàng": 32,
            
            # Tổng đài
            "Tổng số cuộc gọi đến Bệnh viện": 33,
            "Tổng số cuộc gọi nhỡ do từ chối": 34,
            "Tổng số cuộc gọi nhỡ do không bắt máy": 35,
            "Số cuộc gọi đến (Nhánh 0-Tổng đài viên)": 36,
            "Nhỡ do từ chối (Nhánh 0-Tổng đài viên)": 37,
            "Nhỡ do không bắt máy (Nhánh 0-Tổng đài viên)": 38,
            "Số cuộc gọi đến (Nhánh 1-Cấp cứu)": 39,
            "Nhỡ do từ chối (Nhánh 1-Cấp cứu)": 40,
            "Nhỡ do không bắt máy (Nhánh 1-Cấp cứu)": 41,
            "Số cuộc gọi đến (Nhánh 2-Tư vấn Thuốc)": 42,
            "Nhỡ do từ chối (Nhánh 2- Tư vấn Thuốc)": 43,
            "Nhỡ do không bắt máy (Nhánh 2-Tư vấn Thuốc)": 44,
            "Số cuộc gọi đến (Nhánh 3-PKQT)": 45,
            "Nhỡ do từ chối (Nhánh 3-PKQT)": 46,
            "Nhỡ do không bắt máy  (Nhánh 3-PKQT)": 47,
            "Số cuộc gọi đến (Nhánh 4-Vấn đề khác)": 48,
            "Nhỡ do từ chối (Nhánh 4-Vấn đề khác)": 49,
            "Nhỡ do không bắt máy (Nhánh 4-Vấn đề khác)": 50,
            "Hottline": 51,
            
            # Hệ thống thư ký Bệnh viện
            "Số thư ký được sơ tuyển": 52,
            "Số thư ký được tuyển dụng": 53,
            "Số thư ký nhận việc": 54,
            "Số thư ký nghỉ việc": 55,
            "Số thư ký được điều động": 56,
            "Tổng số thư ký": 57,
            "- Thư ký hành chính": 58,
            "- Thư ký chuyên môn": 59,
            "Số buổi sinh hoạt cho thư ký": 60,
            "Số thư ký tham gia sinh hoạt": 61,
            "Số buổi tập huấn, đào tạo cho thư ký": 62,
            "Số thư ký tham gia tập huấn, đào tạo": 63,
            "Số buổi tham quan, học tập": 64,
            "Số thư ký tham gia tham quan, học tập": 65,
            # ======= THÊM CÁC BIẾN THỂ CÓ THỂ =======
            # Biến thể có khoảng trắng thừa
            " Tổng số thư ký": 57,
            "Tổng số thư ký ": 57,
            " Tổng số thư ký ": 57,
            
            # Biến thể có ký tự đặc biệt
            "Tổng số thư ký:": 57,
            "- Tổng số thư ký": 57,
            "• Tổng số thư ký": 57,
            
            # Biến thể viết hoa/thường
            "TỔNG SỐ THƯ KÝ": 57,
            "tổng số thư ký": 57,
            
            # Biến thể từ khóa tương tự
            "Tống số thư ký": 57,  # Typo có thể
            "Tổng số thư kí": 57,  # Ký/kí
            "Tổng thư ký": 57,     # Thiếu "số"
            # =========================================
            # Bãi giữ xe
            "Tổng số lượt vé ngày": 66,
            "Tổng số lượt vé tháng": 67,
            "Công suất trung bình/ngày": 68,
            "Doanh thu": 69,
            "Số phản ánh khiếu nại": 70
        }
        self.content_aggregation = {
        # TRUNG BÌNH - Cho các tỷ lệ %
        "Tỷ lệ hài lòng của khách hàng": "mean",
        "Tỷ lệ hài lòng khách hàng": "mean",  # Biến thể
        "Ty le hai long cua khach hang": "mean",  # Biến thể không dấu
        
        # DỮ LIỆU MỚI NHẤT - Cho các chỉ số tổng số (snapshot)
        "Tổng số thư ký": "last",
        "- Thư ký hành chính": "last", 
        "- Thư ký chuyên môn": "last",
        "Thư ký hành chính": "last",
        "Thư ký chuyên môn": "last",
        " Thư ký hành chính": "last",  # Biến thể có space
        " Thư ký chuyên môn": "last",
        
        # Có thể thêm các nội dung khác cần xử lý đặc biệt
        "Công suất trung bình/ngày": "mean",  # Công suất là trung bình
        "Công suất trung bình": "mean",
        
        # Các chỉ số tài chính có thể cần lấy mới nhất
        "Doanh thu": "sum",  # Doanh thu thì cộng dồn
        "Chi phí bảo dưỡng": "sum",  # Chi phí thì cộng dồn
        
        # DEFAULT: Tất cả các nội dung khác sẽ dùng 'sum'
    }
    
    def get_aggregation_method(self, content):
        """Lấy phương pháp aggregation phù hợp cho nội dung"""
        if pd.isna(content):
            return "sum"
        
        # Thử tên chính xác
        if content in self.content_aggregation:
            return self.content_aggregation[content]
        
        # Thử tên đã chuẩn hóa đơn giản
        normalized = str(content).strip().strip('- •:')
        if normalized in self.content_aggregation:
            return self.content_aggregation[normalized]
        
        # Thử tìm bằng keyword
        content_lower = str(content).lower().strip()
        
        # Tỷ lệ % -> mean
        if any(keyword in content_lower for keyword in ['tỷ lệ', 'ty le', '%', 'phần trăm']):
            return "mean"
        
        # Tổng số thư ký -> last
        if any(keyword in content_lower for keyword in ['tổng số', 'tong so']) and 'thư ký' in content_lower:
            return "last"
        
        # Thư ký con -> last
        if any(keyword in content_lower for keyword in ['thư ký hành chính', 'thư ký chuyên môn', 'thu ky hanh chinh', 'thu ky chuyen mon']):
            return "last"
        
        # Trung bình -> mean
        if any(keyword in content_lower for keyword in ['trung bình', 'trung binh', 'tb']):
            return "mean"
        
        # Mặc định: sum
        return "sum"

    def apply_smart_aggregation(self, data, index_cols, column_cols, value_col):
        """Áp dụng aggregation thông minh theo từng nội dung"""
        try:
            # Group dữ liệu theo index và columns
            if column_cols:
                group_cols = index_cols + column_cols
            else:
                group_cols = index_cols
            
            # Tạo dictionary để store aggregated data
            result_data = []
            
            # Group theo các cột cần thiết
            for group_keys, group_data in data.groupby(group_cols):
                if not isinstance(group_keys, tuple):
                    group_keys = (group_keys,)
                
                # Tạo dict cho group này
                result_row = {}
                
                # Assign index values
                for i, col in enumerate(group_cols):
                    result_row[col] = group_keys[i]
                
                # Lấy nội dung để xác định aggregation method
                if 'Nội dung' in group_data.columns:
                    content = group_data['Nội dung'].iloc[0]
                    agg_method = self.get_aggregation_method(content)
                    
                    # Áp dụng aggregation method
                    if agg_method == "mean":
                        result_row[value_col] = group_data[value_col].mean()
                    elif agg_method == "last":
                        # Lấy dữ liệu mới nhất (tuần cao nhất)
                        if 'Tuần' in group_data.columns:
                            latest_week_data = group_data[group_data['Tuần'] == group_data['Tuần'].max()]
                            result_row[value_col] = latest_week_data[value_col].iloc[-1]
                        else:
                            result_row[value_col] = group_data[value_col].iloc[-1]
                    else:  # sum (default)
                        result_row[value_col] = group_data[value_col].sum()
                else:
                    # Fallback to sum
                    result_row[value_col] = group_data[value_col].sum()
                
                result_data.append(result_row)
            
            # Convert back to DataFrame
            result_df = pd.DataFrame(result_data)
            
            # Create pivot table
            if column_cols:
                pivot = pd.pivot_table(
                    result_df,
                    index=index_cols,
                    columns=column_cols,
                    values=value_col,
                    aggfunc='first',  # Data đã được aggregate rồi
                    fill_value=0
                )
            else:
                pivot = result_df.set_index(index_cols)[value_col]
            
            return pivot
            
        except Exception as e:
            st.error(f"Lỗi trong smart aggregation: {str(e)}")
            # Fallback to normal pivot
            return pd.pivot_table(
                data,
                index=index_cols,
                columns=column_cols if column_cols else None,
                values=value_col,
                aggfunc='sum',
                fill_value=0
            )    
        
    def load_data_from_dataframe(self, df):
        """THÊM METHOD MỚI: Load dữ liệu từ DataFrame"""
        try:
            self.data = df.copy()
            
            # Làm sạch tên cột
            self.data.columns = self.data.columns.str.strip()
            
            # Chuyển đổi kiểu dữ liệu
            self.data['Tuần'] = pd.to_numeric(self.data['Tuần'], errors='coerce')
            self.data['Tháng'] = pd.to_numeric(self.data['Tháng'], errors='coerce')
            self.data['Số liệu'] = pd.to_numeric(self.data['Số liệu'], errors='coerce')
            
            # Thêm cột năm (có thể điều chỉnh theo dữ liệu thực tế)
            if 'Năm' not in self.data.columns:
                self.data['Năm'] = datetime.now().year
            
            # Tạo cột Quý từ Tháng
            self.data['Quý'] = ((self.data['Tháng'] - 1) // 3) + 1
            
            # Tạo cột kết hợp để dễ filter
            self.data['Tháng_Năm'] = self.data.apply(lambda x: f"T{int(x['Tháng'])}/{int(x['Năm'])}", axis=1)
            self.data['Tuần_Tháng'] = self.data.apply(lambda x: f"W{int(x['Tuần'])}-T{int(x['Tháng'])}", axis=1)
            
            # ÁP DỤNG THỨ TỰ ƯU TIÊN
            self._apply_priority_order()
            
            # TÍNH TỶ LỆ SO VỚI TUẦN TRƯỚC
            self._calculate_week_over_week_ratio()
            
            return True
            
        except Exception as e:
            st.error(f"Lỗi khi xử lý DataFrame: {str(e)}")
            return False

    def load_data(self, file):
        """
        Load data directly from an Excel file (desktop path, BytesIO, or Streamlit
        UploadedFile object) and then process it via `load_data_from_dataframe`.

        Parameters
        ----------
        file : str | pathlib.Path | file‑like
            The file path or file‑like object pointing to an Excel workbook.

        Returns
        -------
        bool
            True if the data was loaded and processed successfully, otherwise False.
        """
        try:
            # Pandas can read from both file paths and file‑like objects
            df = pd.read_excel(file)
            return self.load_data_from_dataframe(df)
        except Exception as e:
            st.error(f"Lỗi khi đọc file Excel: {str(e)}")
            return False
    
    def _apply_priority_order(self):
        """Áp dụng thứ tự ưu tiên cho danh mục và nội dung"""
        # Thêm cột thứ tự ưu tiên cho danh mục
        self.data['Danh_mục_thứ_tự'] = self.data['Danh mục'].map(self.category_priority)
        
        # Thêm cột thứ tự ưu tiên cho nội dung
        self.data['Nội_dung_thứ_tự'] = self.data['Nội dung'].map(self.content_priority)
        
        # Gán thứ tự cao (999) cho các danh mục/nội dung không có trong danh sách ưu tiên
        self.data['Danh_mục_thứ_tự'] = self.data['Danh_mục_thứ_tự'].fillna(999)
        self.data['Nội_dung_thứ_tự'] = self.data['Nội_dung_thứ_tự'].fillna(999)
        
        # Sắp xếp dữ liệu theo thứ tự ưu tiên
        self.data = self.data.sort_values([
            'Danh_mục_thứ_tự', 
            'Nội_dung_thứ_tự', 
            'Năm', 
            'Tháng', 
            'Tuần'
        ]).reset_index(drop=True)
    
    def _calculate_week_over_week_ratio(self):
        """Tính tỷ lệ so với tuần trước - LOGIC MỚI"""
        # Khởi tạo cột
        self.data['Tỷ_lệ_tuần_trước'] = None
        self.data['Thay_đổi_tuần_trước'] = None
        
        # Group theo danh mục và nội dung, sau đó tính biến động
        for (category, content), group in self.data.groupby(['Danh mục', 'Nội dung']):
            # Sắp xếp theo năm, tháng, tuần
            group_sorted = group.sort_values(['Năm', 'Tháng', 'Tuần']).reset_index()
            
            # Bỏ qua tuần đầu tiên (không có tuần trước để so sánh)
            for i in range(1, len(group_sorted)):
                current_idx = group_sorted.loc[i, 'index']  # index gốc trong data
                current_value = group_sorted.loc[i, 'Số liệu']
                previous_value = group_sorted.loc[i-1, 'Số liệu']
                
                # Tính biến động
                if pd.notna(current_value) and pd.notna(previous_value):
                    if previous_value != 0:
                        # Công thức: (tuần hiện tại - tuần trước) / tuần trước * 100
                        ratio = ((current_value - previous_value) / previous_value) * 100
                        change = current_value - previous_value
                        
                        self.data.loc[current_idx, 'Tỷ_lệ_tuần_trước'] = ratio
                        self.data.loc[current_idx, 'Thay_đổi_tuần_trước'] = change
                    elif previous_value == 0 and current_value > 0:
                        # Tăng từ 0 lên số dương
                        self.data.loc[current_idx, 'Tỷ_lệ_tuần_trước'] = 999.0  # Vô hạn
                        self.data.loc[current_idx, 'Thay_đổi_tuần_trước'] = current_value
                    # Trường hợp khác (0->0, hoặc giá trị âm) giữ None
    
    def create_pivot_settings(self):
        """Tạo cài đặt cho pivot table"""
        st.sidebar.header("⚙️ Cài đặt Pivot Table")
        
        # Chọn kiểu báo cáo
        report_type = st.sidebar.selectbox(
            "Kiểu báo cáo",
            ["Theo Tuần", "Tùy chỉnh"]
        )
        
        # Chọn dòng và cột cho pivot
        col1, col2 = st.sidebar.columns(2)
        
        available_dims = ['Tuần', 'Tháng', 'Quý', 'Năm', 'Danh mục', 'Nội dung']
        
        with col1:
            rows = st.multiselect(
                "Chọn dòng (Rows)",
                available_dims,
                default=['Danh mục'] if report_type == "Tùy chỉnh" else self._get_default_rows(report_type)
            )
        
        with col2:
            cols = st.multiselect(
                "Chọn cột (Columns)",
                [dim for dim in available_dims if dim not in rows],
                default=self._get_default_cols(report_type)
            )
        
        # Chọn giá trị và phép tính
        values = st.sidebar.selectbox(
            "Giá trị hiển thị",
            ["Số liệu"]
        )
        
        agg_func = st.sidebar.selectbox(
            "Phép tính",
            ["sum", "mean", "count", "min", "max"],
            format_func=lambda x: {
                'sum': 'Tổng',
                'mean': 'Trung bình',
                'count': 'Đếm',
                'min': 'Nhỏ nhất',
                'max': 'Lớn nhất'
            }.get(x, x)
        )
        
        # Hiển thị biến động gộp vào giá trị
        show_ratio_inline = st.sidebar.checkbox("Hiển thị biến động trong giá trị", value=True)
        
        return report_type, rows, cols, values, agg_func, show_ratio_inline
    
    def _get_default_rows(self, report_type):
        """Lấy dòng mặc định theo kiểu báo cáo"""
        defaults = {
            "Theo Tuần": ['Danh mục', 'Nội dung'],
            "Theo Tháng": ['Danh mục'],
            "Theo Quý": ['Danh mục'],
            "Theo Năm": ['Danh mục']
        }
        return defaults.get(report_type, ['Danh mục'])
    
    def _get_default_cols(self, report_type):
        """Lấy cột mặc định theo kiểu báo cáo"""
        defaults = {
            "Theo Tuần": ['Tuần'],
            "Theo Tháng": ['Tháng'],
            "Theo Quý": ['Quý'],
            "Theo Năm": ['Năm']
        }
        return defaults.get(report_type, ['Tháng'])
    
    def create_quick_filters(self):
        """Tạo bộ lọc nhanh với các button"""
        st.sidebar.header("🚀 Bộ lọc nhanh")
        
        # Lấy thông tin thời gian hiện tại
        current_year = datetime.now().year
        current_month = datetime.now().month
        current_week = datetime.now().isocalendar()[1]  # ISO week number
        current_quarter = ((current_month - 1) // 3) + 1
        
        # Lấy tuần cao nhất trong dữ liệu
        max_week_in_data = int(self.data['Tuần'].max()) if not self.data.empty else current_week
        
        # Tạo 2 cột cho layout đẹp
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            # 4 tuần gần nhất
            if st.button("📅 4 tuần gần nhất", use_container_width=True, key="btn_4_weeks"):
                start_week = max(1, max_week_in_data - 3)
                st.session_state.quick_filter = {
                    'from_year': current_year,
                    'from_month': 1,
                    'from_week': start_week,
                    'to_year': current_year,
                    'to_month': 12,
                    'to_week': max_week_in_data,
                    'categories': list(self.data['Danh mục'].unique())
                }
                st.rerun()
            
            # Tháng này
            if st.button("📅 Tháng này", use_container_width=True, key="btn_this_month"):
                st.session_state.quick_filter = {
                    'from_year': current_year,
                    'from_month': current_month,
                    'from_week': 1,
                    'to_year': current_year,
                    'to_month': current_month,
                    'to_week': 53,
                    'categories': list(self.data['Danh mục'].unique())
                }
                st.rerun()
            
            # Quý này
            if st.button("📅 Quý này", use_container_width=True, key="btn_this_quarter"):
                quarter_start_month = (current_quarter - 1) * 3 + 1
                quarter_end_month = current_quarter * 3
                st.session_state.quick_filter = {
                    'from_year': current_year,
                    'from_month': quarter_start_month,
                    'from_week': 1,
                    'to_year': current_year,
                    'to_month': quarter_end_month,
                    'to_week': 53,
                    'categories': list(self.data['Danh mục'].unique())
                }
                st.rerun()
            
            # 6 tháng đầu năm (1-6)
            if st.button("📅 6 tháng đầu năm", use_container_width=True, key="btn_first_half"):
                st.session_state.quick_filter = {
                    'from_year': current_year,
                    'from_month': 1,
                    'from_week': 1,
                    'to_year': current_year,
                    'to_month': 6,
                    'to_week': 53,
                    'categories': list(self.data['Danh mục'].unique())
                }
                st.rerun()
        
        with col2:
            # Tất cả
            if st.button("📅 Tất cả", use_container_width=True, key="btn_all"):
                years = sorted(self.data['Năm'].unique())
                st.session_state.quick_filter = {
                    'from_year': years[0] if years else current_year,
                    'from_month': 1,
                    'from_week': 1,
                    'to_year': years[-1] if years else current_year,
                    'to_month': 12,
                    'to_week': 53,
                    'categories': list(self.data['Danh mục'].unique())
                }
                st.rerun()
            
            # Tháng trước
            if st.button("📅 Tháng trước", use_container_width=True, key="btn_last_month"):
                last_month = current_month - 1 if current_month > 1 else 12
                last_month_year = current_year if current_month > 1 else current_year - 1
                st.session_state.quick_filter = {
                    'from_year': last_month_year,
                    'from_month': last_month,
                    'from_week': 1,
                    'to_year': last_month_year,
                    'to_month': last_month,
                    'to_week': 53,
                    'categories': list(self.data['Danh mục'].unique())
                }
                st.rerun()
            
            # Quý trước
            if st.button("📅 Quý trước", use_container_width=True, key="btn_last_quarter"):
                last_quarter = current_quarter - 1 if current_quarter > 1 else 4
                last_quarter_year = current_year if current_quarter > 1 else current_year - 1
                quarter_start_month = (last_quarter - 1) * 3 + 1
                quarter_end_month = last_quarter * 3
                st.session_state.quick_filter = {
                    'from_year': last_quarter_year,
                    'from_month': quarter_start_month,
                    'from_week': 1,
                    'to_year': last_quarter_year,
                    'to_month': quarter_end_month,
                    'to_week': 53,
                    'categories': list(self.data['Danh mục'].unique())
                }
                st.rerun()
            
            # 6 tháng cuối năm (7-12)
            if st.button("📅 6 tháng cuối năm", use_container_width=True, key="btn_second_half"):
                st.session_state.quick_filter = {
                    'from_year': current_year,
                    'from_month': 7,
                    'from_week': 1,
                    'to_year': current_year,
                    'to_month': 12,
                    'to_week': 53,
                    'categories': list(self.data['Danh mục'].unique())
                }
                st.rerun()
        
        # Hiển thị bộ lọc hiện tại
        if 'quick_filter' in st.session_state:
            filter_info = st.session_state.quick_filter
            st.sidebar.success(f"✅ Đã áp dụng bộ lọc nhanh")
            st.sidebar.info(f"📅 Từ: {filter_info['from_month']}/{filter_info['from_year']} (tuần {filter_info['from_week']})\n"
                        f"📅 Đến: {filter_info['to_month']}/{filter_info['to_year']} (tuần {filter_info['to_week']})")
        
        st.sidebar.markdown("---")

    def create_filters(self):
        """Tạo bộ lọc dữ liệu - CẬP NHẬT để tích hợp với quick filter"""
        
        # THÊM BỘ LỌC NHANH TRƯỚC
        self.create_quick_filters()
        
        st.sidebar.header("🔍 Lọc dữ liệu chi tiết")

        # ----- KHUNG THỜI GIAN: TỪ ... ĐẾN ... -----
        years = sorted(self.data['Năm'].unique())
        months_list = list(range(1, 13))
        weeks_list = list(range(1, 53))

        # Sử dụng giá trị từ quick filter nếu có, nếu không dùng mặc định
        if 'quick_filter' in st.session_state:
            default_from_year = st.session_state.quick_filter['from_year']
            default_from_month = st.session_state.quick_filter['from_month']
            default_from_week = st.session_state.quick_filter['from_week']
            default_to_year = st.session_state.quick_filter['to_year']
            default_to_month = st.session_state.quick_filter['to_month']
            default_to_week = st.session_state.quick_filter['to_week']
            default_categories = st.session_state.quick_filter['categories']
        else:
            default_from_year = years[0] if years else datetime.now().year
            default_from_month = 1
            default_from_week = 1
            default_to_year = years[-1] if years else datetime.now().year
            default_to_month = 12
            default_to_week = 52
            default_categories = list(self.data['Danh mục'].unique())

        # Tính toán index an toàn cho selectbox
        def safe_get_index(value, options_list):
            """Lấy index an toàn, tránh lỗi nếu value không có trong list"""
            try:
                return options_list.index(value)
            except (ValueError, IndexError):
                return 0

        st.sidebar.subheader("⏱️ Từ (From)")
        from_year = st.sidebar.selectbox("Năm bắt đầu", years, 
                                    index=safe_get_index(default_from_year, years), 
                                    key="from_year")
        from_month = st.sidebar.selectbox("Tháng bắt đầu", months_list, 
                                        index=max(0, min(default_from_month - 1, len(months_list) - 1)), 
                                        key="from_month")
        from_week = st.sidebar.selectbox("Tuần bắt đầu", weeks_list, 
                                    index=max(0, min(default_from_week - 1, len(weeks_list) - 1)), 
                                    key="from_week")

        st.sidebar.subheader("⏱️ Đến (To)")
        to_year = st.sidebar.selectbox("Năm kết thúc", years, 
                                    index=safe_get_index(default_to_year, years) if years else 0, 
                                    key="to_year")
        to_month = st.sidebar.selectbox("Tháng kết thúc", months_list, 
                                    index=max(0, min(default_to_month - 1, len(months_list) - 1)), 
                                    key="to_month")
        to_week = st.sidebar.selectbox("Tuần kết thúc", weeks_list, 
                                    index=max(0, min(default_to_week - 1, len(weeks_list) - 1)), 
                                    key="to_week")

        # -------- CHỌN DANH MỤC --------
        unique_categories = self.data['Danh mục'].unique()
        sorted_categories = sorted(unique_categories,
                                key=lambda x: self.category_priority.get(x, 999))

        selected_categories = []
        with st.sidebar.expander("📂 Chọn danh mục", expanded=True):
            # Kiểm tra xem có bộ lọc nhanh không để quyết định select_all
            if 'quick_filter' in st.session_state:
                select_all = st.checkbox("Chọn tất cả danh mục", value=True, key="select_all_cat")
            else:
                select_all = st.checkbox("Chọn tất cả danh mục", value=True, key="select_all_cat")
                
            if select_all:
                selected_categories = list(sorted_categories)
            else:
                for category in sorted_categories:
                    category_selected = st.checkbox(f"📁 {category}", 
                                                value=category in default_categories, 
                                                key=f"cat_{category}")
                    if category_selected:
                        selected_categories.append(category)

        # Reset quick filter button
        if st.sidebar.button("🔄 Reset bộ lọc nhanh", help="Xóa bộ lọc nhanh đã chọn"):
            if 'quick_filter' in st.session_state:
                del st.session_state.quick_filter
            st.sidebar.success("✅ Đã reset bộ lọc nhanh!")
            st.rerun()

        return from_year, from_month, from_week, to_year, to_month, to_week, selected_categories
        
    def filter_data(self, from_year, from_month, from_week, to_year, to_month, to_week, categories):
        """Lọc dữ liệu theo khoảng tuần–tháng–năm"""
        filtered = self.data.copy()

        # Điều kiện bắt đầu
        cond_start = (
            (filtered['Năm'] > from_year) |
            ((filtered['Năm'] == from_year) & (filtered['Tháng'] > from_month)) |
            ((filtered['Năm'] == from_year) & (filtered['Tháng'] == from_month) & (filtered['Tuần'] >= from_week))
        )

        # Điều kiện kết thúc
        cond_end = (
            (filtered['Năm'] < to_year) |
            ((filtered['Năm'] == to_year) & (filtered['Tháng'] < to_month)) |
            ((filtered['Năm'] == to_year) & (filtered['Tháng'] == to_month) & (filtered['Tuần'] <= to_week))
        )

        filtered = filtered[cond_start & cond_end & (filtered['Danh mục'].isin(categories))]

        return filtered

    def aggregate_data_by_report_type(self, data, report_type):
        """Tự động aggregate dữ liệu theo loại báo cáo"""
        if report_type == "Theo Tuần":
            # Giữ nguyên dữ liệu tuần
            return data
        
        elif report_type == "Theo Tháng":
            # Aggregate theo tháng
            aggregated = data.groupby([
                'Danh mục', 'Nội dung', 'Năm', 'Tháng', 'Quý',
                'Danh_mục_thứ_tự', 'Nội_dung_thứ_tự'
            ]).agg({
                'Số liệu': 'sum'  # Tổng theo tháng
            }).reset_index()
            
            # Tạo lại các cột cần thiết
            aggregated['Tháng_Năm'] = aggregated.apply(lambda x: f"T{int(x['Tháng'])}/{int(x['Năm'])}", axis=1)
            
            # Không tính biến động cho aggregate theo tháng (có thể thêm sau)
            aggregated['Tỷ_lệ_tuần_trước'] = None
            aggregated['Thay_đổi_tuần_trước'] = None
            
            return aggregated
        
        elif report_type == "Theo Quý":
            # Aggregate theo quý
            aggregated = data.groupby([
                'Danh mục', 'Nội dung', 'Năm', 'Quý',
                'Danh_mục_thứ_tự', 'Nội_dung_thứ_tự'
            ]).agg({
                'Số liệu': 'sum'  # Tổng theo quý
            }).reset_index()
            
            # Không tính biến động cho aggregate theo quý
            aggregated['Tỷ_lệ_tuần_trước'] = None
            aggregated['Thay_đổi_tuần_trước'] = None
            
            return aggregated
        
        elif report_type == "Theo Năm":
            # Aggregate theo năm
            aggregated = data.groupby([
                'Danh mục', 'Nội dung', 'Năm',
                'Danh_mục_thứ_tự', 'Nội_dung_thứ_tự'
            ]).agg({
                'Số liệu': 'sum'  # Tổng theo năm
            }).reset_index()
            
            # Không tính biến động cho aggregate theo năm
            aggregated['Tỷ_lệ_tuần_trước'] = None
            aggregated['Thay_đổi_tuần_trước'] = None
            
            return aggregated
        
        else:  # Tùy chỉnh
            return data
    
    def format_value_with_change(self, value, ratio, change):
        """Định dạng giá trị với biến động inline - CẢI TIẾN ĐỂ HIỂN THỊ RÕ RÀNG HƠN"""
        # Đảm bảo hiển thị số đầy đủ
        value_str = f"{value:,.0f}".replace(',', '.')
        
        if pd.isna(ratio) or ratio == 0:
            return value_str
        
        if ratio == 999:  # Vô hạn
            return f"{value_str} <span class='positive-change'>↑∞%</span>"
        
        if ratio > 0:
            symbol = "↑"
            color_class = "positive-change"
        elif ratio < 0:
            symbol = "↓"  
            color_class = "negative-change"
        else:
            symbol = "→"
            color_class = "no-change"
            
        ratio_text = f"{abs(ratio):.1f}%"
        
        # FORMAT RÕ RÀNG: số (biến động)
        return f"{value_str} <span class='{color_class}'>({symbol}{ratio_text})</span>"
    
    def create_hierarchical_pivot_table_with_ratio(self, data, rows, cols, values, agg_func, show_ratio_inline):
        try:
            if not rows and not cols:
                st.warning("Vui lòng chọn ít nhất một chiều cho dòng hoặc cột")
                return None
            
            # Đảm bảo dữ liệu đã được sắp xếp theo thứ tự ưu tiên
            if 'Danh mục' in rows:
                data = data.sort_values(['Danh_mục_thứ_tự', 'Nội_dung_thứ_tự'])
            
            # ========== SỬ DỤNG SMART AGGREGATION ==========
            # Tạo pivot table cho giá trị chính
            # Tạo pivot table cho giá trị chính
            if cols:
                pivot = self.apply_smart_aggregation(data, rows, cols, values)
    
            # ============= SẮP XẾP CỘT TUẦN GIẢM DẦN =============
            if 'Tuần' in cols and hasattr(pivot, 'columns'):
                # Lấy danh sách cột hiện tại
                current_columns = list(pivot.columns)
        
                # Tách cột tuần và cột khác
                week_columns = []
                other_columns = []
        
                for col in current_columns:
                    try:
                        # XỬ LÝ MULTIINDEX - Kiểm tra xem có phải là tuple không
                        if isinstance(col, tuple):
                            # Nếu là MultiIndex, tìm phần tử là số tuần
                            week_found = False
                            for element in col:
                                try:
                                    week_num = int(str(element).strip())
                                    if 1 <= week_num <= 53:  # Tuần hợp lệ
                                        week_columns.append(col)
                                        week_found = True
                                        break
                                except (ValueError, TypeError):
                                    continue
                            if not week_found:
                                other_columns.append(col)
                        else:
                            # Xử lý cột đơn lẻ như cũ
                            week_num = int(str(col).strip())
                            if 1 <= week_num <= 53:  # Tuần hợp lệ
                                week_columns.append(col)
                            else:
                                other_columns.append(col)
                    except (ValueError, TypeError):
                        other_columns.append(col)
                
                # Chỉ thực hiện sắp xếp và thông báo nếu có cột tuần
                if week_columns:
                    # Sắp xếp tuần theo thứ tự GIẢM DẦN (tuần cao nhất trước)
                    if isinstance(current_columns[0], tuple):
                        # Với MultiIndex, sắp xếp theo phần tử tuần
                        week_columns_sorted = sorted(week_columns, 
                            key=lambda x: max([int(str(e)) for e in x if str(e).isdigit() and 1 <= int(str(e)) <= 53]), 
                            reverse=True)
                    else:
                        # Với single index
                        week_columns_sorted = sorted(week_columns, key=lambda x: int(str(x)), reverse=True)
                    
                    # Tái tạo thứ tự cột: tuần (giảm dần) + cột khác
                    new_column_order = week_columns_sorted + other_columns
                    
                    # Reindex pivot table với thứ tự mới
                    pivot = pivot.reindex(columns=new_column_order)
                    
                    # Lấy min/max tuần để hiển thị thông báo
                    week_numbers = []
                    for col in week_columns:
                        if isinstance(col, tuple):
                            for element in col:
                                try:
                                    week_num = int(str(element).strip())
                                    if 1 <= week_num <= 53:
                                        week_numbers.append(week_num)
                                        break
                                except (ValueError, TypeError):
                                    continue
                        else:
                            try:
                                week_num = int(str(col).strip())
                                if 1 <= week_num <= 53:
                                    week_numbers.append(week_num)
                            except (ValueError, TypeError):
                                continue
                    
                    if week_numbers:
                        st.sidebar.info(f"📅 Hiển thị từ tuần {max(week_numbers)} → tuần {min(week_numbers)}")
            # ===============================================
            
            # Nếu cần hiển thị biến động inline (CHỈ CHO BÁO CÁO THEO TUẦN)
            if show_ratio_inline and cols and 'Tuần' in cols:
                # Lọc dữ liệu có biến động
                ratio_data = data[pd.notna(data['Tỷ_lệ_tuần_trước'])].copy()
                
                if not ratio_data.empty:
                    try:
                        # Tạo pivot table cho giá trị gốc với smart aggregation
                        main_pivot = self.apply_smart_aggregation(data, rows, cols, 'Số liệu')
                        
                        # ============= SẮP XẾP CỘT CHO MAIN_PIVOT =============
                        if hasattr(main_pivot, 'columns'):
                            current_columns = list(main_pivot.columns)
                            week_columns = []
                            other_columns = []
                            
                            for col in current_columns:
                                try:
                                    week_num = int(str(col).strip())
                                    if 1 <= week_num <= 53:
                                        week_columns.append(col)
                                    else:
                                        other_columns.append(col)
                                except (ValueError, TypeError):
                                    other_columns.append(col)
                            
                            # Sắp xếp tuần giảm dần
                            week_columns_sorted = sorted(week_columns, key=lambda x: int(str(x)), reverse=True)
                            new_column_order = week_columns_sorted + other_columns
                            
                            main_pivot = main_pivot.reindex(columns=new_column_order)
                        # ====================================================
                        
                        # Tạo pivot table cho tỷ lệ biến động
                        ratio_pivot = pd.pivot_table(
                            ratio_data,
                            index=rows if rows else None,
                            columns=cols,
                            values='Tỷ_lệ_tuần_trước',
                            aggfunc='mean',
                            fill_value=None
                        )
                        
                        # ============= SẮP XẾP CỘT CHO RATIO_PIVOT =============
                        if hasattr(ratio_pivot, 'columns'):
                            current_columns = list(ratio_pivot.columns)
                            week_columns = []
                            other_columns = []
                            
                            for col in current_columns:
                                try:
                                    week_num = int(str(col).strip())
                                    if 1 <= week_num <= 53:
                                        week_columns.append(col)
                                    else:
                                        other_columns.append(col)
                                except (ValueError, TypeError):
                                    other_columns.append(col)
                            
                            week_columns_sorted = sorted(week_columns, key=lambda x: int(str(x)), reverse=True)
                            new_column_order = week_columns_sorted + other_columns
                            
                            ratio_pivot = ratio_pivot.reindex(columns=new_column_order)
                        # ====================================================
                        
                        # Tạo combined pivot với biến động
                        combined_pivot = main_pivot.copy()
                        
                        # Áp dụng biến động cho từng ô
                        for idx in main_pivot.index:
                            for col in main_pivot.columns:
                                main_value = main_pivot.loc[idx, col]
                                
                                # Kiểm tra có biến động không
                                if idx in ratio_pivot.index and col in ratio_pivot.columns:
                                    ratio_val = ratio_pivot.loc[idx, col]
                                    if pd.notna(ratio_val):
                                        # Có biến động - format với %
                                        combined_pivot.loc[idx, col] = self.format_value_with_change(main_value, ratio_val, 0)
                                        continue
                                
                                # Không có biến động - chỉ hiển thị số
                                combined_pivot.loc[idx, col] = f"{main_value:,.0f}".replace(',', '.')
                        
                        # THÊM CỘT TỔNG - SMART AGGREGATION
                        combined_pivot['Tổng'] = ""
                        for idx in combined_pivot.index:
                            # Lấy nội dung để xác định cách tính tổng
                            if isinstance(idx, tuple) and len(idx) > 1:
                                content = idx[1]  # Nội dung thường ở vị trí thứ 2
                            else:
                                content = str(idx)
                            
                            agg_method = self.get_aggregation_method(content)
                            
                            row_total = 0
                            row_count = 0
                            
                            for col in main_pivot.columns:
                                val = main_pivot.loc[idx, col]
                                if pd.notna(val) and val != 0:
                                    if agg_method == "mean":
                                        row_total += float(val)
                                        row_count += 1
                                    elif agg_method == "last":
                                        # Với 'last', lấy giá trị mới nhất (cột đầu tiên)
                                        row_total = float(val)
                                        break
                                    else:  # sum
                                        row_total += float(val)
                            
                            # Format tổng
                            if agg_method == "mean" and row_count > 0:
                                avg_value = row_total / row_count
                                combined_pivot.loc[idx, 'Tổng'] = f"{avg_value:,.1f}".replace(',', '.')
                            else:
                                combined_pivot.loc[idx, 'Tổng'] = f"{row_total:,.0f}".replace(',', '.')
                        
                        return combined_pivot
                        
                    except Exception as e:
                        st.sidebar.error(f"Lỗi tạo biến động: {str(e)}")
                        pass
            
            # Nếu không có biến động - format số đẹp và thêm cột tổng
            if isinstance(pivot, pd.DataFrame):
                pivot_formatted = pivot.copy()
                
                # Format tất cả số thành dạng đẹp
                for idx in pivot_formatted.index:
                    for col in pivot_formatted.columns:
                        val = pivot.loc[idx, col]
                        if pd.notna(val):
                            pivot_formatted.loc[idx, col] = f"{val:,.1f}".replace(',', '.')
                
                # THÊM CỘT TỔNG - SMART AGGREGATION
                pivot_formatted['Tổng'] = ""
                for idx in pivot_formatted.index:
                    # Lấy nội dung để xác định cách tính tổng
                    if isinstance(idx, tuple) and len(idx) > 1:
                        content = idx[1]  # Nội dung thường ở vị trí thứ 2
                    else:
                        content = str(idx)
                    
                    agg_method = self.get_aggregation_method(content)
                    
                    row_total = 0
                    row_count = 0
                    
                    for col in pivot.columns:
                        val = pivot.loc[idx, col]
                        if pd.notna(val) and val != 0:
                            if agg_method == "mean":
                                row_total += float(val)
                                row_count += 1
                            elif agg_method == "last":
                                # Với 'last', lấy giá trị mới nhất (cột đầu tiên)
                                row_total = float(val)
                                break
                            else:  # sum
                                row_total += float(val)
                    
                    # Format tổng
                    if agg_method == "mean" and row_count > 0:
                        avg_value = row_total / row_count
                        pivot_formatted.loc[idx, 'Tổng'] = f"{avg_value:,.1f}".replace(',', '.')
                    elif agg_method == "last":
                        pivot_formatted.loc[idx, 'Tổng'] = f"{row_total:,.0f}".replace(',', '.')
                    else:
                        pivot_formatted.loc[idx, 'Tổng'] = f"{row_total:,.0f}".replace(',', '.')
                
                return pivot_formatted
            
            return pivot
            
        except Exception as e:
            st.error(f"Lỗi tạo pivot table: {str(e)}")
            return None

 
    def display_category_sparklines(self, category_data, category_name, report_type):
        """Hiển thị sparklines cho từng nội dung trong danh mục"""
        try:
            if not isinstance(category_data, pd.DataFrame):
                return
            
            # Tạo sparklines cho từng nội dung trong danh mục
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.markdown("**Nội dung**")
            with col2:
                st.markdown("**Xu hướng**")
            with col3:
                st.markdown("**Tổng hàng**")
            
            for content in category_data.index:
                # Lấy dữ liệu cho nội dung này
                content_values = []
                for col in category_data.columns:
                    val = category_data.loc[content, col]
                    if isinstance(val, str):
                        # Extract số từ HTML
                        import re
                        numbers = re.findall(r'[\d.]+', val.replace('.', ''))
                        if numbers:
                            content_values.append(int(numbers[0].replace('.', '')))
                        else:
                            content_values.append(0)
                    else:
                        content_values.append(val if pd.notna(val) else 0)
                
                # Tạo sparkline
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    y=content_values,
                    mode='lines+markers',
                    line=dict(width=2, color='royalblue'),
                    marker=dict(size=3),
                    showlegend=False
                ))
                
                # Highlight max/min
                if content_values and max(content_values) > 0:
                    max_idx = np.argmax(content_values)
                    min_idx = np.argmin(content_values)
                    
                    fig.add_trace(go.Scatter(
                        x=[max_idx], y=[content_values[max_idx]],
                        mode='markers', marker=dict(size=5, color='green'),
                        showlegend=False
                    ))
                    fig.add_trace(go.Scatter(
                        x=[min_idx], y=[content_values[min_idx]],
                        mode='markers', marker=dict(size=5, color='red'),
                        showlegend=False
                    ))
                
                fig.update_layout(
                    margin=dict(l=0, r=0, t=0, b=0),
                    height=40, width=200,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
                    yaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
                    hovermode=False
                )
                
                # Tính tổng hàng
                row_total = sum(content_values)
                
                # Hiển thị
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.markdown(f"📄 {content}")
                with col2:
                    st.plotly_chart(fig, use_container_width=True, key=f"spark_{category_name}_{content}")
                with col3:
                    st.markdown(f"**{row_total:,.0f}**".replace(',', '.'))
                    
        except Exception as e:
            st.error(f"Lỗi tạo sparkline cho {category_name}: {str(e)}")
    
    def display_hierarchical_pivot_improved(self, pivot, data):
        """Hiển thị pivot table với cấu trúc phân cấp cải tiến - Sparkline ở dưới cùng"""
        if pivot is None:
            return
        
        # Kiểm tra xem có phải pivot table với Danh mục không
        if isinstance(pivot.index, pd.MultiIndex) and 'Danh mục' in pivot.index.names:
            # Hiển thị theo cấu trúc phân cấp
            
            # Lấy danh sách các danh mục theo thứ tự ưu tiên
            categories = pivot.index.get_level_values('Danh mục').unique()
            sorted_categories = sorted(categories, key=lambda x: self.category_priority.get(x, 999))
            
            # PHẦN 1: HIỂN THỊ PIVOT TABLE CHO TỪNG DANH MỤC
            for category in sorted_categories:
                # Expander without label; we'll render a custom styled header inside
                with st.expander("", expanded=True):
                    # Category title: bigger, bold, subtle background
                    st.markdown(f"<div class='category-header'>📁 {category}</div>", unsafe_allow_html=True)
                    # Lọc dữ liệu cho danh mục này
                    category_data = pivot.xs(category, level='Danh mục')
                    
                    # Sắp xếp theo thứ tự ưu tiên nội dung
                    if isinstance(category_data.index, pd.Index):
                        # Lấy danh sách nội dung và sắp xếp
                        contents = category_data.index.tolist()
                        sorted_contents = sorted(contents, key=lambda x: self.content_priority.get(x, 999))
                        category_data = category_data.reindex(sorted_contents)
                    
                    # HIỂN THỊ BẢNG DỮ LIỆU
                    if isinstance(category_data, pd.DataFrame):
                        # Tạo HTML table để hiển thị đầy đủ số
                        html_table = "<div class='full-width-table'>"
                        html_table += "<table style='width:100%; border-collapse: collapse; font-size: 15px;'>"
                        
                        # Header
                        html_table += "<tr style='background-color: #f0f2f6;'>"
                        html_table += "<th style='border: 1px solid #ddd; padding: 8px; text-align: left; min-width: 250px; position: sticky; left: 0; background-color: #f0f2f6; z-index: 10;'>Nội dung</th>"
                        for col in category_data.columns:
                            if col == 'Tổng':
                                html_table += f"<th style='border: 1px solid #ddd; padding: 8px; text-align: center; min-width: 120px; position: sticky; right: 0; background-color: #f0f2f6; z-index: 10; font-weight: bold;'>{col}</th>"
                            else:
                                html_table += f"<th style='border: 1px solid #ddd; padding: 8px; text-align: center; min-width: 150px;'>{col}</th>"
                        html_table += "</tr>"
                        
                        # Data rows
                        for content in category_data.index:
                            html_table += "<tr>"
                            html_table += f"<td style='border: 1px solid #ddd; padding: 8px; font-weight: bold; position: sticky; left: 0; background-color: #f8f9fa; z-index: 10;'>{content}</td>"
                            
                            for col in category_data.columns:
                                value = category_data.loc[content, col]
                                if col == 'Tổng':
                                    html_table += f"<td style='border: 1px solid #ddd; padding: 8px; text-align: right; position: sticky; right: 0; background-color: #e9ecef; z-index: 10; font-weight: bold;' class='number-cell'>{value}</td>"
                                else:
                                    html_table += f"<td style='border: 1px solid #ddd; padding: 8px; text-align: right;' class='number-cell'>{value}</td>"
                            
                            html_table += "</tr>"
                        
                        html_table += "</table></div>"
                        st.markdown(html_table, unsafe_allow_html=True)
                    
                    else:
                        # Nếu là Series
                        html_table = "<div class='full-width-table'>"
                        html_table += "<table style='width:100%; border-collapse: collapse; font-size: 12px;'>"
                        html_table += "<tr style='background-color: #f0f2f6;'>"
                        html_table += "<th style='border: 1px solid #ddd; padding: 8px;'>Danh mục</th>"
                        html_table += "<th style='border: 1px solid #ddd; padding: 8px;'>Giá trị</th>"
                        html_table += "</tr>"
                        html_table += "<tr>"
                        html_table += f"<td style='border: 1px solid #ddd; padding: 8px;'>{category}</td>"
                        formatted_value = f"{category_data:,.0f}".replace(',', '.') if isinstance(category_data, (int, float, np.integer, np.floating)) else str(category_data)
                        html_table += f"<td style='border: 1px solid #ddd; padding: 8px; text-align: right;' class='number-cell'>{formatted_value}</td>"
                        html_table += "</tr>"
                        html_table += "</table></div>"
                        st.markdown(html_table, unsafe_allow_html=True)
            
            # PHẦN 2: HIỂN THỊ SPARKLINE CHỈ CHO BÁO CÁO THEO TUẦN
            # Kiểm tra nếu pivot có cột là số tuần (hoặc đã chọn báo cáo theo tuần)
            if any(str(col).strip().isdigit() for col in pivot.columns if col != 'Tổng'):
                st.markdown("---")  # Đường phân cách
                st.subheader("📈 Biểu đồ xu hướng tổng hợp theo từng nội dung")
                st.markdown("*Xu hướng biến động qua các tuần cho mỗi nội dung công việc*")
                
                # Tạo container cho sparklines
                sparkline_data_all = {}
                
                # Thu thập dữ liệu sparkline cho tất cả danh mục
                for category in sorted_categories:
                    try:
                        category_data = pivot.xs(category, level='Danh mục')
                        
                        if isinstance(category_data, pd.DataFrame):
                            # Sắp xếp theo thứ tự ưu tiên nội dung
                            contents = category_data.index.tolist()
                            sorted_contents = sorted(contents, key=lambda x: self.content_priority.get(x, 999))
                            category_data = category_data.reindex(sorted_contents)
                            
                            # Lưu vào dict chung
                            sparkline_data_all[category] = {
                                'data': category_data,
                                'contents': sorted_contents
                            }
                    except Exception as e:
                        continue
                
                # Hiển thị sparklines theo danh mục
                for category in sorted_categories:
                    if category in sparkline_data_all:
                        with st.expander(f"📊 Xu hướng: {category}", expanded=False):
                            category_info = sparkline_data_all[category]
                            category_data = category_info['data']
                            
                            try:
                                # Header cho bảng sparkline
                                st.markdown("**📊 Xu hướng biến động cho từng nội dung:**")
                                
                                # Tạo bảng sparkline cho danh mục này
                                sparkline_rows = []
                                
                                for content in category_info['contents']:
                                    # Lấy dữ liệu cho nội dung này
                                    content_values = []
                                    for col in category_data.columns:
                                        if col != 'Tổng':  # Bỏ qua cột Tổng khi tính sparkline
                                            val = category_data.loc[content, col]
                                            if isinstance(val, str):
                                                # Extract số từ HTML
                                                import re
                                                numbers = re.findall(r'[\d.]+', val.replace('.', ''))
                                                if numbers:
                                                    content_values.append(int(numbers[0].replace('.', '')))
                                                else:
                                                    content_values.append(0)
                                            else:
                                                content_values.append(val if pd.notna(val) else 0)
                                    
                                    # Tạo sparkline
                                    fig = go.Figure()
                                    fig.add_trace(go.Scatter(
                                        y=content_values,
                                        mode='lines+markers',
                                        line=dict(width=2, color='royalblue'),
                                        marker=dict(size=3),
                                        showlegend=False
                                    ))
                                    
                                    # Highlight max/min
                                    if content_values and max(content_values) > 0:
                                        max_idx = np.argmax(content_values)
                                        min_idx = np.argmin(content_values)
                                        
                                        fig.add_trace(go.Scatter(
                                            x=[max_idx], y=[content_values[max_idx]],
                                            mode='markers', marker=dict(size=5, color='green'),
                                            showlegend=False
                                        ))
                                        fig.add_trace(go.Scatter(
                                            x=[min_idx], y=[content_values[min_idx]],
                                            mode='markers', marker=dict(size=5, color='red'),
                                            showlegend=False
                                        ))
                                    
                                    fig.update_layout(
                                        margin=dict(l=0, r=0, t=0, b=0),
                                        height=40, width=200,
                                        paper_bgcolor='rgba(0,0,0,0)',
                                        plot_bgcolor='rgba(0,0,0,0)',
                                        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
                                        yaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
                                        hovermode=False
                                    )
                                    
                                    # Lấy tổng hàng từ cột Tổng
                                    row_total = category_data.loc[content, 'Tổng'] if 'Tổng' in category_data.columns else sum(content_values)
                                    
                                    # Lưu vào danh sách
                                    sparkline_rows.append({
                                        'content': content,
                                        'fig': fig,
                                        'total': row_total,
                                        'values': content_values
                                    })
                                
                                # Hiển thị từng row với sparkline trong layout 3 cột
                                for row_data in sparkline_rows:
                                    col1, col2, col3 = st.columns([3, 2, 1])
                                    
                                    with col1:
                                        st.markdown(f"📄 {row_data['content']}")
                                    
                                    with col2:
                                        st.plotly_chart(row_data['fig'], use_container_width=True, 
                                                    key=f"spark_{category}_{row_data['content']}")
                                    
                                    with col3:
                                        if isinstance(row_data['total'], str):
                                            st.markdown(f"**{row_data['total']}**")
                                        else:
                                            st.markdown(f"**{row_data['total']:,.0f}**".replace(',', '.'))
                                
                                # Thống kê tổng quan cho danh mục
                                total_category = sum([sum(row['values']) for row in sparkline_rows])
                                avg_per_content = total_category / len(sparkline_rows) if sparkline_rows else 0
                                
                                st.info(f"""
                                📊 **Tổng quan {category}:**
                                - 📈 Tổng cộng: {total_category:,.0f}
                                - 📊 Trung bình/nội dung: {avg_per_content:,.0f}
                                - 📋 Số nội dung: {len(sparkline_rows)}
                                """.replace(',', '.'))
                                        
                            except Exception as e:
                                st.error(f"Lỗi tạo sparkline cho {category}: {str(e)}")
        
        elif 'Danh mục' in pivot.index.names:
            # Hiển thị đơn giản với Danh mục
            categories = pivot.index.unique()
            sorted_categories = sorted(categories, key=lambda x: self.category_priority.get(x, 999))
            
            for category in sorted_categories:
                with st.expander(f"📁 {category}", expanded=True):
                    category_data = pivot.loc[category]
                    
                    html_table = "<table style='width:100%; border-collapse: collapse;'>"
                    html_table += "<tr style='background-color: #f0f2f6;'>"
                    html_table += "<th style='border: 1px solid #ddd; padding: 8px;'>Danh mục</th>"
                    html_table += "<th style='border: 1px solid #ddd; padding: 8px;'>Giá trị</th>"
                    html_table += "</tr>"
                    html_table += "<tr>"
                    html_table += f"<td style='border: 1px solid #ddd; padding: 8px;'>{category}</td>"
                    html_table += f"<td style='border: 1px solid #ddd; padding: 8px; text-align: right;' class='number-cell'>{category_data}</td>"
                    html_table += "</tr>"
                    html_table += "</table>"
                    st.markdown(html_table, unsafe_allow_html=True)
        
        else:
            # Hiển thị pivot table thông thường
            st.subheader("📊 Pivot Table")
            
            html_table = "<div class='full-width-table'>"
            html_table += "<table style='width:100%; border-collapse: collapse; font-size: 12px;'>"
            
            # Header
            html_table += "<tr style='background-color: #f0f2f6;'>"
            html_table += "<th style='border: 1px solid #ddd; padding: 8px;'>Index</th>"
            if isinstance(pivot, pd.DataFrame):
                for col in pivot.columns:
                    html_table += f"<th style='border: 1px solid #ddd; padding: 8px; text-align: center;'>{col}</th>"
            else:
                html_table += "<th style='border: 1px solid #ddd; padding: 8px; text-align: center;'>Giá trị</th>"
            html_table += "</tr>"
            
            # Data
            if isinstance(pivot, pd.DataFrame):
                for idx in pivot.index:
                    html_table += "<tr>"
                    html_table += f"<td style='border: 1px solid #ddd; padding: 8px;'>{idx}</td>"
                    for col in pivot.columns:
                        value = pivot.loc[idx, col]
                        html_table += f"<td style='border: 1px solid #ddd; padding: 8px; text-align: right;' class='number-cell'>{value}</td>"
                    html_table += "</tr>"
            else:
                for idx in pivot.index:
                    html_table += "<tr>"
                    html_table += f"<td style='border: 1px solid #ddd; padding: 8px;'>{idx}</td>"
                    html_table += f"<td style='border: 1px solid #ddd; padding: 8px; text-align: right;' class='number-cell'>{pivot.loc[idx]}</td>"
                    html_table += "</tr>"
            
            html_table += "</table></div>"
            st.markdown(html_table, unsafe_allow_html=True)
    
    def create_sparkline_charts(self, pivot, report_type):
        """Tạo biểu đồ sparkline cho mỗi dòng trong pivot table"""
        if pivot is None or not isinstance(pivot, pd.DataFrame):
            return None
        
        # Xác định cột thời gian dựa vào report_type
        time_column_name = {
            "Theo Tuần": "Tuần",
            "Theo Tháng": "Tháng",
            "Theo Quý": "Quý",
            "Theo Năm": "Năm"
        }.get(report_type, "Tháng")
        
        # Tạo dataframe cho biểu đồ
        sparklines_data = {}
        
        # Reset index để dễ dàng xử lý
        if isinstance(pivot.index, pd.MultiIndex):
            pivot_reset = pivot.reset_index()
        else:
            pivot_reset = pivot.reset_index()
            
        # Lấy tên của các cột chứa giá trị
        value_columns = [col for col in pivot.columns 
                         if not isinstance(col, tuple) or time_column_name in col]
        
        # Tạo sparkline cho mỗi dòng
        for idx, row in pivot_reset.iterrows():
                
            # Lấy tên hàng
            if isinstance(pivot.index, pd.MultiIndex):
                row_key = tuple(row[list(pivot.index.names)])
            else:
                row_key = row[pivot.index.name]
                
            # Lấy giá trị cho sparkline (extract từ HTML nếu cần)
            values = []
            for col in value_columns:
                try:
                    if col in pivot.columns:
                        val = pivot.loc[row_key, col]
                        # Nếu là chuỗi HTML, lấy số đầu tiên
                        if isinstance(val, str):
                            import re
                            numbers = re.findall(r'[\d.]+', val.replace('.', ''))
                            if numbers:
                                values.append(int(numbers[0].replace('.', '')))
                            else:
                                values.append(0)
                        else:
                            values.append(val)
                except:
                    values.append(0)
            
            # Tạo sparkline figure
            fig = go.Figure()
            
            # Thêm line chart
            fig.add_trace(go.Scatter(
                y=values,
                mode='lines+markers',
                line=dict(width=2, color='royalblue'),
                marker=dict(size=4),
                showlegend=False
            ))
            
            # Highlight điểm cao nhất
            if values:
                max_idx = np.argmax(values)
                fig.add_trace(go.Scatter(
                    x=[max_idx],
                    y=[values[max_idx]],
                    mode='markers',
                    marker=dict(size=6, color='green'),
                    showlegend=False
                ))
                
                # Highlight điểm thấp nhất
                min_idx = np.argmin(values)
                fig.add_trace(go.Scatter(
                    x=[min_idx],
                    y=[values[min_idx]],
                    mode='markers',
                    marker=dict(size=6, color='red'),
                    showlegend=False
                ))
            
            # Định dạng figure
            fig.update_layout(
                margin=dict(l=0, r=0, t=0, b=0),
                height=30,
                width=150,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(
                    showticklabels=False,
                    showgrid=False,
                    zeroline=False
                ),
                yaxis=dict(
                    showticklabels=False,
                    showgrid=False,
                    zeroline=False
                ),
                hovermode=False
            )
            
            # Lưu figure
            sparklines_data[row_key] = fig
            
        return sparklines_data
    
    def create_individual_trend_chart(self, data, content_item, time_col, chart_type="Đường", normalize=False):
        """Tạo biểu đồ xu hướng riêng cho một nội dung cụ thể"""
        try:
            # Lọc dữ liệu cho nội dung được chọn
            content_data = data[data['Nội dung'] == content_item]
            
            if content_data.empty:
                return None
                
            # Tạo pivot table cho nội dung này
            pivot_data = pd.pivot_table(
                content_data,
                index='Nội dung',
                columns=time_col,
                values='Số liệu',
                aggfunc='sum',
                fill_value=0
            )
            
            # Lấy giá trị cho biểu đồ
            time_values = list(pivot_data.columns)
            data_values = pivot_data.iloc[0].values
            
            # Chuẩn hóa dữ liệu nếu cần
            if normalize and max(data_values) > 0:
                data_values = data_values / max(data_values) * 100
            
            # BỎ HIỂN THỊ SỐ ƯU TIÊN
            title = f"{content_item}"
            
            # Tạo biểu đồ tương ứng với loại đã chọn
            if chart_type == "Đường":
                fig = px.line(
                    x=time_values,
                    y=data_values,
                    markers=True,
                    title=title
                )
                
                # Thêm điểm cao nhất và thấp nhất
                if len(data_values) > 0:
                    max_idx = np.argmax(data_values)
                    fig.add_trace(go.Scatter(
                        x=[time_values[max_idx]],
                        y=[data_values[max_idx]],
                        mode='markers',
                        marker=dict(size=10, color='green', symbol='circle'),
                        name='Cao nhất',
                        showlegend=False
                    ))
                    
                    min_idx = np.argmin(data_values)
                    fig.add_trace(go.Scatter(
                        x=[time_values[min_idx]],
                        y=[data_values[min_idx]],
                        mode='markers',
                        marker=dict(size=10, color='red', symbol='circle'),
                        name='Thấp nhất',
                        showlegend=False
                    ))
                
            elif chart_type == "Cột":
                fig = px.bar(
                    x=time_values,
                    y=data_values,
                    title=title
                )
                
                # Highlight cột cao nhất và thấp nhất
                if len(data_values) > 0:
                    max_idx = np.argmax(data_values)
                    min_idx = np.argmin(data_values)
                    
                    bar_colors = ['royalblue'] * len(data_values)
                    bar_colors[max_idx] = 'green'
                    bar_colors[min_idx] = 'red'
                    
                    fig.update_traces(marker_color=bar_colors)
                
            else:  # Vùng
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=time_values,
                    y=data_values,
                    mode='lines',
                    fill='tozeroy',
                    line=dict(color='royalblue'),
                    name=content_item
                ))
                
                # Thêm điểm cao nhất và thấp nhất
                if len(data_values) > 0:
                    max_idx = np.argmax(data_values)
                    fig.add_trace(go.Scatter(
                        x=[time_values[max_idx]],
                        y=[data_values[max_idx]],
                        mode='markers',
                        marker=dict(size=10, color='green', symbol='circle'),
                        name='Cao nhất',
                        showlegend=False
                    ))
                    
                    min_idx = np.argmin(data_values)
                    fig.add_trace(go.Scatter(
                        x=[time_values[min_idx]],
                        y=[data_values[min_idx]],
                        mode='markers',
                        marker=dict(size=10, color='red', symbol='circle'),
                        name='Thấp nhất',
                        showlegend=False
                    ))
                
                fig.update_layout(title=title)
            
            # Cập nhật layout
            y_title = "% (so với giá trị cao nhất)" if normalize else "Giá trị"
            time_col_display = {"Tuần": "Tuần", "Tháng": "Tháng", "Quý": "Quý", "Năm": "Năm"}.get(time_col, time_col)
            
            fig.update_layout(
                xaxis_title=time_col_display,
                yaxis_title=y_title,
                height=300,
                margin=dict(l=10, r=10, t=40, b=40),
                hovermode="x",
                plot_bgcolor='rgba(240,240,240,0.1)'
            )
            
            # Thêm đường xu hướng nếu có đủ dữ liệu
            if len(data_values) > 2:
                x_values = list(range(len(data_values)))
                coeffs = np.polyfit(x_values, data_values, 1)
                trend_line = np.poly1d(coeffs)(x_values)
                
                # Xác định màu đường xu hướng
                trend_color = 'green' if coeffs[0] > 0 else 'red'
                
                if chart_type in ["Đường", "Vùng"]:
                    fig.add_trace(go.Scatter(
                        x=time_values,
                        y=trend_line,
                        mode='lines',
                        line=dict(color=trend_color, dash='dash', width=2),
                        name='Xu hướng',
                        showlegend=False
                    ))
            
            return fig
            
        except Exception as e:
            st.error(f"Lỗi khi tạo biểu đồ cho {content_item}: {str(e)}")
            return None

def main():
    # HEADER: logo + title on one line (flexbox)
    try:
        # Encode logo to base64 for inline <img>
        script_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(script_dir, "assets", "logo.png")
        logo_base64 = ""
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as f:
                logo_base64 = base64.b64encode(f.read()).decode()
    except Exception:
        logo_base64 = ""

    # Hiển thị logo trong sidebar
    if logo_base64:
        st.sidebar.image(f"data:image/png;base64,{logo_base64}", width=100)

    header_html = f"""
    <div style='
        display:flex;
        align-items:center;
        justify-content:center;
        padding:10px 0;
        background:#ffffff;
        border-radius:15px;
        margin-bottom:0;
    '>
        <h1 style='
            color:#1f77b4;
            margin:0;
            font-size:2.7rem;
            font-weight:bold;
            font-family:"Segoe UI", Arial, sans-serif;
            text-shadow:2px 2px 4px rgba(0,0,0,0.1);
            letter-spacing:1px; text-align:center;'>
            Dashboard hoạt động Phòng Hành chính
        </h1>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)
    
    # Footer gọn gàng – gom toàn bộ thông tin dự án vào một expander cuối trang
    st.markdown("---")
    with st.expander("ℹ️ Thông tin về Dashboard", expanded=False):
        # Giới thiệu và tính năng
        st.markdown("""
        **🏥 Dashboard chuyên biệt cho Phòng Hành Chính Bệnh viện**

        **✨ Tính năng nổi bật:**
        - 📋 13 danh mục và 70+ nội dung theo thứ tự ưu tiên cố định  
        - 📈 Hiển thị biến động tuần (%) ngay trong giá trị: `1.234.567 (↑15%)`  
        - 🔒 Cột **Nội dung** và **Tổng** đóng băng khi cuộn  
        - 📊 Sparkline xu hướng cho từng danh mục  
        - 💾 Xuất báo cáo Excel đa sheet và CSV  
        - ☁️ Tự động sync với GitHub storage  
        """)
        # Thông tin bản quyền + GitHub
        st.markdown("""
        <div style='text-align: center; color: #666; padding: 15px; background-color:rgba(255, 255, 255, 0.08);
                    border-radius: 10px; margin-top: 20px;'>
            <p style='margin: 0; font-size: 14px;'>
                🏥 <strong>Phòng Hành Chính - Bệnh viện Đại học Y Dược TPHCM - University Medical Center HCMC (UMC)</strong>
                &nbsp;|&nbsp;
                🌐 <a href="https://github.com/corner-25/dashboard-phong-hanh-chinh" target="_blank"
                      style="text-decoration: none; color: #1f77b4;">GitHub Project</a>
            </p>
            <p style='margin: 5px 0 0 0; font-size: 12px; color: #888;'>
                © 2025 Dashboard Phòng Hành Chính — Phát triển bởi <strong>Dương Hữu Quang</strong>
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # Khởi tạo dashboard và DataManager
    dashboard = PivotTableDashboard()
    
    # Initialize data manager để load dữ liệu từ GitHub
    if 'data_manager' not in st.session_state:
        st.session_state.data_manager = DataManager()
    
    manager = st.session_state.data_manager
    
    # Kiểm tra kết nối GitHub
    connected, status_msg = manager.check_github_connection()
    
    file_loaded = False
    
    if connected:
        st.sidebar.success("☁️ Kết nối GitHub thành công")
        
        # Thử load dữ liệu từ GitHub trước
        try:
            github_data, metadata = manager.load_current_data()
            
            if github_data is not None and metadata:
                # Có dữ liệu từ GitHub
                st.sidebar.info(f"""
                📊 **Dữ liệu từ GitHub:**
                - 📄 {metadata.get('filename', 'Unknown')}
                - 📅 Tuần {metadata.get('week_number', '?')}/{metadata.get('year', '?')}
                """)
                
                # Load vào dashboard - SỬA LẠI DÒNG NÀY
                if dashboard.load_data_from_dataframe(github_data):
                    file_loaded = True
                else:
                    st.sidebar.warning("⚠️ Lỗi xử lý dữ liệu GitHub")
                    file_loaded = False
            else:
                st.sidebar.warning("📭 Chưa có dữ liệu trên GitHub")
                file_loaded = False
                
        except Exception as github_error:
            st.sidebar.error(f"❌ Lỗi load GitHub: {str(github_error)}")
            file_loaded = False
    else:
        st.sidebar.warning("⚠️ Không kết nối được GitHub")
        file_loaded = False
    
    # Upload section trong sidebar
    st.sidebar.header("📤 Upload dữ liệu mới")
    
    # Chọn cách nhập dữ liệu
    data_source = st.sidebar.radio(
        "Chọn nguồn dữ liệu",
        ["Upload file", "Nhập đường dẫn file"]
    )
    
    if data_source == "Upload file":
        uploaded_file = st.sidebar.file_uploader("Chọn file Excel", type=['xlsx', 'xls'])
        if uploaded_file is not None:
            # Nếu có GitHub connection, cho phép upload lên GitHub
            if connected:
                col1, col2 = st.sidebar.columns(2)
                with col1:
                    if st.button("📊 Xem trước", use_container_width=True):
                        if dashboard.load_data(uploaded_file):
                            st.sidebar.success("✅ Đã tải dữ liệu thành công!")
                            file_loaded = True
                
                with col2:
                    if st.button("☁️ Upload GitHub", use_container_width=True):
                        # Đọc file để upload
                        try:
                            data = pd.read_excel(uploaded_file)
                            success = manager.upload_new_file(data, uploaded_file.name)
                            if success:
                                st.balloons()
                                time.sleep(1)
                                st.rerun()
                        except Exception as e:
                            st.sidebar.error(f"❌ Lỗi upload: {str(e)}")
            else:
                # Không có GitHub, chỉ xem local
                if dashboard.load_data(uploaded_file):
                    st.sidebar.success("✅ Đã tải dữ liệu thành công!")
                    file_loaded = True
        
        # Tự động load lại nếu đã có đường dẫn trong session
        if 'file_path' in st.session_state:
            if os.path.exists(st.session_state['file_path']):
                dashboard.load_data(st.session_state['file_path'])
                file_loaded = True
    
    # Phần còn lại của dashboard (chỉ hiển thị khi có dữ liệu)
    if file_loaded and dashboard.data is not None:
        # Tạo các cài đặt và bộ lọc
        report_type, rows, cols, values, agg_func, show_ratio_inline = dashboard.create_pivot_settings()
        from_year, from_month, from_week, to_year, to_month, to_week, categories = dashboard.create_filters()
        
        # Áp dụng bộ lọc
        filtered_data = dashboard.filter_data(from_year, from_month, from_week, to_year, to_month, to_week, categories)
        
        # THÊM: Tự động aggregate theo loại báo cáo
        aggregated_data = dashboard.aggregate_data_by_report_type(filtered_data, report_type)
        
        # Nút làm mới dữ liệu
        if st.sidebar.button("🔄 Làm mới dữ liệu", use_container_width=True):
            if connected:
                # Reload từ GitHub
                try:
                    github_data, metadata = manager.load_current_data()
                    if github_data is not None:
                        dashboard.load_data_from_dataframe(github_data)
                        st.rerun()
                except:
                    pass
            elif 'file_path' in st.session_state:
                dashboard.load_data(st.session_state['file_path'])
                st.rerun()
        
        # Tabs cho các chế độ xem
        tab1, tab2, tab3 = st.tabs(["📋 Pivot Table", "📊 Xu hướng theo thời gian", "💾 Xuất báo cáo"])
        
        with tab1:
            # Tạo pivot table với biến động - SỬ DỤNG aggregated_data
            pivot = dashboard.create_hierarchical_pivot_table_with_ratio(
                aggregated_data, rows, cols, values, agg_func, show_ratio_inline
            )
            
            if pivot is not None:
                # Hiển thị pivot table cải tiến
                dashboard.display_hierarchical_pivot_improved(pivot, aggregated_data)
                
                # Tùy chọn xuất
                col1, col2 = st.columns(2)
                with col1:
                    # Tạo CSV từ dữ liệu gốc (không có HTML)
                    if show_ratio_inline and report_type == "Theo Tuần":
                        st.info("💡 Xuất CSV sẽ chứa dữ liệu gốc (không có biến động HTML)")
                    
                    # Tạo pivot đơn giản cho CSV
                    simple_pivot = pd.pivot_table(
                        aggregated_data,
                        index=rows if rows else None,
                        columns=cols if cols else None,
                        values=values,
                        aggfunc=agg_func,
                        fill_value=0,
                        margins=False  # BỎ TỔNG CHUNG
                    )
                    
                    csv = simple_pivot.to_csv(encoding='utf-8-sig')
                    st.download_button(
                        "📥 Tải CSV",
                        csv,
                        f"pivot_table_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        "text/csv"
                    )
        
        with tab2:
            st.header("Xu hướng theo thời gian (theo thứ tự ưu tiên)")
            
            # Xác định trường thời gian dựa vào kiểu báo cáo
            time_col = {
                "Theo Tuần": "Tuần", 
                "Theo Tháng": "Tháng", 
                "Theo Quý": "Quý", 
                "Theo Năm": "Năm"
            }.get(report_type, "Tháng")
            
            # Hiển thị tùy chọn cho biểu đồ
            col1, col2, col3 = st.columns(3)
            
            with col1:
                chart_type = st.selectbox(
                    "Loại biểu đồ",
                    ["Đường", "Cột", "Vùng"]
                )
            
            with col2:
                normalize = st.checkbox("Chuẩn hóa (so sánh %)", value=False)
                
            with col3:
                num_cols = st.select_slider(
                    "Số cột hiển thị",
                    options=[1, 2, 3],
                    value=2
                )
            
            # Lọc dữ liệu cho các Nội dung (hiển thị theo thứ tự ưu tiên) - SỬ DỤNG aggregated_data
            unique_contents = aggregated_data['Nội dung'].unique()
            sorted_contents = sorted(unique_contents, key=lambda x: dashboard.content_priority.get(x, 999))
            
            content_filter = st.multiselect(
                "Chọn Nội dung cần hiển thị (theo thứ tự ưu tiên)",
                sorted_contents,
                default=sorted_contents[:10]  # Mặc định hiển thị 10 nội dung đầu tiên
            )
            
            filtered_for_charts = aggregated_data[aggregated_data['Nội dung'].isin(content_filter)]
            
            if filtered_for_charts.empty:
                st.warning("Không có dữ liệu phù hợp với bộ lọc đã chọn!")
            else:
                # Hiển thị biểu đồ cho từng nội dung riêng biệt
                st.subheader(f"Biểu đồ xu hướng theo {time_col} cho từng Nội dung")
                
                # Sắp xếp dữ liệu theo thứ tự ưu tiên
                sorted_data = filtered_for_charts.copy()
                sorted_data = sorted_data.sort_values(['Danh_mục_thứ_tự', 'Nội_dung_thứ_tự'])
                
                # Tạo container cho các danh mục
                categories = sorted_data['Danh mục'].unique()
                sorted_categories = sorted(categories, key=lambda x: dashboard.category_priority.get(x, 999))
                
                for category in sorted_categories:
                    # Hiển thị Danh mục với expander (BỎ HIỂN THỊ SỐ ƯU TIÊN)
                    with st.expander(f"📁 {category}", expanded=True):
                        # Lọc dữ liệu cho danh mục này
                        category_data = sorted_data[sorted_data['Danh mục'] == category]
                        
                        # Lấy danh sách nội dung trong danh mục (đã sắp xếp)
                        category_contents = category_data['Nội dung'].unique()
                        sorted_category_contents = sorted(category_contents, 
                                                        key=lambda x: dashboard.content_priority.get(x, 999))
                        
                        # Tạo grid hiển thị biểu đồ
                        cols_container = st.columns(num_cols)
                        
                        # Duyệt qua từng nội dung và tạo biểu đồ riêng
                        for i, content_item in enumerate(sorted_category_contents):
                            # Tạo biểu đồ cho nội dung này
                            fig = dashboard.create_individual_trend_chart(
                                category_data, content_item, time_col, chart_type, normalize
                            )
                            
                            if fig is not None:
                                # Hiển thị trong cột tương ứng
                                col_idx = i % num_cols
                                with cols_container[col_idx]:
                                    st.plotly_chart(fig, use_container_width=True)
                
                # Hiển thị bảng dữ liệu
                with st.expander("Xem dữ liệu chi tiết (theo thứ tự ưu tiên)"):
                    # Tạo pivot cho xem dữ liệu chi tiết - SỬ DỤNG aggregated_data
                    detail_pivot = pd.pivot_table(
                        filtered_for_charts,
                        index=['Danh mục', 'Nội dung'],
                        columns=time_col,
                        values='Số liệu',
                        aggfunc='sum',
                        fill_value=0
                    )
                    
                    # Sắp xếp theo thứ tự ưu tiên
                    detail_pivot_sorted = detail_pivot.copy()
                    detail_pivot_sorted['Danh_mục_thứ_tự'] = detail_pivot_sorted.index.get_level_values('Danh mục').map(dashboard.category_priority).fillna(999)
                    detail_pivot_sorted['Nội_dung_thứ_tự'] = detail_pivot_sorted.index.get_level_values('Nội dung').map(dashboard.content_priority).fillna(999)
                    detail_pivot_sorted = detail_pivot_sorted.sort_values(['Danh_mục_thứ_tự', 'Nội_dung_thứ_tự'])
                    detail_pivot_sorted = detail_pivot_sorted.drop(columns=['Danh_mục_thứ_tự', 'Nội_dung_thứ_tự'])
                    
                    # Hiển thị với HTML table để đảm bảo hiển thị đầy đủ số
                    html_table = "<div class='full-width-table'>"
                    html_table += "<table style='width:100%; border-collapse: collapse; font-size: 11px;'>"
                    html_table += "<tr style='background-color: #f0f2f6;'>"
                    html_table += "<th style='border: 1px solid #ddd; padding: 6px;'>Danh mục</th>"
                    html_table += "<th style='border: 1px solid #ddd; padding: 6px;'>Nội dung</th>"
                    for col in detail_pivot_sorted.columns:
                        html_table += f"<th style='border: 1px solid #ddd; padding: 6px; text-align: center;'>{col}</th>"
                    html_table += "</tr>"
                    
                    for idx in detail_pivot_sorted.index:
                        html_table += "<tr>"
                        html_table += f"<td style='border: 1px solid #ddd; padding: 6px;'>{idx[0]}</td>"
                        html_table += f"<td style='border: 1px solid #ddd; padding: 6px;'>{idx[1]}</td>"
                        for col in detail_pivot_sorted.columns:
                            value = detail_pivot_sorted.loc[idx, col]
                            formatted_value = f"{value:,.0f}".replace(',', '.')
                            html_table += f"<td style='border: 1px solid #ddd; padding: 6px; text-align: right;' class='number-cell'>{formatted_value}</td>"
                        html_table += "</tr>"
                    
                    html_table += "</table></div>"
                    st.markdown(html_table, unsafe_allow_html=True)
        
        with tab3:
            st.header("Xuất báo cáo")
            
            # Tạo báo cáo tổng hợp
            report_format = st.selectbox(
                "Chọn định dạng",
                ["Excel đa sheet với thứ tự ưu tiên", "Excel đơn giản", "CSV"]
            )
            
            if st.button("Tạo báo cáo", use_container_width=True):
                if report_format == "Excel đa sheet với thứ tự ưu tiên":
                    # Tạo file Excel với nhiều sheet
                    output_file = f'bao_cao_phong_hanh_chinh_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
                    with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
                        # Sheet 1: Dữ liệu gốc (đã sắp xếp) - SỬ DỤNG aggregated_data
                        aggregated_data_export = aggregated_data.drop(columns=['Danh_mục_thứ_tự', 'Nội_dung_thứ_tự'], errors='ignore')
                        aggregated_data_export.to_excel(writer, sheet_name='Dữ liệu đã aggregate', index=False)
                        
                        # Sheet 2: Pivot table (dữ liệu số, không có HTML) - SỬ DỤNG aggregated_data
                        simple_pivot = pd.pivot_table(
                            aggregated_data,
                            index=rows if rows else None,
                            columns=cols if cols else None,
                            values=values,
                            aggfunc=agg_func,
                            fill_value=0,
                            margins=False  # BỎ TỔNG CHUNG
                        )
                        simple_pivot.to_excel(writer, sheet_name='Pivot Table')
                        
                        # Sheet 3: Tổng hợp theo danh mục (theo thứ tự ưu tiên) - SỬ DỤNG aggregated_data
                        category_summary = aggregated_data.groupby('Danh mục')['Số liệu'].agg(['sum', 'mean', 'count'])
                        category_summary['Thứ_tự'] = category_summary.index.map(dashboard.category_priority).fillna(999)
                        category_summary = category_summary.sort_values('Thứ_tự').drop(columns=['Thứ_tự'])
                        category_summary.to_excel(writer, sheet_name='Theo danh mục')
                        
                        # Sheet 4: Tổng hợp theo thời gian - SỬ DỤNG aggregated_data
                        time_summary = aggregated_data.pivot_table(
                            index=time_col,
                            columns='Danh mục',
                            values='Số liệu',
                            aggfunc='sum',
                            fill_value=0
                        )
                        time_summary.to_excel(writer, sheet_name='Theo thời gian')
                        
                        # Sheet 5: Tổng hợp theo nội dung (theo thứ tự ưu tiên) - SỬ DỤNG aggregated_data
                        content_summary = aggregated_data.pivot_table(
                            index=['Danh mục', 'Nội dung'],
                            values='Số liệu',
                            aggfunc=['sum', 'mean', 'count'],
                            fill_value=0
                        )
                        content_summary.to_excel(writer, sheet_name='Theo nội dung')
                        
                        # Sheet 6: Tỷ lệ thay đổi - CHỈ CHO BÁO CÁO THEO TUẦN
                        if report_type == "Theo Tuần":
                            ratio_data = aggregated_data[aggregated_data['Tỷ_lệ_tuần_trước'] != 0]
                            if not ratio_data.empty:
                                ratio_summary = ratio_data.pivot_table(
                                    index=['Danh mục', 'Nội dung'],
                                    columns='Tuần',
                                    values=['Tỷ_lệ_tuần_trước', 'Thay_đổi_tuần_trước'],
                                    aggfunc='mean',
                                    fill_value=None
                                )
                                ratio_summary.to_excel(writer, sheet_name='Tỷ lệ thay đổi')
                        
                        # Sheet 7: Cấu hình thứ tự ưu tiên cố định
                        priority_df = pd.DataFrame([
                            {'Loại': 'Danh mục', 'Tên': k, 'Thứ tự': v} 
                            for k, v in dashboard.category_priority.items()
                        ] + [
                            {'Loại': 'Nội dung', 'Tên': k, 'Thứ tự': v} 
                            for k, v in dashboard.content_priority.items()
                        ])
                
                        priority_df = priority_df.sort_values(['Loại', 'Thứ tự'])
                        priority_df.to_excel(writer, sheet_name='Thứ tự ưu tiên', index=False)
                    
                    with open(output_file, 'rb') as f:
                        st.download_button(
                            "📥 Tải báo cáo Excel với thứ tự ưu tiên",
                            f.read(),
                            output_file,
                            "application/vnd.ms-excel"
                        )
                    
                    st.success("✅ Đã tạo báo cáo với thứ tự ưu tiên thành công!")
                
                elif report_format == "Excel đơn giản":
                    # Tạo file Excel đơn giản - SỬ DỤNG aggregated_data
                    output_file = f'bao_cao_don_gian_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
                    with pd.ExcelWriter(output_file) as writer:
                        aggregated_data_export = aggregated_data.drop(columns=['Danh_mục_thứ_tự', 'Nội_dung_thứ_tự'], errors='ignore')
                        aggregated_data_export.to_excel(writer, index=False)
                    
                    with open(output_file, 'rb') as f:
                        st.download_button(
                            "📥 Tải Excel đơn giản",
                            f.read(),
                            output_file,
                            "application/vnd.ms-excel"
                        )
                    
                    st.success("✅ Đã tạo báo cáo đơn giản thành công!")
                
                else:  # CSV
                    aggregated_data_export = aggregated_data.drop(columns=['Danh_mục_thứ_tự', 'Nội_dung_thứ_tự'], errors='ignore')
                    csv = aggregated_data_export.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        "📥 Tải CSV",
                        csv,
                        f"bao_cao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        "text/csv"
                    )
                    
                    st.success("✅ Đã tạo file CSV thành công!")
    
    else:
        st.info("👆 Vui lòng tải lên file Excel hoặc nhập đường dẫn file để bắt đầu")
        
        # Hướng dẫn
        with st.expander("📖 Hướng dẫn sử dụng Dashboard Phòng Hành Chính"):
            st.markdown("""
            ### 🎯 Dashboard chuyên biệt cho Phòng Hành Chính
            
            #### ✨ **Tính năng đặc biệt:**
            
            **1. Thứ tự ưu tiên cố định:**
            - 🥇 Tự động sắp xếp theo thứ tự quan trọng công việc
            - 📋 13 danh mục chính từ "Văn bản đến" đến "Bãi giữ xe"
            - 📄 70 nội dung được sắp xếp theo thứ tự ưu tiên
            
            **2. Hiển thị số đầy đủ:**
            - 💰 Hiển thị đầy đủ số lớn (ví dụ: 1.234.567)
            - 📊 Bảng HTML tùy chỉnh không bị cắt số
            - 🔍 Scroll ngang để xem đầy đủ dữ liệu
            
            **3. Biến động inline:**
            - 📈 Giá trị và biến động trong cùng một ô
            - 🟢 Tăng: "100.000 (↑15%)" 
            - 🔴 Giảm: "85.000 (↓15%)"
            - ⚪ Không đổi: "100.000 (→0%)"
            
            **4. Sync với GitHub:**
            - ☁️ Tự động tải dữ liệu từ GitHub storage
            - 🔄 Upload và sync dữ liệu mới
            - 📱 Truy cập từ mọi thiết bị
            
            #### 📂 **Danh mục theo thứ tự ưu tiên:**
            1. **Văn bản đến** - Quản lý văn bản đến
            2. **Văn bản phát hành** - Quản lý văn bản đi
            3. **Chăm sóc khách VIP** - Dịch vụ VIP
            4. **Lễ tân** - Hỗ trợ sự kiện
            5. **Tiếp khách trong nước** - Đón tiếp khách
            6. **Sự kiện** - Tổ chức sự kiện
            7. **Đón tiếp khách VIP** - Dịch vụ đặc biệt
            8. **Tổ chức cuộc họp trực tuyến** - Họp online
            9. **Trang điều hành tác nghiệp** - ĐHTN
            10. **Tổ xe** - Quản lý vận tải
            11. **Tổng đài** - Dịch vụ điện thoại
            12. **Hệ thống thư ký Bệnh viện** - Quản lý thư ký
            13. **Bãi giữ xe** - Dịch vụ đậu xe
            
            #### 🚀 **Cách sử dụng:**
            1. **Tự động**: Dữ liệu tự động sync từ GitHub
            2. **Thủ công**: Upload file Excel hoặc nhập đường dẫn nếu cần
            3. **Chọn báo cáo**: Theo Tuần/Tháng/Quý/Năm
            4. **Lọc dữ liệu**: Chọn thời gian và danh mục
            5. **Xem kết quả**: Pivot table với biến động inline
            6. **Xuất báo cáo**: Excel/CSV với thứ tự ưu tiên
            
            #### 💡 **Lợi ích:**
            - ⚡ **Tự động 100%**: Không cần sắp xếp thủ công
            - 🎯 **Ưu tiên rõ ràng**: Theo tầm quan trọng công việc  
            - 📊 **Hiển thị đầy đủ**: Không bị mất số liệu
            - 📈 **Biến động trực quan**: Nhìn thấy ngay xu hướng
            - 💾 **Xuất chuyên nghiệp**: Báo cáo đầy đủ thông tin
            - ☁️ **Sync tự động**: Kết nối với GitHub storage
            
            #### ⚠️ **Lưu ý:**
            - Dữ liệu cần có cột: Tuần, Tháng, Danh mục, Nội dung, Số liệu
            - Thứ tự ưu tiên đã được cố định, không cần điều chỉnh
            - Biến động chỉ hiển thị từ tuần thứ 2 trở đi
            - Biến động được tính so với tuần liền trước
            - Dữ liệu sẽ tự động sync từ GitHub nếu có kết nối
            """)
            
        # Hiển thị hướng dẫn GitHub nếu chưa kết nối
        if not connected:
            with st.expander("🔧 Cấu hình GitHub để sync tự động"):
                st.markdown("""
                **Để sử dụng tính năng sync tự động với GitHub:**
                
                1. **Tạo GitHub Personal Access Token**:
                   - Vào GitHub → Settings → Developer settings → Personal access tokens
                   - Tạo token mới với quyền `repo` và `contents:write`
                
                2. **Thêm vào Streamlit Secrets**:
                   ```
                   github_token = "ghp_xxxxxxxxxxxx"
                   github_owner = "your-username"  
                   github_repo = "your-repo-name"
                   ```
                
                3. **Sau khi cấu hình**:
                   - Dashboard sẽ tự động load dữ liệu từ GitHub
                   - Upload file mới trực tiếp lên GitHub
                   - Sync dữ liệu giữa các thiết bị
                """)

if __name__ == "__main__":
    main()
