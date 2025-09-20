#!/usr/bin/env python3
"""
Manual Fleet Data Sync Engine - Fixed Version
Sync dữ liệu từ Google Sheets lên GitHub
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime
import logging
import os
from dotenv import load_dotenv
import base64
from typing import Dict, List, Optional
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fleet_sync.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ManualFleetSync:
    """
    Manual Fleet Data Sync Engine
    Fixed version - no ensure_ascii issues
    """
    
    def __init__(self):
        """Khởi tạo sync engine"""
        self.sheets_service = None
        
        # Config cố định
        self.config = {
            "google_sheets": {
                "credentials_file": "ivory-haven-463209-b8-09944271707f.json",
                "spreadsheet_id": "1sYzuvnv-lzQcv-IZjT672LTpfUrqdWCesx4pW8mIuqM"
            },
            "github": {
                "username": "corner-25",
                "repository": "vehicle-storage",
                "token": self.get_github_token(),
                "branch": "main"
            }
        }
        
        # Vehicle classifications
        self.admin_vehicles = ["51B-330.67", "50A-012.59", "50A-007.20", "51A-1212", "50A-004.55"]
        self.ambulance_vehicles = ["50A-007.39", "50M-004.37", "50A-009.44", "50A-010.67", 
                                 "50M-002.19", "51B-509.51", "50A-019.90", "50A-018.35"]
        
        # Driver mapping
        self.driver_names = {
            "ngochai191974@gmail.com": "Ngọc Hải",
            "phongthai230177@gmail.com": "Thái Phong", 
            "dunglamlong@gmail.com": "Long Dũng",
            "trananhtuan461970@gmail.com": "Anh Tuấn",
            "thanhdungvo29@gmail.com": "Thanh Dũng",
            "duck79884@gmail.com": "Đức",
            "ngohoangxuyen@gmail.com": "Hoàng Xuyên",
            "hodinhxuyen@gmail.com": "Đình Xuyên",
            "nvhung1981970@gmail.com": "Văn Hùng",
            "thanggptk21@gmail.com": "Văn Thảo",
            "nguyenhung091281@gmail.com": "Nguyễn Hùng",
            "nguyemthanhtrung12345@gmail.com": "Thành Trung",
            "nguyenhungumc@gmail.com": "Nguyễn Hùng",
            "dvo567947@gmail.com": "Thanh Dũng",
            "traannhtuan461970@gmail.com": "Anh Tuấn",
            "hoanganhsie1983@gmail.com": "Hoàng Anh",
            "hoanganhsieumc@gmail.com": "Hoàng Anh",
            "thaonguyenvan860@gmail.com": "Văn Thảo",
            "ledangthaiphong@gmail.com": "Thái Phong",
            "dohungcuong1970@gmail.com": "Hùng Cường",
            "trananhtuan74797@gmail.com": "Anh Tuấn"
        }
        
        # Stats
        self.sync_stats = {
            'total_syncs': 0,
            'successful_syncs': 0,
            'last_sync': None,
            'last_error': None
        }
    
    def get_github_token(self) -> str:
        # Priority 1: Environment variable
        token = os.getenv('GITHUB_TOKEN')
        if token and len(token) > 10:
            return token
        
        # Priority 2: File (backward compatibility)
        token_file = "github_token.txt"
        if os.path.exists(token_file):
            try:
                with open(token_file, 'r') as f:
                    token = f.read().strip()
                if token and token != "YOUR_TOKEN_HERE":
                    return token
            except:
                pass
        
        # Priority 3: User input (chỉ khi chạy standalone)
        if __name__ == "__main__":
            print("🔑 GITHUB TOKEN SETUP")
            print("=" * 40)
            print("Nhập GitHub token:")
            token = input("Token: ").strip()
            if token:
                return token
        
        return "YOUR_TOKEN_HERE"

    
    def get_google_credentials(self):
        """Get Google credentials from Streamlit secrets or file"""
        try:
            import streamlit as st
            if hasattr(st, 'secrets') and 'google_credentials' in st.secrets:
                import tempfile
                import json
                
                # Convert secrets to dict
                creds_dict = {
                    "type": st.secrets.google_credentials.type,
                    "project_id": st.secrets.google_credentials.project_id,
                    "private_key_id": st.secrets.google_credentials.private_key_id,
                    "private_key": st.secrets.google_credentials.private_key,
                    "client_email": st.secrets.google_credentials.client_email,
                    "client_id": st.secrets.google_credentials.client_id,
                    "auth_uri": st.secrets.google_credentials.auth_uri,
                    "token_uri": st.secrets.google_credentials.token_uri,
                    "auth_provider_x509_cert_url": st.secrets.google_credentials.auth_provider_x509_cert_url,
                    "client_x509_cert_url": st.secrets.google_credentials.client_x509_cert_url,
                    "universe_domain": st.secrets.google_credentials.universe_domain
                }
                
                # Create temporary file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                    json.dump(creds_dict, f)
                    return f.name
        except Exception as e:
            logger.error(f"Error getting Streamlit secrets: {e}")
        
        # Fallback to local file
        credentials_file = self.config['google_sheets']['credentials_file']
        if os.path.exists(credentials_file):
            return credentials_file
        
        return None
    
    def authenticate_google_sheets(self) -> bool:
        """Xác thực Google Sheets"""
        try:
            credentials_file = self.get_google_credentials()  # Now calling self.get_google_credentials()
            
            if not credentials_file:
                logger.error("❌ Không tìm thấy Google credentials")
                return False
            
            # Read credentials
            with open(credentials_file, 'r', encoding='utf-8') as f:
                creds_data = json.load(f)
            
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets.readonly',
                'https://www.googleapis.com/auth/drive.readonly'
            ]
            
            credentials = service_account.Credentials.from_service_account_info(
                creds_data, scopes=scopes
            )
            
            self.sheets_service = build('sheets', 'v4', credentials=credentials)
            
            # Test connection
            spreadsheet_id = self.config['google_sheets']['spreadsheet_id']
            test_result = self.sheets_service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()
            
            logger.info("✅ Google Sheets connected successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Google Sheets error: {e}")
            return False
            
    def read_all_sheets(self) -> Optional[pd.DataFrame]:
        """Đọc tất cả sheets và merge"""
        try:
            spreadsheet_id = self.config['google_sheets']['spreadsheet_id']
            
            # Get sheet info
            sheet_metadata = self.sheets_service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()
            
            all_data = []
            
            for sheet in sheet_metadata.get('sheets', []):
                sheet_name = sheet['properties']['title']
                
                try:
                    # Read sheet data
                    result = self.sheets_service.spreadsheets().values().get(
                        spreadsheetId=spreadsheet_id,
                        range=f"'{sheet_name}'"
                    ).execute()
                    
                    values = result.get('values', [])
                    
                    if len(values) < 2:
                        logger.warning(f"⚠️ Sheet {sheet_name} no data")
                        continue
                    
                    # Convert to DataFrame
                    headers = values[0]
                    data_rows = values[1:]
                    
                    # Clean data
                    max_cols = len(headers)
                    cleaned_data = []
                    
                    for row in data_rows:
                        while len(row) < max_cols:
                            row.append(None)
                        if len(row) > max_cols:
                            row = row[:max_cols]
                        cleaned_data.append(row)
                    
                    df = pd.DataFrame(cleaned_data, columns=headers)
                    
                    # Add metadata
                    df['Mã xe'] = sheet_name
                    df['Tên tài xế'] = df['Email Address'].map(self.driver_names).fillna(df['Email Address'])
                    
                    if sheet_name in self.admin_vehicles:
                        df['Loại xe'] = 'Hành chính'
                        # Set missing columns to null
                        df['Chi tiết chuyến xe'] = None
                        df['Doanh thu'] = None
                    else:
                        df['Loại xe'] = 'Cứu thương'
                    
                    all_data.append(df)
                    logger.info(f"✅ {sheet_name}: {len(df)} trips")
                    
                except Exception as e:
                    logger.error(f"❌ Error reading {sheet_name}: {e}")
                    continue
            
            if not all_data:
                return None
            
            # Combine all data
            combined_df = pd.concat(all_data, ignore_index=True)
            
            logger.info(f"📊 Total: {len(combined_df)} trips from {combined_df['Mã xe'].nunique()} vehicles")
            return combined_df
            
        except Exception as e:
            logger.error(f"❌ Error reading sheets: {e}")
            return None
    
    def save_to_github(self, data: pd.DataFrame) -> bool:
        """Lưu dữ liệu lên GitHub (FIXED VERSION - NO ensure_ascii)"""
        try:
            github_config = self.config['github']
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Check if repo exists first
            check_url = f"https://api.github.com/repos/{github_config['username']}/{github_config['repository']}"
            headers = {
                'Authorization': f"token {github_config['token']}",
                'Accept': 'application/vnd.github.v3+json'
            }
            
            response = requests.get(check_url, headers=headers)
            
            if response.status_code == 404:
                logger.error("❌ Repository không tồn tại!")
                logger.info("💡 Tạo repository manual tại: https://github.com/new")
                logger.info("   Repository name: vehicle-storage")
                logger.info("   Hoặc sử dụng repo hiện có: https://github.com/corner-25/vehicle-storage")
                return False
            elif response.status_code != 200:
                logger.error(f"❌ Không thể truy cập repository: {response.text}")
                return False
            
            logger.info("✅ Repository found")
            
            # FIXED: Convert to JSON without ensure_ascii parameter
            combined_json = data.to_json(orient='records', indent=2)
            
            # DEBUG: Check JSON content before upload
            logger.info(f"📄 JSON content length: {len(combined_json)} characters")
            logger.info(f"📄 JSON preview: {combined_json[:200]}...")
            
            if not combined_json or combined_json.strip() == "":
                logger.error("❌ CRITICAL: JSON content is empty!")
                return False
            
            if len(combined_json) < 100:
                logger.warning(f"⚠️ JSON content seems too short: {combined_json}")
            
            # Save latest data (for dashboard) - ONLY THIS, NO BACKUP
            latest_filename = "data/latest/fleet_data_latest.json"
            logger.info(f"🔄 Uploading main data file: {latest_filename}")
            
            upload_success = self.upload_file_to_github(
                combined_json,
                latest_filename,
                f"Update latest data - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            if not upload_success:
                logger.error("❌ CRITICAL: Failed to upload main data file!")
                return False
            else:
                logger.info("✅ Main data file uploaded successfully")
            
            # Save summary (overwrite, no timestamp)
            logger.info("🔄 Uploading summary file...")
            summary = self.generate_summary(data)
            summary_json = json.dumps(summary, indent=2, ensure_ascii=False)
            summary_filename = "data/summary/summary_latest.json"
            
            summary_success = self.upload_file_to_github(
                summary_json,
                summary_filename,
                f"Update summary - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            if summary_success:
                logger.info("✅ Summary file uploaded successfully")
            else:
                logger.warning("⚠️ Summary upload failed, but main data is OK")
            
            logger.info("✅ Data saved to GitHub successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ GitHub save error: {e}")
            return False
    
    def upload_file_to_github(self, content: str, filename: str, commit_message: str) -> bool:
        """Upload single file to GitHub"""
        try:
            github_config = self.config['github']
            
            url = f"https://api.github.com/repos/{github_config['username']}/{github_config['repository']}/contents/{filename}"
            headers = {
                'Authorization': f"token {github_config['token']}",
                'Accept': 'application/vnd.github.v3+json'
            }
            
            # Encode content
            content_encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
            
            data = {
                "message": commit_message,
                "content": content_encoded,
                "branch": github_config['branch']
            }
            
            # Check if file exists (for update)
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data["sha"] = response.json()["sha"]
                logger.info(f"📝 Updating existing file: {filename}")
            else:
                logger.info(f"📝 Creating new file: {filename}")
            
            # Upload file
            response = requests.put(url, headers=headers, json=data)
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ Successfully uploaded: {filename}")
                return True
            else:
                logger.error(f"❌ Upload error {filename}")
                logger.error(f"Status: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Upload file error: {e}")
            return False
    
    def generate_summary(self, data: pd.DataFrame) -> Dict:
        """Tạo summary stats"""
        try:
            admin_data = data[data['Loại xe'] == 'Hành chính']
            ambulance_data = data[data['Loại xe'] == 'Cứu thương']
            
            summary = {
                'timestamp': datetime.now().isoformat(),
                'total_trips': len(data),
                'total_vehicles': data['Mã xe'].nunique(),
                'admin_vehicles': len(admin_data['Mã xe'].unique()),
                'ambulance_vehicles': len(ambulance_data['Mã xe'].unique()),
                'admin_trips': len(admin_data),
                'ambulance_trips': len(ambulance_data),
                'top_vehicles': data['Mã xe'].value_counts().head(5).to_dict(),
                'top_drivers': data['Tên tài xế'].value_counts().head(5).to_dict(),
                'sync_stats': self.sync_stats
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Summary error: {e}")
            return {'error': str(e)}
    
    def sync_now(self) -> bool:
        """Thực hiện sync ngay"""
        logger.info("🚀 Starting manual sync...")
        
        self.sync_stats['total_syncs'] += 1
        
        try:
            # 1. Authenticate Google Sheets
            if not self.authenticate_google_sheets():
                raise Exception("Google Sheets authentication failed")
            
            # 2. Read all data
            combined_data = self.read_all_sheets()
            if combined_data is None or len(combined_data) == 0:
                raise Exception("No data from Google Sheets")
            
            # 3. Save to GitHub
            if not self.save_to_github(combined_data):
                raise Exception("GitHub save failed")
            
            # 4. Update stats
            self.sync_stats['successful_syncs'] += 1
            self.sync_stats['last_sync'] = datetime.now().isoformat()
            
            logger.info("✅ SYNC SUCCESSFUL!")
            logger.info(f"📊 Synced {len(combined_data)} trips from {combined_data['Mã xe'].nunique()} vehicles")
            
            return True
            
        except Exception as e:
            self.sync_stats['last_error'] = str(e)
            logger.error(f"❌ Sync failed: {e}")
            return False
    
    def test_connections(self) -> Dict[str, bool]:
        """Test connections"""
        results = {
            'google_sheets': False,
            'github': False
        }
        
        try:
            # Test Google Sheets
            if self.authenticate_google_sheets():
                results['google_sheets'] = True
            
            # Test GitHub
            github_config = self.config['github']
            if github_config['token'] != "YOUR_TOKEN_HERE":
                headers = {
                    'Authorization': f"token {github_config['token']}",
                    'Accept': 'application/vnd.github.v3+json'
                }
                response = requests.get('https://api.github.com/user', headers=headers)
                if response.status_code == 200:
                    results['github'] = True
                    user_info = response.json()
                    logger.info(f"✅ GitHub user: {user_info.get('login')}")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Test error: {e}")
            return results


def main():
    """Main function với menu đơn giản"""
    print("🚀 MANUAL FLEET DATA SYNC - FIXED VERSION")
    print("=" * 50)
    print("📊 Google Sheets → GitHub")
    print("=" * 50)
    
    sync_engine = ManualFleetSync()
    
    # Check GitHub token
    if sync_engine.config['github']['token'] == "YOUR_TOKEN_HERE":
        print("❌ GitHub token chưa được setup!")
        return
    
    while True:
        print("\n📋 MENU:")
        print("1. 🧪 Test connections")
        print("2. 🔄 Sync ngay")
        print("3. 📊 Xem stats")
        print("4. 🌐 Open GitHub repo")
        print("5. 🚪 Exit")
        
        choice = input("\nChọn (1-5): ").strip()
        
        if choice == '1':
            print("\n🧪 Testing connections...")
            results = sync_engine.test_connections()
            print(f"📊 Google Sheets: {'✅' if results['google_sheets'] else '❌'}")
            print(f"🐙 GitHub: {'✅' if results['github'] else '❌'}")
        
        elif choice == '2':
            print("\n🔄 Starting sync...")
            success = sync_engine.sync_now()
            if success:
                print("🎉 Sync completed successfully!")
            else:
                print("💥 Sync failed!")
        
        elif choice == '3':
            print("\n📊 SYNC STATS:")
            stats = sync_engine.sync_stats
            for key, value in stats.items():
                print(f"  {key}: {value}")
        
        elif choice == '4':
            repo_url = f"https://github.com/{sync_engine.config['github']['username']}/{sync_engine.config['github']['repository']}"
            print(f"\n🌐 GitHub Repository:")
            print(f"   {repo_url}")
        
        elif choice == '5':
            print("👋 Bye!")
            break
        
        else:
            print("❌ Invalid choice!")


if __name__ == "__main__":
    main()
