import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime
import os, base64


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

    .section-header {
        background-color: #f6f8fa;
        padding: 1.25rem;
        border-radius: 10px;
        margin-bottom: 1.5rem;
        text-align: center;
    }
    .section-header h2 {
        margin: 0;
        font-size: 2rem;
        font-weight: bold;
        color: #1f77b4;
    }
    .section-header p {
        margin: 0;
        font-size: 1rem;
        color: #555;
    }
</style>
""", unsafe_allow_html=True)

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
        {logo_html}
        <h1 style='
            color:#1f77b4;
            margin:0;
            font-size:3.2rem;
            font-weight:bold;
            font-family:"Segoe UI", Arial, sans-serif;
            text-shadow:2px 2px 4px rgba(0,0,0,0.1);
            letter-spacing:1px;
            text-align:center;
        '>Dashboard Quản lý số liệu Bệnh viện Đại học Y Dược TP. Hồ Chí Minh</h1>
    </div>
    """
st.markdown(header_html, unsafe_allow_html=True)

# Dữ liệu Phòng VTTB
vttb_data = {
    "sua_chua": {
        "phat_sinh": 2322,
        "hoan_thanh": 1973,
        "ty_le_hoan_thanh": round((1973/2322)*100, 1)
    },
    "trang_thai_tbyt": {
        "khac_phuc_tam_thoi": 54,
        "dang_sua_chua": 87,
        "thanh_ly": 2574,
        "tong_tam_ngung": 54 + 87 + 2574
    },
    "dau_thau": {
        "dang_thuc_hien": 49,
        "hoan_thanh": 51,
        "tong_gia_tri": 1158385811271
    },
    "van_ban": {
        "tong_den": 4965,
        "hoan_thanh": 4695,
        "chua_xu_ly": 144,
        "dang_xu_ly": 126,
        "ty_le_chua_xu_ly": 3,
        "ty_le_dang_xu_ly": 3
    },
    "kho": {
        "nhap_hcsk": 11150128821,
        "nhap_lktm": 13134877542,
        "xuat_hcsk": 11032099005,
        "xuat_lktm": 12868396672,
        "ton_hcsk": 833431469,
        "ton_lktm": 1017249841
    }
}

# Dữ liệu Khoa KSKTYC
ksktyc_data = {
    "kham_khong_nn": {"value": 26794, "growth": 13.68},
    "kham_co_nn": {"value": 383, "growth": 751.11},
    "kham_lai_xe": {"value": 0, "growth": 0},
    "kham_dinh_ky": {"value": 24458, "growth": 14.23},
    "kham_hop_dong": {"value": 17803, "growth": 2.69},
    "kham_khong_hop_dong": {"value": 6655, "growth": 63.31},
    "kham_ca_nhan": {"value": 2719, "growth": 23.42},
    "kham_noi_vien": {"value": 23554, "growth": 20.23},
    "kham_ngoai_vien": {"value": 3623, "growth": -9.97}
}

# Dữ liệu Phòng CNTT
cntt_data = {
    "thiet_bi": {
        "laptop": {"name": "Laptop", "quantity": 115},
        "may_vi_tinh": {"name": "Máy vi tính", "quantity": 1480},
        "kiosk": {"name": "Kiosk điện tử", "quantity": 12},
        "may_in_laser": {"name": "Máy in Laser trắng đen", "quantity": 611},
        "may_in_mau": {"name": "Máy in màu", "quantity": 63},
        "may_in_ma_vach": {"name": "Máy in mã vạch", "quantity": 362},
        "dau_doc_ma_vach": {"name": "Đầu đọc mã vạch", "quantity": 482},
        "may_in_nhiet": {"name": "Máy in nhiệt", "quantity": 101},
        "switch": {"name": "Switch", "quantity": 247},
        "access_point": {"name": "Access Point", "quantity": 416},
        "server_vat_ly": {"name": "Server vật lý", "quantity": 16},
        "server_ao_hoa": {"name": "Server ảo hóa", "quantity": 220},
        "san": {"name": "SAN", "quantity": 5},
        "das": {"name": "DAS", "quantity": 1},
        "nas": {"name": "NAS", "quantity": 5},
        "router": {"name": "Router", "quantity": 2},
        "wifi_controller": {"name": "Wifi Controller", "quantity": 4},
        "firewall_cisco": {"name": "Firewall trong Cisco", "quantity": 2},
        "firewall_fortigate": {"name": "Firewall ngoài Fortigate", "quantity": 4},
        "san_switch": {"name": "SAN switch", "quantity": 4},
        "may_tinh_bang": {"name": "Máy tính bảng", "quantity": 404},
        "may_scan": {"name": "Máy scan", "quantity": 111},
        "may_in_the": {"name": "Máy in thẻ VietinBank", "quantity": 10}
    },
    "hoat_dong": {
        "giai_quyet_de_nghi": {"name": "Giải quyết Đề nghị/Yêu cầu từ các Đơn vị", "value": 97.16, "unit": "%", "comparison": 97.56},
        "ho_tro_phan_cung": {"name": "Hỗ trợ Phần cứng - Mạng", "value": 2546, "unit": "lượt", "comparison": 2734},
        "ho_tro_phan_mem": {"name": "Hỗ trợ phần mềm và thống kê số liệu", "value": 2806, "unit": "lượt", "comparison": 2752},
        "trien_khai_chuc_nang": {"name": "Triển khai chức năng phần mềm mới", "value": 87, "unit": "chức năng", "comparison": 71},
        "dang_ky_kham_online": {"name": "Đăng ký khám trực tuyến UMC Care", "value": 515745, "unit": "lượt", "comparison": 166600},
        "su_dung_app": {"name": "Sử dụng ứng dụng di động", "value": 1144937, "unit": "lượt", "comparison": 585431},
        "ty_le_su_dung": {"name": "Tỷ lệ sử dụng trực tuyến", "value": 45.05, "unit": "%", "comparison": 28.46},
        "tham_quan": {"name": "Tiếp đoàn tham quan, học tập về CNTT", "value": 10, "unit": "đoàn", "comparison": 12}
    }
}

# Dữ liệu Trung Tâm Truyền Thông
tttt_data = {
    "bai_viet_truyen_thong": {
        "2024": 1201,
        "2025": 822,
        "growth": -32
    },
    "chuong_trinh_phong_su": {
        "2024": 390,
        "2025": 204,
        "growth": -48
    },
    "chuong_trinh_giao_duc": {
        "2024": 10,
        "2025": 4,
        "growth": -60
    },
    "website": {
        "luot_truy_cap_2024": 33855428,
        "luot_truy_cap_2025": 36074074,
        "luot_truy_cap_growth": 6.5,
        "bai_viet_2024": 140,
        "bai_viet_2025": 156,
        "bai_viet_growth": 11
    },
    "fanpage": {
        "luot_thich_2024": 186830,
        "luot_thich_2025": 229832,
        "luot_thich_growth": 23,
        "bai_viet_2024": 270,
        "bai_viet_2025": 239,
        "bai_viet_growth": -11,
        "hoi_dap_2024": 9015,
        "hoi_dap_2025": 9255,
        "hoi_dap_growth": 3
    },
    "zalo": {
        "luot_quan_tam_2024": 7035,
        "luot_quan_tam_2025": 10005,
        "luot_quan_tam_growth": 42,
        "bai_viet_2024": 221,
        "bai_viet_2025": 251,
        "bai_viet_growth": 14
    },
    "youtube": {
        "luot_dang_ky_2024": 163111,
        "luot_dang_ky_2025": 189403,
        "luot_dang_ky_growth": 16,
        "video_2024": 156,
        "video_2025": 174,
        "video_growth": 12
    },
    "tiktok": {
        "luot_dang_ky_2024": 0,
        "luot_dang_ky_2025": 3585,
        "luot_dang_ky_growth": 100,
        "video_2024": 0,
        "video_2025": 23,
        "video_growth": 100
    },
    "an_pham": {
        "loai_an_pham_2024": 15,
        "loai_an_pham_2025": 140,
        "loai_an_pham_growth": 833,
        "so_luong_2024": 0,
        "so_luong_2025": 300713,
        "so_luong_growth": 100
    }
}

# Dữ liệu Phòng Công Tác Xã Hội
ctxh_data = {
    "ho_tro_nguoi_benh": {
        "tu_van_nhap_vien": {"value": 24136, "comparison": 89.92, "unit": "Trường hợp"},
        "tu_van_xuat_vien": {"value": 23636, "comparison": 93.53, "unit": "Trường hợp"},
        "goi_dien_thoai": {"value": 4599, "comparison": 86, "unit": "Cuộc gọi"},
        "tin_nhan_tai_kham": {"value": 20743, "comparison": 103.84, "unit": "Tin nhắn"},
        "cai_dat_app": {"value": 23248, "comparison": 103, "unit": "Lượt"},
        "ho_tro_kho_khan": {"value": 86, "comparison": 661, "unit": "Lượt người"},
        "kinh_phi_ho_tro": {"value": 8575712876, "comparison": 395, "unit": "Đồng"},
        "ho_tro_tam_ly": {"value": 254, "comparison": 49, "unit": "Lượt người"},
        "chuong_trinh_ho_tro": {"value": 5, "comparison": 83.33, "unit": "Chương trình"},
        "hai_long_noi_tru": {"value": 99.20, "comparison": 100.61, "unit": "%"}
    },
    "sinh_hoat_nha": {
        "lan_sinh_hoat_cc": {"value": 246, "comparison": 95, "unit": "Lần"},
        "nguoi_tham_du_cc": {"value": 6950, "comparison": 116, "unit": "Lượt người"},
        "lan_sinh_hoat_gmhs": {"value": 250, "comparison": 96, "unit": "Lần"},
        "nguoi_tham_du_gmhs": {"value": 14953, "comparison": 94, "unit": "Lượt người"},
        "tu_van_phau_thuat": {"value": 3118, "comparison": 78.84, "unit": "Lượt người"},
        "videocall": {"value": 5719, "comparison": 94, "unit": "Lượt người"}
    },
    "ho_tro_thuoc": {
        "so_chuong_trinh": {"value": 12, "comparison": 100, "unit": "Chương trình"},
        "nguoi_benh_tham_gia": {"value": 313, "comparison": 148.34, "unit": "Lượt người"},
        "tien_tai_tro": {"value": 57942065779, "comparison": 186.22, "unit": "Đồng"}
    },
    "tiep_nhan_gop_y": {
        "thu_khen": {"value": 294, "comparison": 108, "unit": "Thư"},
        "thu_gop_y": {"value": 9, "comparison": 450, "unit": "Thư"},
        "duong_day_byt": {"value": 0, "comparison": 100, "unit": "Trường hợp"},
        "duong_day_gd": {"value": 82, "comparison": 97.62, "unit": "Trường hợp"}
    },
    "cham_soc_cong_dong": {
        "tong_kinh_phi": {"value": 2178690356, "comparison": 77, "unit": "Đồng"},
        "so_chuong_trinh": {"value": 10, "comparison": 91, "unit": "Chương trình"},
        "luot_dan": {"value": 4062, "comparison": 103, "unit": "Lượt người"},
        "me_vnah_tb": {"value": 12, "comparison": 66.67, "unit": "Lượt người"},
        "nan_nhan_da_cam": {"value": 1000, "comparison": 142.86, "unit": "Lượt người"},
        "tang_bo": {"value": 0, "comparison": 0, "unit": "Con"},
        "tang_xe_dap": {"value": 36, "comparison": 120, "unit": "Cái"},
        "so_tiet_kiem": {"value": 0, "comparison": 0, "unit": "Cái"},
        "hoc_bong": {"value": 0, "comparison": 100, "unit": "Suất"},
        "cong_trinh": {"value": 1, "comparison": 0, "unit": "Công trình"}
    },
    "van_dong_tai_tro": {
        "so_tien": {"value": 65.9, "comparison": 173.88, "unit": "Đồng"}
    }
}

tcbc_data = {
    "to_chuc": {
        "phong_trung_tam": {"value": 16, "change": 0},
        "khoa": {"value": 54, "change": -1, "detail": {"chinh": 42, "lien_ket": 10, "phu_thuoc": 2}},
        "trung_tam": {"value": 6, "change": 0, "detail": {"chinh": 4, "lien_ket": 1, "phu_thuoc": 1}},
        "don_nguyen": {"value": 30, "change": +1, "detail": {"chinh": 28, "lien_ket": 2, "phu_thuoc": 0}},
        "don_vi": {"value": 6, "change": 0, "detail": {"chinh": 1, "lien_ket": 2, "phu_thuoc": 3}},
        "tram": {"value": 1, "change": +1},
        "hoi_dong": {"value": 27, "change": 0, "detail": {"chinh": 26, "phu_thuoc": 1}},
        "to": {"value": 14, "change": 0, "detail": {"chinh": 12, "lien_ket": 1, "phu_thuoc": 1}},
        "ban_tieu_ban": {"value": 21, "change": 0},
        "mang_luoi": {"value": 17, "change": 0},
        "sap_xep_don_vi": {
            "thanh_lap": {"value": 1, "change": +1},
            "doi_ten": {"value": 30, "change": +30},
            "giai_the": {"value": 7, "change": +7}
        }
    },
    "nhan_su": {
        "thuong_xuyen": {"value": 3598, "change": +135, "detail": {"chinh": 3155, "lien_ket": 364, "phu_thuoc": 79}},
        "vu_viec_toan_tg": {"value": 144, "change": -5, "detail": {"chinh": 114, "lien_ket": 24, "phu_thuoc": 6}},
        "vu_viec_ban_tg": {"value": 637, "change": +33, "detail": {"chinh": 475, "lien_ket": 128, "phu_thuoc": 34}},
        "bo_nhiem": {"value": 3, "change": +1},
        "bo_nhiem_lai": {"value": 9, "change": +6},
        "giao_phu_trach": {"value": 5, "change": +5, "detail": {"chinh": 3, "lien_ket": 2}},
        "thoi_chuc_vu": {"value": 4, "change": +2, "detail": {"chinh": 2, "lien_ket": 2}},
        "tuyen_dung": {"value": 105, "change": -46, "detail": {"chinh": 80, "lien_ket": 21, "phu_thuoc": 4}},
        "cham_dut_hdld": {"value": 36, "change": -6, "detail": {"chinh": 35, "phu_thuoc": 1}},
        
        # THÊM DỮ LIỆU MỚI - CƠ CẤU NHÂN SỰ CHI TIẾT
        "tong_nhan_su_3_co_so": {
            "t6_2024": 4216,
            "t6_2025": 4379,
            "tang_giam": 163,
            "tang_giam_percent": 3.87
        },
        "co_cau_trinh_do": {
            "sau_dai_hoc": {
                "t6_2024": 1158,
                "t6_2025": 1236,
                "tang_giam": 78,
                "tang_giam_percent": 6.7
            },
            "dai_hoc": {
                "t6_2024": 1331,
                "t6_2025": 1514,
                "tang_giam": 183,
                "tang_giam_percent": 13.7
            },
            "cao_dang_trung_hoc": {
                "t6_2024": 1129,
                "t6_2025": 998,
                "tang_giam": -131,
                "tang_giam_percent": -11.6
            },
            "pho_thong_trung_hoc": {
                "t6_2024": 598,
                "t6_2025": 631,
                "tang_giam": 33,
                "tang_giam_percent": 5.5
            }
        },
        "co_cau_chi_tiet": {
            "giao_su": {"so_luong": 12, "ty_le": 0.27},
            "pho_giao_su": {"so_luong": 86, "ty_le": 1.96},
            "tien_si": {"so_luong": 146, "ty_le": 3.33},
            "bac_sy_ck2": {"so_luong": 135, "ty_le": 3.08},
            "thac_si": {"so_luong": 642, "ty_le": 14.66},
            "bac_sy_ck1": {"so_luong": 215, "ty_le": 4.91},
            "dai_hoc_chi_tiet": {"so_luong": 1514, "ty_le": 34.57},
            "cao_dang": {"so_luong": 80, "ty_le": 1.83},
            "trung_hoc": {"so_luong": 918, "ty_le": 20.96},
            "nhan_vien_yte_khac": {"so_luong": 631, "ty_le": 14.41}
        }
    },
    "dao_tao": {
        "cu_dao_tao": {"value": 301, "change": +112, "detail": {"trong_nuoc": 255, "nuoc_ngoai": 46}},
        "dao_tao_noi_bo": {
            "so_lop": {"value": 7, "change": +3},
            "luot_tham_gia": {"value": 617, "change": +166}
        }
    },
    "khieu_nai_to_cao": {
        "don_thu_khieu_nai": {"value": 1, "change": 0},
        "don_thu_to_cao": {"value": 0, "change": 0},
        "vu_viec_khoi_kien": {"value": 0, "change": 0},
        "da_giai_quyet": {"value": 0, "change": 0},
        "chua_giai_quyet": {"value": 0, "change": 0}
    },
    "thi_dua_khen_thuong": {
        "khen_dinh_ky": {"value": 49, "change": 0, "detail": {"tap_the": 48, "ca_nhan": 1}},
        "khen_dot_xuat": {"value": 983, "change": 0, "detail": {"tap_the": 812, "ca_nhan": 170, "phu_thuoc": 1}},
        "sang_kien": {"value": 0, "change": 0},
        "danh_gia": {"value": 0, "change": 0}
    }
}

qttn_data = {
    "hieu_suat_hoat_dong": {
        "ty_le_hoan_thanh_de_nghi": {"value": 63, "target": 80},
        "ty_le_hoan_thanh_sua_chua": {"value": 100, "target": 95},
        "ty_le_hoan_thanh_ke_hoach": {"value": 70, "target": 85},
        "ty_le_hoan_thanh_mua_sam": {"value": 78, "target": 80}
    },
    "chat_thai": {
        "rac_thai_thong_thuong": {"value": 655, "unit": "tấn"},
        "chat_thai_nguy_hai_lay_nhiem": {"value": 218.7, "unit": "tấn"},
        "chat_thai_nguy_hai": {"value": 12.5, "unit": "tấn"},
        "tai_che": {
            "giay": {"value": 86.4, "unit": "tấn"},
            "nhua": {"value": 12.9, "unit": "tấn"}
        }
    },
    "kho_khi_y_te": {
        "tong_hop": {
            "ton_dau_ky": 17342225,
            "nhap_trong_ky": 1519526118,
            "xuat_trong_ky": 1514080998,
            "ton_cuoi_ky": 22787345
        },
        "chi_tiet_ton_cuoi_ky": {
            "argon_1m3": {"value": 218000, "quantity": 2, "unit": "VND/bình"},
            "co2_25kg": {"value": 17070625, "quantity": 65, "unit": "VND/bình"},
            "co2_8kg": {"value": 1512720, "quantity": 18, "unit": "VND/bình"},
            "nitro_6m3": {"value": 1925000, "quantity": 25, "unit": "VND/bình"},
            "oxy_lon_6m3": {"value": 1863000, "quantity": 36, "unit": "VND/bình"},
            "oxy_nho_2m3": {"value": 198000, "quantity": 6, "unit": "VND/bình"}
        },
        "theo_thang": {
            "ton_dau_ky": [17342225, 16176124, 16005975, 23232700, 21811794, 22746944],
            "nhap": [260105615, 271425594, 222402147, 344070650, 204267338, 217254774],
            "xuat": [261271716, 271595743, 215175422, 345491556, 203332188, 217214373],
            "ton_cuoi_ky": [16176124, 16005975, 23232700, 21811794, 22746944, 22787345]
        }
    }
}

# TABS CHÍNH - MỖI PHÒNG BAN MỘT TAB
tab_vttb, tab_ksktyc, tab_cntt, tab_ctxh, tab_tttt, tab_tcbc, tab_qttn = st.tabs([
    "🔧 Vật Tư Thiết Bị", 
    "🩺 Khám Sức Khỏe Theo Yêu Cầu",
    "💻 Công Nghệ Thông Tin",
    "🤝 Công Tác Xã Hội",
    "📱 Truyền Thông",
    "👥 Tổ chức Cán bộ",
    "🏢 Quản trị Tòa nhà"
])

# ==================== TAB PHÒNG VTTB ====================
with tab_vttb:
    st.markdown("""
    <div class="section-header">
        <h2>🔧 VẬT TƯ THIẾT BỊ</h2>
        <p>Quản lý sửa chữa, đấu thầu, kho vật tư và xử lý văn bản</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sub-tabs cho VTTB
    subtab1, subtab2, subtab3, subtab4, subtab5 = st.tabs([
        "📊 Tổng Quan", "🔧 Sửa Chữa TBYT", "📦 Mua Sắm", "📄 Văn Bản", "🏪 Quản Lý Kho"
    ])
    
    # Mock data cho xu hướng 6 tháng
    months = ['Tháng 1', 'Tháng 2', 'Tháng 3', 'Tháng 4', 'Tháng 5', 'Tháng 6']
    
    # VTTB - Tab Tổng quan
    with subtab1:
        st.header("📊 Tổng quan hoạt động")
        
        # KPI Cards hàng đầu
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Tỷ lệ hoàn thành sửa chữa",
                f"{vttb_data['sua_chua']['ty_le_hoan_thanh']}%",
                f"{vttb_data['sua_chua']['ty_le_hoan_thanh'] - 80:.1f}% vs target 80%"
            )
        
        with col2:
            st.metric(
                "Gói thầu hoàn thành",
                f"{vttb_data['dau_thau']['hoan_thanh']} gói",
                f"+{vttb_data['dau_thau']['hoan_thanh'] - 45} vs kế hoạch"
            )
        
        with col3:
            st.metric(
                "Tỷ lệ xử lý văn bản",
                f"{round((vttb_data['van_ban']['hoan_thanh']/vttb_data['van_ban']['tong_den'])*100, 1)}%",
                "Đạt mục tiêu"
            )
        
        with col4:
            tong_ton_kho = vttb_data['kho']['ton_hcsk'] + vttb_data['kho']['ton_lktm']
            st.metric(
                "Tổng tồn kho",
                f"{tong_ton_kho/1e9:.1f} tỷ VNĐ",
                "Ổn định"
            )
        
        # Biểu đồ tổng quan
        col1, col2 = st.columns(2)
        
        with col1:
            # Biểu đồ trạng thái thiết bị
            fig_status = go.Figure(data=[go.Pie(
                labels=['Đã khắc phục (tạm thời)', 'Đang sửa chữa', 'Đã thanh lý'],
                values=[
                    vttb_data['trang_thai_tbyt']['khac_phuc_tam_thoi'],
                    vttb_data['trang_thai_tbyt']['dang_sua_chua'],
                    vttb_data['trang_thai_tbyt']['thanh_ly']
                ],
                hole=0.4,
                marker_colors=['#28a745', '#ffc107', '#dc3545']
            )])
            fig_status.update_layout(title="Trạng thái thiết bị tạm ngưng sử dụng")
            st.plotly_chart(fig_status, use_container_width=True)
        
        with col2:
            # Biểu đồ so sánh nhập xuất kho
            kho_data = pd.DataFrame({
                'Loại kho': ['HCSK', 'LKTM'],
                'Nhập kho': [vttb_data['kho']['nhap_hcsk']/1e9, vttb_data['kho']['nhap_lktm']/1e9],
                'Xuất kho': [vttb_data['kho']['xuat_hcsk']/1e9, vttb_data['kho']['xuat_lktm']/1e9]
            })
            
            fig_kho = px.bar(kho_data, x='Loại kho', y=['Nhập kho', 'Xuất kho'],
                            title="Nhập xuất kho (tỷ VNĐ)",
                            barmode='group',
                            color_discrete_sequence=['#4ECDC4', '#FFA07A'])
            st.plotly_chart(fig_kho, use_container_width=True)

    # VTTB - Tab Sửa chữa
    with subtab2:
        st.header("🔧 Công Tác Sửa Chữa Thiết Bị Y Tế")
        
        # Metrics sửa chữa
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Công việc phát sinh",
                f"{vttb_data['sua_chua']['phat_sinh']:,}",
                "công việc"
            )
        
        with col2:
            st.metric(
                "Đã hoàn thành",
                f"{vttb_data['sua_chua']['hoan_thanh']:,}",
                f"{vttb_data['sua_chua']['hoan_thanh'] - vttb_data['sua_chua']['phat_sinh']:+,} vs phát sinh"
            )
        
        with col3:
            st.metric(
                "Tỷ lệ hoàn thành",
                f"{vttb_data['sua_chua']['ty_le_hoan_thanh']}%",
                f"{vttb_data['sua_chua']['ty_le_hoan_thanh'] - 85:.1f}% vs target 85%"
            )
        
        # Biểu đồ xu hướng sửa chữa (mock data dựa trên dữ liệu thực)        
        # Tạo xu hướng tăng dần
        phat_sinh_trend = [350, 380, 395, 410, 385, 402]  # Tổng = 2322
        hoan_thanh_trend = [290, 320, 340, 350, 315, 358]  # Tổng = 1973
        
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(x=months, y=phat_sinh_trend, 
                                      mode='lines+markers', name='Phát sinh',
                                      line=dict(color='#FF6B6B', width=3)))
        fig_trend.add_trace(go.Scatter(x=months, y=hoan_thanh_trend,
                                      mode='lines+markers', name='Hoàn thành',
                                      line=dict(color='#4ECDC4', width=3)))
        
        fig_trend.update_layout(
            title="Xu hướng sửa chữa TBYT theo tháng",
            xaxis_title="Tháng",
            yaxis_title="Số lượng công việc",
            height=400
        )
        st.plotly_chart(fig_trend, use_container_width=True)
        
        # Bảng chi tiết trạng thái thiết bị
        st.subheader("📋 Chi tiết trạng thái thiết bị tạm ngưng")
        
        status_df = pd.DataFrame({
            'Trạng thái': [
                'Đã khắc phục (theo dõi tiếp)',
                'Đang sửa chữa',
                'Đã thanh lý'
            ],
            'Số lượng': [
                vttb_data['trang_thai_tbyt']['khac_phuc_tam_thoi'],
                vttb_data['trang_thai_tbyt']['dang_sua_chua'],
                vttb_data['trang_thai_tbyt']['thanh_ly']
            ],
            'Tỷ lệ (%)': [
                round((vttb_data['trang_thai_tbyt']['khac_phuc_tam_thoi']/vttb_data['trang_thai_tbyt']['tong_tam_ngung'])*100, 1),
                round((vttb_data['trang_thai_tbyt']['dang_sua_chua']/vttb_data['trang_thai_tbyt']['tong_tam_ngung'])*100, 1),
                round((vttb_data['trang_thai_tbyt']['thanh_ly']/vttb_data['trang_thai_tbyt']['tong_tam_ngung'])*100, 1)
            ]
        })
        
        st.dataframe(status_df, use_container_width=True)

    # VTTB - Tab Đấu thầu  
    with subtab3:
        st.header("📦 Công tác Mua sắm")
        
        # Metrics đấu thầu
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Gói thầu đang thực hiện",
                f"{vttb_data['dau_thau']['dang_thuc_hien']}",
                "gói thầu"
            )
        
        with col2:
            st.metric(
                "Đã hoàn thành",
                f"{vttb_data['dau_thau']['hoan_thanh']}",
                "gói thầu"
            )
        
        with col3:
            st.metric(
                "Tổng giá trị",
                f"{vttb_data['dau_thau']['tong_gia_tri']/1e9:.1f} tỷ VNĐ",
                "mua sắm"
            )
        
        # Biểu đồ tiến độ đấu thầu
        col1, col2 = st.columns(2)
        
        with col1:
            # Pie chart tiến độ
            fig_progress = go.Figure(data=[go.Pie(
                labels=['Đã hoàn thành', 'Đang thực hiện'],
                values=[vttb_data['dau_thau']['hoan_thanh'], vttb_data['dau_thau']['dang_thuc_hien']],
                hole=0.4,
                marker_colors=['#28a745', '#ffc107']
            )])
            fig_progress.update_layout(title="Tiến độ thực hiện gói thầu")
            st.plotly_chart(fig_progress, use_container_width=True)
        
        with col2:
            # Xu hướng hoàn thành theo tháng (mock data)
            completion_trend = [6, 8, 9, 10, 9, 9]  # Tổng = 51
            
            fig_completion = px.bar(
                x=months, y=completion_trend,
                title="Gói thầu hoàn thành theo tháng",
                color=completion_trend,
                color_continuous_scale='Teal'
            )
            fig_completion.update_layout(showlegend=False)
            st.plotly_chart(fig_completion, use_container_width=True)

    # VTTB - Tab Văn bản
    with subtab4:
        st.header("📄 Xử Lý Hồ Sơ & Văn Bản")
        
        # Metrics văn bản
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Tổng văn bản đến",
                f"{vttb_data['van_ban']['tong_den']:,}",
                "văn bản"
            )
        
        with col2:
            st.metric(
                "Đã hoàn thành",
                f"{vttb_data['van_ban']['hoan_thanh']:,}",
                f"{round((vttb_data['van_ban']['hoan_thanh']/vttb_data['van_ban']['tong_den'])*100, 1)}%"
            )
        
        with col3:
            st.metric(
                "Đang xử lý",
                f"{vttb_data['van_ban']['dang_xu_ly']}",
                f"{vttb_data['van_ban']['ty_le_dang_xu_ly']}%"
            )
        
        with col4:
            st.metric(
                "Chưa xử lý",
                f"{vttb_data['van_ban']['chua_xu_ly']}",
                f"{vttb_data['van_ban']['ty_le_chua_xu_ly']}%"
            )
        
        # Biểu đồ trạng thái văn bản
        col1, col2 = st.columns(2)
        
        with col1:
            # Donut chart trạng thái
            fig_status = go.Figure(data=[go.Pie(
                labels=['Đã hoàn thành', 'Đang xử lý', 'Chưa xử lý'],
                values=[
                    vttb_data['van_ban']['hoan_thanh'],
                    vttb_data['van_ban']['dang_xu_ly'],
                    vttb_data['van_ban']['chua_xu_ly']
                ],
                hole=0.4,
                marker_colors=['#28a745', '#ffc107', '#dc3545']
            )])
            fig_status.update_layout(title="Trạng thái xử lý văn bản")
            st.plotly_chart(fig_status, use_container_width=True)
        
        with col2:
            # Progress bar
            progress = (vttb_data['van_ban']['hoan_thanh'] / vttb_data['van_ban']['tong_den']) * 100
            
            fig_progress = go.Figure(go.Indicator(
                mode = "gauge+number+delta",
                value = progress,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "Tỷ lệ hoàn thành (%)"},
                delta = {'reference': 95, 'increasing': {'color': "green"}},
                gauge = {
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "#4ECDC4"},
                    'steps': [
                        {'range': [0, 80], 'color': "lightgray"},
                        {'range': [80, 95], 'color': "yellow"},
                        {'range': [95, 100], 'color': "lightgreen"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 95
                    }
                }
            ))
            fig_progress.update_layout(height=300)
            st.plotly_chart(fig_progress, use_container_width=True)

    # VTTB - Tab Kho
    with subtab5:
        st.header("🏪 Công Tác Cung Ứng & Quản Lý Kho")
        
        # Hiển thị thông tin tổng quan
        st.subheader("📈 Tổng Quan Xuất Nhập Tồn (6 tháng đầu năm 2025)")
        
        # Metrics kho - chia thành 2 hàng
        st.write("**🏪 KHO HCSK (Hành chính sự nghiệp)**")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Tổng nhập kho",
                f"{vttb_data['kho']['nhap_hcsk']/1e9:.2f} tỷ VNĐ",
                "6 tháng"
            )
        
        with col2:
            st.metric(
                "Tổng xuất kho", 
                f"{vttb_data['kho']['xuat_hcsk']/1e9:.2f} tỷ VNĐ",
                "6 tháng"
            )
        
        with col3:
            st.metric(
                "Tồn kho hiện tại",
                f"{vttb_data['kho']['ton_hcsk']/1e9:.3f} tỷ VNĐ",
                f"{((vttb_data['kho']['ton_hcsk']/vttb_data['kho']['nhap_hcsk'])*100):.1f}% nhập kho"
            )
        
        st.write("**🏭 KHO LKTM (Lâm sàng kỹ thuật)**")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Tổng nhập kho",
                f"{vttb_data['kho']['nhap_lktm']/1e9:.2f} tỷ VNĐ",
                "6 tháng"
            )
        
        with col2:
            st.metric(
                "Tổng xuất kho",
                f"{vttb_data['kho']['xuat_lktm']/1e9:.2f} tỷ VNĐ",
                "6 tháng"
            )
        
        with col3:
            st.metric(
                "Tồn kho hiện tại",
                f"{vttb_data['kho']['ton_lktm']/1e9:.3f} tỷ VNĐ", 
                f"{((vttb_data['kho']['ton_lktm']/vttb_data['kho']['nhap_lktm'])*100):.1f}% nhập kho"
            )
        
        # Biểu đồ phân tích kho
        col1, col2 = st.columns(2)
        
        with col1:
            # Biểu đồ cột so sánh nhập xuất tồn
            kho_data = pd.DataFrame({
                'Loại kho': ['HCSK', 'HCSK', 'HCSK', 'LKTM', 'LKTM', 'LKTM'],
                'Hoạt động': ['Nhập', 'Xuất', 'Tồn', 'Nhập', 'Xuất', 'Tồn'],
                'Giá trị (tỷ VNĐ)': [
                    vttb_data['kho']['nhap_hcsk']/1e9,
                    vttb_data['kho']['xuat_hcsk']/1e9,
                    vttb_data['kho']['ton_hcsk']/1e9,
                    vttb_data['kho']['nhap_lktm']/1e9,
                    vttb_data['kho']['xuat_lktm']/1e9,
                    vttb_data['kho']['ton_lktm']/1e9
                ]
            })
            
            fig_kho_detail = px.bar(kho_data, x='Loại kho', y='Giá trị (tỷ VNĐ)',
                                   color='Hoạt động', barmode='group',
                                   title="So sánh Nhập - Xuất - Tồn kho",
                                   color_discrete_sequence=['#4ECDC4', '#FF6B6B', '#FFA500'])
            fig_kho_detail.update_layout(height=400)
            st.plotly_chart(fig_kho_detail, use_container_width=True)
        
        with col2:
            # Pie chart tỷ lệ tồn kho
            ton_kho_data = pd.DataFrame({
                'Kho': ['HCSK', 'LKTM'],
                'Tồn kho (tỷ VNĐ)': [
                    vttb_data['kho']['ton_hcsk']/1e9,
                    vttb_data['kho']['ton_lktm']/1e9
                ],
                'Tỷ lệ (%)': [
                    (vttb_data['kho']['ton_hcsk']/(vttb_data['kho']['ton_hcsk']+vttb_data['kho']['ton_lktm']))*100,
                    (vttb_data['kho']['ton_lktm']/(vttb_data['kho']['ton_hcsk']+vttb_data['kho']['ton_lktm']))*100
                ]
            })
            
            fig_inventory = px.pie(ton_kho_data, values='Tồn kho (tỷ VNĐ)', names='Kho',
                                  title="Cơ cấu tồn kho hiện tại",
                                  color_discrete_sequence=['#4ECDC4', '#FF9999'])
            
            # Thêm thông tin tỷ lệ vào labels
            fig_inventory.update_traces(
                textposition='inside', 
                textinfo='percent+label',
                hovertemplate='<b>%{label}</b><br>Giá trị: %{value:.3f} tỷ VNĐ<br>Tỷ lệ: %{percent}<extra></extra>'
            )
            fig_inventory.update_layout(height=400)
            st.plotly_chart(fig_inventory, use_container_width=True)
        
        # Biểu đồ dòng tiền kho
        st.subheader("💰 Phân Tích Dòng Tiền Kho")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Tỷ lệ xuất/nhập
            ty_le_hcsk = (vttb_data['kho']['xuat_hcsk']/vttb_data['kho']['nhap_hcsk'])*100
            ty_le_lktm = (vttb_data['kho']['xuat_lktm']/vttb_data['kho']['nhap_lktm'])*100
            
            efficiency_data = pd.DataFrame({
                'Kho': ['HCSK', 'LKTM'],
                'Tỷ lệ xuất/nhập (%)': [ty_le_hcsk, ty_le_lktm]
            })
            
            fig_efficiency = px.bar(efficiency_data, x='Kho', y='Tỷ lệ xuất/nhập (%)',
                                   title="Hiệu quả sử dụng kho (Xuất/Nhập)",
                                   color='Tỷ lệ xuất/nhập (%)',
                                   color_continuous_scale='Viridis',
                                   text='Tỷ lệ xuất/nhập (%)')
            
            fig_efficiency.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig_efficiency.add_hline(y=100, line_dash="dash", line_color="red", 
                                   annotation_text="Mục tiêu 100%")
            st.plotly_chart(fig_efficiency, use_container_width=True)
        
        with col2:
            # Xu hướng tồn kho (mock data - chia đều 6 tháng)
            months = ['T1', 'T2', 'T3', 'T4', 'T5', 'T6']
            
            # Giả sử tồn kho tăng dần qua các tháng
            ton_hcsk_trend = np.linspace(500, vttb_data['kho']['ton_hcsk']/1e6, 6)
            ton_lktm_trend = np.linspace(600, vttb_data['kho']['ton_lktm']/1e6, 6)
            
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(x=months, y=ton_hcsk_trend,
                                          mode='lines+markers', name='HCSK',
                                          line=dict(color='#4ECDC4', width=3)))
            fig_trend.add_trace(go.Scatter(x=months, y=ton_lktm_trend,
                                          mode='lines+markers', name='LKTM',
                                          line=dict(color='#FF6B6B', width=3)))
            
            fig_trend.update_layout(
                title="Xu hướng tồn kho theo tháng",
                xaxis_title="Tháng",
                yaxis_title="Tồn kho (triệu VNĐ)",
                height=400
            )
            st.plotly_chart(fig_trend, use_container_width=True)
        
        # Bảng chi tiết đầy đủ
        st.subheader("📊 Bảng Tổng Hợp Chi Tiết Xuất Nhập Tồn")
        
        # Tính toán các chỉ số bổ sung
        tong_nhap = vttb_data['kho']['nhap_hcsk'] + vttb_data['kho']['nhap_lktm']
        tong_xuat = vttb_data['kho']['xuat_hcsk'] + vttb_data['kho']['xuat_lktm']
        tong_ton = vttb_data['kho']['ton_hcsk'] + vttb_data['kho']['ton_lktm']
        
        inventory_detail = pd.DataFrame({
            'Loại kho': ['HCSK', 'LKTM', '📊 TỔNG CỘNG'],
            'Nhập kho (VNĐ)': [
                f"{vttb_data['kho']['nhap_hcsk']:,}",
                f"{vttb_data['kho']['nhap_lktm']:,}",
                f"{tong_nhap:,}"
            ],
            'Xuất kho (VNĐ)': [
                f"{vttb_data['kho']['xuat_hcsk']:,}",
                f"{vttb_data['kho']['xuat_lktm']:,}",
                f"{tong_xuat:,}"
            ],
            'Tồn kho (VNĐ)': [
                f"{vttb_data['kho']['ton_hcsk']:,}",
                f"{vttb_data['kho']['ton_lktm']:,}",
                f"{tong_ton:,}"
            ],
            'Tỷ lệ xuất/nhập (%)': [
                f"{(vttb_data['kho']['xuat_hcsk']/vttb_data['kho']['nhap_hcsk']*100):.1f}%",
                f"{(vttb_data['kho']['xuat_lktm']/vttb_data['kho']['nhap_lktm']*100):.1f}%",
                f"{(tong_xuat/tong_nhap*100):.1f}%"
            ],
            'Tỷ lệ tồn/nhập (%)': [
                f"{(vttb_data['kho']['ton_hcsk']/vttb_data['kho']['nhap_hcsk']*100):.1f}%",
                f"{(vttb_data['kho']['ton_lktm']/vttb_data['kho']['nhap_lktm']*100):.1f}%",
                f"{(tong_ton/tong_nhap*100):.1f}%"
            ]
        })
        
        st.dataframe(inventory_detail, use_container_width=True)
        
        # Thông tin phân tích
        col1, col2 = st.columns(2)
        
        with col1:
            st.info("📈 **Phân tích hiệu quả:**")
            st.write(f"• Tổng vòng quay kho: **{(tong_xuat/tong_nhap*100):.1f}%**")
            st.write(f"• Kho HCSK hiệu quả hơn: **{ty_le_hcsk:.1f}%** vs LKTM **{ty_le_lktm:.1f}%**")
            st.write(f"• Tồn kho an toàn: **{(tong_ton/1e9):.2f} tỷ VNĐ**")
        
        with col2:
            st.success("✅ **Khuyến nghị:**")
            if ty_le_hcsk > 95:
                st.write("• Kho HCSK: Hiệu quả tốt, duy trì")
            else:
                st.write("• Kho HCSK: Cần tăng tốc độ xuất kho")
            
            if ty_le_lktm > 95:
                st.write("• Kho LKTM: Hiệu quả tốt, duy trì")
            else:
                st.write("• Kho LKTM: Cần tối ưu quy trình xuất kho")
            st.write("• Theo dõi tồn kho để tránh ứ đọng")

# ==================== TAB KHOA KSKTYC ====================
with tab_ksktyc:
    st.markdown("""
    <div class="section-header">
        <h2>🩺 KHÁM SỨC KHỎE THEO YÊU CẦU</h2>
        <p>Khám sức khỏe định kỳ, cá nhân và doanh nghiệp</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Tổng quan KPIs chính
    tong_kham = ksktyc_data["kham_khong_nn"]["value"] + ksktyc_data["kham_co_nn"]["value"]
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Tổng lượt khám", f"{tong_kham:,}", "người")
    
    with col2:
        st.metric("Khám định kỳ", f"{ksktyc_data['kham_dinh_ky']['value']:,}", 
                 f"+{ksktyc_data['kham_dinh_ky']['growth']:.1f}%")
    
    with col3:
        st.metric("Khám có yếu tố NN", f"{ksktyc_data['kham_co_nn']['value']:,}", 
                 f"+{ksktyc_data['kham_co_nn']['growth']:.0f}%")
    
    with col4:
        ty_le_noi_vien = (ksktyc_data['kham_noi_vien']['value'] / tong_kham) * 100
        st.metric("Tỷ lệ nội viện", f"{ty_le_noi_vien:.1f}%", 
                 f"+{ksktyc_data['kham_noi_vien']['growth']:.1f}%")
    
    # Biểu đồ phân tích
    col1, col2 = st.columns(2)
    
    with col1:
        # Phân loại theo nguồn
        labels_nguon = ['Không có yếu tố NN', 'Có yếu tố NN', 'Lái xe']
        values_nguon = [
            ksktyc_data['kham_khong_nn']['value'],
            ksktyc_data['kham_co_nn']['value'], 
            ksktyc_data['kham_lai_xe']['value']
        ]
        
        fig_nguon = go.Figure(data=[go.Pie(
            labels=labels_nguon,
            values=values_nguon,
            hole=0.4,
            marker_colors=['#4ECDC4', '#FF6B6B', '#FFA07A']
        )])
        fig_nguon.update_layout(title="Phân loại theo yếu tố nước ngoài")
        st.plotly_chart(fig_nguon, use_container_width=True)
    
    with col2:
        # So sánh nội vs ngoại viện
        location_data = pd.DataFrame({
            'Địa điểm': ['Nội viện', 'Ngoại viện'],
            'Số lượt': [
                ksktyc_data['kham_noi_vien']['value'],
                ksktyc_data['kham_ngoai_vien']['value']
            ],
            'Tăng trưởng': [
                ksktyc_data['kham_noi_vien']['growth'],
                ksktyc_data['kham_ngoai_vien']['growth']
            ]
        })
        
        fig_location = px.bar(location_data, x='Địa điểm', y='Số lượt',
                             title="So sánh nội viện vs ngoại viện",
                             color='Tăng trưởng',
                             color_continuous_scale='RdYlGn',
                             text='Số lượt')
        fig_location.update_traces(texttemplate='%{text:,}', textposition='outside')
        st.plotly_chart(fig_location, use_container_width=True)
    
    # Biểu đồ tăng trưởng
    st.subheader("📈 Tăng Trưởng So Với Cùng Kỳ")
    
    growth_data = pd.DataFrame({
        'Loại khám': [
            'Không có NN', 'Có NN', 'Định kỳ', 'Hợp đồng', 
            'Không hợp đồng', 'Cá nhân', 'Nội viện', 'Ngoại viện'
        ],
        'Tăng trưởng (%)': [
            ksktyc_data['kham_khong_nn']['growth'],
            ksktyc_data['kham_co_nn']['growth'],
            ksktyc_data['kham_dinh_ky']['growth'],
            ksktyc_data['kham_hop_dong']['growth'],
            ksktyc_data['kham_khong_hop_dong']['growth'],
            ksktyc_data['kham_ca_nhan']['growth'],
            ksktyc_data['kham_noi_vien']['growth'],
            ksktyc_data['kham_ngoai_vien']['growth']
        ]
    })
    
    fig_growth = px.bar(growth_data, x='Loại khám', y='Tăng trưởng (%)',
                       title="Tăng trưởng theo loại khám sức khỏe",
                       color='Tăng trưởng (%)',
                       color_continuous_scale='RdYlGn')
    fig_growth.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig_growth, use_container_width=True)
    
    # Bảng chi tiết
    st.subheader("📋 Bảng Chi Tiết Khám Sức Khỏe")
    
    detail_data = pd.DataFrame({
        'STT': [1, 2, 3, 4, 5, 6, 7, 8, 9],
        'Nội dung': [
            'Khám KHÔNG có yếu tố nước ngoài',
            'Khám CÓ yếu tố nước ngoài', 
            'Khám sức khỏe lái xe',
            'Khám sức khỏe định kỳ',
            'Khám theo hợp đồng',
            'Khám không hợp đồng',
            'Khám cá nhân',
            'Khám nội viện',
            'Khám ngoại viện'
        ],
        'Số liệu 6 tháng 2025': [
            f"{ksktyc_data['kham_khong_nn']['value']:,}",
            f"{ksktyc_data['kham_co_nn']['value']:,}",
            f"{ksktyc_data['kham_lai_xe']['value']:,}",
            f"{ksktyc_data['kham_dinh_ky']['value']:,}",
            f"{ksktyc_data['kham_hop_dong']['value']:,}",
            f"{ksktyc_data['kham_khong_hop_dong']['value']:,}",
            f"{ksktyc_data['kham_ca_nhan']['value']:,}",
            f"{ksktyc_data['kham_noi_vien']['value']:,}",
            f"{ksktyc_data['kham_ngoai_vien']['value']:,}"
        ],
        'So sánh cùng kỳ (%)': [
            f"+{ksktyc_data['kham_khong_nn']['growth']:.2f}%",
            f"+{ksktyc_data['kham_co_nn']['growth']:.2f}%",
            "0%",
            f"+{ksktyc_data['kham_dinh_ky']['growth']:.2f}%",
            f"+{ksktyc_data['kham_hop_dong']['growth']:.2f}%",
            f"+{ksktyc_data['kham_khong_hop_dong']['growth']:.2f}%",
            f"+{ksktyc_data['kham_ca_nhan']['growth']:.2f}%",
            f"+{ksktyc_data['kham_noi_vien']['growth']:.2f}%",
            f"{ksktyc_data['kham_ngoai_vien']['growth']:.2f}%"
        ],
        'Xu hướng': [
            '📈' if ksktyc_data['kham_khong_nn']['growth'] > 0 else '📉',
            '📈' if ksktyc_data['kham_co_nn']['growth'] > 0 else '📉',
            '➖',
            '📈' if ksktyc_data['kham_dinh_ky']['growth'] > 0 else '📉',
            '📈' if ksktyc_data['kham_hop_dong']['growth'] > 0 else '📉',
            '📈' if ksktyc_data['kham_khong_hop_dong']['growth'] > 0 else '📉',
            '📈' if ksktyc_data['kham_ca_nhan']['growth'] > 0 else '📉',
            '📈' if ksktyc_data['kham_noi_vien']['growth'] > 0 else '📉',
            '📈' if ksktyc_data['kham_ngoai_vien']['growth'] > 0 else '📉'
        ]
    })
    
    st.dataframe(detail_data, use_container_width=True)
    
    # Insights
    st.subheader("💡 Phân Tích & Nhận Xét")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.success("🎉 **Điểm nổi bật:**")
        st.write("• Tăng trưởng mạnh khám có yếu tố NN (+751%)")
        st.write("• Khám không hợp đồng tăng 63.3%")
        st.write("• Khám nội viện tăng trưởng tốt (+20.2%)")
        st.write("• Tổng lượt khám đạt 27,177 người")
    
    with col2:
        st.warning("⚠️ **Cần lưu ý:**")
        st.write("• Khám ngoại viện giảm 9.97%") 
        st.write("• Khám lái xe = 0 (cần khảo sát)")
        st.write("• Tăng trưởng hợp đồng chậm (2.69%)")
        st.write("• Cần mở rộng dịch vụ ngoại viện")

# ==================== TAB PHÒNG CNTT ====================
with tab_cntt:
    st.markdown("""
    <div class="section-header">
        <h2>💻 CÔNG NGHỆ THÔNG TIN</h2>
        <p>Quản lý hạ tầng CNTT, hỗ trợ kỹ thuật và phát triển ứng dụng</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Tổng quan thiết bị
    st.subheader("🖥️ Tổng Quan Thiết Bị CNTT")
    
    # Tính tổng thiết bị
    tong_thiet_bi = sum([item["quantity"] for item in cntt_data["thiet_bi"].values()])
    
    # KPI Cards chính
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Tổng thiết bị CNTT",
            f"{tong_thiet_bi:,}",
            "thiết bị"
        )
    
    with col2:
        st.metric(
            "Máy vi tính",
            f"{cntt_data['thiet_bi']['may_vi_tinh']['quantity']:,}",
            f"{(cntt_data['thiet_bi']['may_vi_tinh']['quantity']/tong_thiet_bi*100):.1f}% tổng TB"
        )
    
    with col3:
        st.metric(
            "Tỷ lệ giải quyết yêu cầu",
            f"{cntt_data['hoat_dong']['giai_quyet_de_nghi']['value']:.1f}%",
            f"+{cntt_data['hoat_dong']['giai_quyet_de_nghi']['value'] - cntt_data['hoat_dong']['giai_quyet_de_nghi']['comparison']:.1f}%"
        )
    
    with col4:
        st.metric(
            "Đăng ký khám online",
            f"{cntt_data['hoat_dong']['dang_ky_kham_online']['value']:,}",
            f"+{cntt_data['hoat_dong']['dang_ky_kham_online']['value'] - cntt_data['hoat_dong']['dang_ky_kham_online']['comparison']:,}"
        )
    
    # Phân loại thiết bị
    st.subheader("📊 Phân Loại Thiết Bị Theo Chức Năng")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Nhóm thiết bị theo chức năng
        may_tinh_nhom = cntt_data['thiet_bi']['laptop']['quantity'] + cntt_data['thiet_bi']['may_vi_tinh']['quantity'] + cntt_data['thiet_bi']['may_tinh_bang']['quantity']
        may_in_nhom = cntt_data['thiet_bi']['may_in_laser']['quantity'] + cntt_data['thiet_bi']['may_in_mau']['quantity'] + cntt_data['thiet_bi']['may_in_ma_vach']['quantity'] + cntt_data['thiet_bi']['may_in_nhiet']['quantity'] + cntt_data['thiet_bi']['may_in_the']['quantity']
        mang_nhom = cntt_data['thiet_bi']['switch']['quantity'] + cntt_data['thiet_bi']['access_point']['quantity'] + cntt_data['thiet_bi']['router']['quantity'] + cntt_data['thiet_bi']['wifi_controller']['quantity']
        server_nhom = cntt_data['thiet_bi']['server_vat_ly']['quantity'] + cntt_data['thiet_bi']['server_ao_hoa']['quantity'] + cntt_data['thiet_bi']['san']['quantity'] + cntt_data['thiet_bi']['das']['quantity'] + cntt_data['thiet_bi']['nas']['quantity']
        
        nhom_data = pd.DataFrame({
            'Nhóm thiết bị': ['Máy tính', 'Máy in', 'Thiết bị mạng', 'Server & Storage', 'Khác'],
            'Số lượng': [
                may_tinh_nhom,
                may_in_nhom, 
                mang_nhom,
                server_nhom,
                tong_thiet_bi - may_tinh_nhom - may_in_nhom - mang_nhom - server_nhom
            ]
        })
        
        fig_nhom = px.pie(nhom_data, values='Số lượng', names='Nhóm thiết bị',
                         title="Phân bổ thiết bị theo nhóm chức năng",
                         color_discrete_sequence=['#4ECDC4', '#FF6B6B', '#FFA500', '#32CD32', '#DA70D6'])
        fig_nhom.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_nhom, use_container_width=True)
    
    with col2:
        # Top 10 thiết bị nhiều nhất
        thiet_bi_list = [(item["name"], item["quantity"]) for item in cntt_data["thiet_bi"].values()]
        thiet_bi_list.sort(key=lambda x: x[1], reverse=True)
        top_10 = thiet_bi_list[:10]
        
        top_10_df = pd.DataFrame(top_10, columns=['Thiết bị', 'Số lượng'])
        
        fig_top10 = px.bar(top_10_df, x='Số lượng', y='Thiết bị',
                          title="Top 10 thiết bị nhiều nhất", 
                          orientation='h',
                          color='Số lượng',
                          color_continuous_scale='Blues')
        fig_top10.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_top10, use_container_width=True)
    
    # Hoạt động hỗ trợ
    st.subheader("🛠️ Hoạt Động Hỗ Trợ & Phát Triển")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Hỗ trợ phần cứng",
            f"{cntt_data['hoat_dong']['ho_tro_phan_cung']['value']:,}",
            f"{cntt_data['hoat_dong']['ho_tro_phan_cung']['value'] - cntt_data['hoat_dong']['ho_tro_phan_cung']['comparison']:+,} lượt"
        )
    
    with col2:
        st.metric(
            "Hỗ trợ phần mềm",
            f"{cntt_data['hoat_dong']['ho_tro_phan_mem']['value']:,}",
            f"{cntt_data['hoat_dong']['ho_tro_phan_mem']['value'] - cntt_data['hoat_dong']['ho_tro_phan_mem']['comparison']:+,} lượt"
        )
    
    with col3:
        st.metric(
            "Chức năng mới",
            f"{cntt_data['hoat_dong']['trien_khai_chuc_nang']['value']}",
            f"{cntt_data['hoat_dong']['trien_khai_chuc_nang']['value'] - cntt_data['hoat_dong']['trien_khai_chuc_nang']['comparison']:+,} chức năng"
        )
    
    with col4:
        st.metric(
            "Tham quan CNTT",
            f"{cntt_data['hoat_dong']['tham_quan']['value']}",
            f"{cntt_data['hoat_dong']['tham_quan']['value'] - cntt_data['hoat_dong']['tham_quan']['comparison']:+,} đoàn"
        )
    
    # Biểu đồ so sánh hiệu suất
    col1, col2 = st.columns(2)
    
    with col1:
        # So sánh hoạt động 2 kỳ
        hoat_dong_comparison = []
        for key, item in cntt_data['hoat_dong'].items():
            hoat_dong_comparison.append({
                'Hoạt động': item['name'][:20] + '...' if len(item['name']) > 20 else item['name'],
                'Kỳ hiện tại': item['value'],
                'Kỳ trước': item['comparison'],
                'Đơn vị': item['unit']
            })
        
        comparison_df = pd.DataFrame(hoat_dong_comparison)
        
        # Chỉ hiển thị 5 hoạt động chính
        comparison_df_main = comparison_df.head(4)
        
        fig_comparison = px.bar(comparison_df_main, x='Hoạt động', y=['Kỳ hiện tại', 'Kỳ trước'],
                               title="So sánh hiệu suất các hoạt động",
                               barmode='group',
                               color_discrete_sequence=['#4ECDC4', '#FF6B6B'])
        fig_comparison.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_comparison, use_container_width=True)
    
    with col2:
        # Mức độ tăng trưởng
        growth_data = []
        for key, item in cntt_data['hoat_dong'].items():
            if item['comparison'] > 0:
                growth_rate = ((item['value'] - item['comparison']) / item['comparison']) * 100
                growth_data.append({
                    'Hoạt động': item['name'][:15] + '...' if len(item['name']) > 15 else item['name'],
                    'Tăng trưởng (%)': growth_rate
                })
        
        growth_df = pd.DataFrame(growth_data)
        
        fig_growth = px.bar(growth_df, x='Hoạt động', y='Tăng trưởng (%)',
                           title="Tăng trưởng các hoạt động (%)",
                           color='Tăng trưởng (%)',
                           color_continuous_scale='RdYlGn')
        fig_growth.update_layout(xaxis_tickangle=-45)
        fig_growth.add_hline(y=0, line_dash="dash", line_color="black")
        st.plotly_chart(fig_growth, use_container_width=True)
    
    # Bảng chi tiết thiết bị
    st.subheader("📋 Bảng Chi Tiết Thiết Bị CNTT")
    
    # Tạo DataFrame cho thiết bị
    thiet_bi_detail = []
    for i, (key, item) in enumerate(cntt_data["thiet_bi"].items(), 1):
        thiet_bi_detail.append({
            'STT': i,
            'Tên thiết bị': item["name"],
            'Số lượng': item["quantity"],
            'Tỷ lệ (%)': f"{(item['quantity']/tong_thiet_bi*100):.1f}%",
            'Trạng thái': '✅ Hoạt động' if item["quantity"] > 0 else '❌ Không có'
        })
    
    thiet_bi_df = pd.DataFrame(thiet_bi_detail)
    st.dataframe(thiet_bi_df, use_container_width=True)
    
    # Bảng hoạt động
    st.subheader("📊 Bảng Hoạt Động & Hỗ Trợ")
    
    hoat_dong_detail = []
    for i, (key, item) in enumerate(cntt_data["hoat_dong"].items(), 1):
        if item['comparison'] > 0:
            change = item['value'] - item['comparison']
            change_percent = (change / item['comparison']) * 100
            change_text = f"{change:+,} ({change_percent:+.1f}%)"
        else:
            change_text = "N/A"
            
        hoat_dong_detail.append({
            'STT': i,
            'Hoạt động': item["name"],
            'Kỳ hiện tại': f"{item['value']:,} {item['unit']}",
            'Kỳ trước': f"{item['comparison']:,} {item['unit']}" if item['comparison'] > 0 else "N/A",
            'Thay đổi': change_text,
            'Xu hướng': '📈' if item['value'] > item['comparison'] else '📉' if item['value'] < item['comparison'] else '➖'
        })
    
    hoat_dong_df = pd.DataFrame(hoat_dong_detail)
    st.dataframe(hoat_dong_df, use_container_width=True)
    
    # Insights
    st.subheader("💡 Phân Tích & Đánh Giá")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.success("🎉 **Thành tựu nổi bật:**")
        st.write("• Tổng thiết bị CNTT: **4,796 thiết bị**")
        st.write("• Tỷ lệ giải quyết yêu cầu: **97.16%**")
        st.write("• Đăng ký khám online tăng mạnh: **+209%**")
        st.write("• Triển khai 87 chức năng phần mềm mới")
        st.write("• Hỗ trợ kỹ thuật: **5,352 lượt**")
    
    with col2:
        st.info("🎯 **Kế hoạch phát triển:**")
        st.write("• Nâng cấp hạ tầng server và storage")
        st.write("• Tăng cường bảo mật với firewall")
        st.write("• Phát triển thêm tính năng UMC Care")
        st.write("• Mở rộng hệ thống wifi toàn viện")
        st.write("• Đào tạo nhân viên sử dụng CNTT")

# ==================== TAB PHÒNG CTXH ====================
with tab_ctxh:
    st.markdown("""
    <div class="section-header">
        <h2>🤝 CÔNG TÁC XÃ HỘI</h2>
        <p>Hỗ trợ người bệnh, chăm sóc cộng đồng và vận động tài trợ</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Tổng quan KPIs chính
    st.subheader("📊 Tổng Quan Hoạt Động CTXH")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Tư vấn nhập viện",
            f"{ctxh_data['ho_tro_nguoi_benh']['tu_van_nhap_vien']['value']:,}",
            f"vs cùng kỳ: {ctxh_data['ho_tro_nguoi_benh']['tu_van_nhap_vien']['comparison']:.1f}%"
        )
    
    with col2:
        st.metric(
            "Hỗ trợ khó khăn",
            f"{ctxh_data['ho_tro_nguoi_benh']['kinh_phi_ho_tro']['value']/1e9:.1f} tỷ VNĐ",
            f"Tăng {ctxh_data['ho_tro_nguoi_benh']['kinh_phi_ho_tro']['comparison']:.0f}%"
        )
    
    with col3:
        st.metric(
            "Sự hài lòng nội trú",
            f"{ctxh_data['ho_tro_nguoi_benh']['hai_long_noi_tru']['value']:.1f}%",
            f"{ctxh_data['ho_tro_nguoi_benh']['hai_long_noi_tru']['comparison']:.1f}%"
        )
    
    with col4:
        st.metric(
            "Chăm sóc cộng đồng",
            f"{ctxh_data['cham_soc_cong_dong']['luot_dan']['value']:,} người",
            f"+{ctxh_data['cham_soc_cong_dong']['luot_dan']['comparison']:.0f}%"
        )
    
    # Tab con cho từng mảng hoạt động
    subtab1, subtab2, subtab3, subtab4 = st.tabs([
        "👥 Hỗ Trợ Người Bệnh",
        "🏥 Sinh Hoạt & Tư Vấn", 
        "🌍 Chăm Sóc Cộng Đồng",
        "💰 Tài Trợ & Góp Ý"
    ])
    
    # Tab Hỗ trợ người bệnh
    with subtab1:
        st.header("👥 Hỗ Trợ Người Bệnh")
        
        # Metrics hỗ trợ
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Tư vấn xuất viện",
                f"{ctxh_data['ho_tro_nguoi_benh']['tu_van_xuat_vien']['value']:,}",
                f"{ctxh_data['ho_tro_nguoi_benh']['tu_van_xuat_vien']['comparison']:.1f}% vs cùng kỳ"
            )
        
        with col2:
            st.metric(
                "Cài đặt UMC Care",
                f"{ctxh_data['ho_tro_nguoi_benh']['cai_dat_app']['value']:,}",
                f"+{ctxh_data['ho_tro_nguoi_benh']['cai_dat_app']['comparison']:.0f}%"
            )
        
        with col3:
            st.metric(
                "Tin nhắn tái khám",
                f"{ctxh_data['ho_tro_nguoi_benh']['tin_nhan_tai_kham']['value']:,}",
                f"+{ctxh_data['ho_tro_nguoi_benh']['tin_nhan_tai_kham']['comparison']:.1f}%"
            )
        
        # Biểu đồ hoạt động hỗ trợ
        col1, col2 = st.columns(2)
        
        with col1:
            # Biểu đồ các hoạt động tư vấn
            tu_van_data = pd.DataFrame({
                'Hoạt động': ['Tư vấn nhập viện', 'Tư vấn xuất viện', 'Gọi điện hỏi thăm', 'Tin nhắn tái khám'],
                'Số lượng': [
                    ctxh_data['ho_tro_nguoi_benh']['tu_van_nhap_vien']['value'],
                    ctxh_data['ho_tro_nguoi_benh']['tu_van_xuat_vien']['value'],
                    ctxh_data['ho_tro_nguoi_benh']['goi_dien_thoai']['value'],
                    ctxh_data['ho_tro_nguoi_benh']['tin_nhan_tai_kham']['value']
                ]
            })
            
            fig_tu_van = px.bar(tu_van_data, x='Hoạt động', y='Số lượng',
                               title="Hoạt động tư vấn & hỗ trợ",
                               color='Số lượng',
                               color_continuous_scale='Blues')
            fig_tu_van.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_tu_van, use_container_width=True)
        
        with col2:
            # Biểu đồ hỗ trợ khó khăn
            ho_tro_data = pd.DataFrame({
                'Loại hỗ trợ': ['Người được hỗ trợ', 'Hỗ trợ tâm lý', 'Chương trình'],
                'Số lượng': [
                    ctxh_data['ho_tro_nguoi_benh']['ho_tro_kho_khan']['value'],
                    ctxh_data['ho_tro_nguoi_benh']['ho_tro_tam_ly']['value'],
                    ctxh_data['ho_tro_nguoi_benh']['chuong_trinh_ho_tro']['value']
                ]
            })
            
            fig_ho_tro = px.pie(ho_tro_data, values='Số lượng', names='Loại hỗ trợ',
                               title="Phân bổ hoạt động hỗ trợ",
                               color_discrete_sequence=['#FF6B6B', '#4ECDC4', '#FFA500'])
            st.plotly_chart(fig_ho_tro, use_container_width=True)
        
        # Bảng chi tiết hỗ trợ người bệnh
        st.subheader("📋 Chi Tiết Hỗ Trợ Người Bệnh")
        
        ho_tro_detail = pd.DataFrame({
            'STT': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            'Nội dung': [
                'Tư vấn nhập viện',
                'Tư vấn xuất viện', 
                'Gọi điện hỏi thăm sau xuất viện',
                'Tin nhắn nhắc tái khám',
                'Cài đặt app UMC Care',
                'Hỗ trợ người bệnh khó khăn',
                'Kinh phí hỗ trợ khó khăn',
                'Hỗ trợ tâm lý xã hội',
                'Chương trình hỗ trợ',
                'Sự hài lòng nội trú'
            ],
            'Kết quả 6 tháng': [
                f"{ctxh_data['ho_tro_nguoi_benh']['tu_van_nhap_vien']['value']:,} trường hợp",
                f"{ctxh_data['ho_tro_nguoi_benh']['tu_van_xuat_vien']['value']:,} trường hợp",
                f"{ctxh_data['ho_tro_nguoi_benh']['goi_dien_thoai']['value']:,} cuộc gọi",
                f"{ctxh_data['ho_tro_nguoi_benh']['tin_nhan_tai_kham']['value']:,} tin nhắn",
                f"{ctxh_data['ho_tro_nguoi_benh']['cai_dat_app']['value']:,} lượt",
                f"{ctxh_data['ho_tro_nguoi_benh']['ho_tro_kho_khan']['value']:,} lượt người",
                f"{ctxh_data['ho_tro_nguoi_benh']['kinh_phi_ho_tro']['value']/1e9:.1f} tỷ VNĐ",
                f"{ctxh_data['ho_tro_nguoi_benh']['ho_tro_tam_ly']['value']:,} lượt người",
                f"{ctxh_data['ho_tro_nguoi_benh']['chuong_trinh_ho_tro']['value']:,} chương trình",
                f"{ctxh_data['ho_tro_nguoi_benh']['hai_long_noi_tru']['value']:.1f}%"
            ],
            'So sánh cùng kỳ (%)': [
                f"{ctxh_data['ho_tro_nguoi_benh']['tu_van_nhap_vien']['comparison']:.1f}%",
                f"{ctxh_data['ho_tro_nguoi_benh']['tu_van_xuat_vien']['comparison']:.1f}%",
                f"{ctxh_data['ho_tro_nguoi_benh']['goi_dien_thoai']['comparison']:.0f}%",
                f"{ctxh_data['ho_tro_nguoi_benh']['tin_nhan_tai_kham']['comparison']:.1f}%",
                f"{ctxh_data['ho_tro_nguoi_benh']['cai_dat_app']['comparison']:.0f}%",
                f"{ctxh_data['ho_tro_nguoi_benh']['ho_tro_kho_khan']['comparison']:.0f}%",
                f"{ctxh_data['ho_tro_nguoi_benh']['kinh_phi_ho_tro']['comparison']:.0f}%",
                f"{ctxh_data['ho_tro_nguoi_benh']['ho_tro_tam_ly']['comparison']:.0f}%",
                f"{ctxh_data['ho_tro_nguoi_benh']['chuong_trinh_ho_tro']['comparison']:.1f}%",
                f"{ctxh_data['ho_tro_nguoi_benh']['hai_long_noi_tru']['comparison']:.1f}%"
            ]
        })
        
        st.dataframe(ho_tro_detail, use_container_width=True)
    
    # Tab Sinh hoạt & Tư vấn
    with subtab2:
        st.header("🏥 Sinh Hoạt Người Nhà & Tư Vấn")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Sinh hoạt Cấp cứu",
                f"{ctxh_data['sinh_hoat_nha']['lan_sinh_hoat_cc']['value']} lần",
                f"{ctxh_data['sinh_hoat_nha']['nguoi_tham_du_cc']['value']:,} người tham dự"
            )
        
        with col2:
            st.metric(
                "Sinh hoạt GMHS",
                f"{ctxh_data['sinh_hoat_nha']['lan_sinh_hoat_gmhs']['value']} lần",
                f"{ctxh_data['sinh_hoat_nha']['nguoi_tham_du_gmhs']['value']:,} người tham dự"
            )
        
        with col3:
            st.metric(
                "Video call với nhà",
                f"{ctxh_data['sinh_hoat_nha']['videocall']['value']:,}",
                f"{ctxh_data['sinh_hoat_nha']['videocall']['comparison']:.0f}% vs cùng kỳ"
            )
        
        # Biểu đồ sinh hoạt
        col1, col2 = st.columns(2)
        
        with col1:
            sinh_hoat_data = pd.DataFrame({
                'Khoa': ['Cấp cứu', 'GMHS'],
                'Số lần sinh hoạt': [
                    ctxh_data['sinh_hoat_nha']['lan_sinh_hoat_cc']['value'],
                    ctxh_data['sinh_hoat_nha']['lan_sinh_hoat_gmhs']['value']
                ],
                'Người tham dự': [
                    ctxh_data['sinh_hoat_nha']['nguoi_tham_du_cc']['value'],
                    ctxh_data['sinh_hoat_nha']['nguoi_tham_du_gmhs']['value']
                ]
            })
            
            fig_sinh_hoat = px.bar(sinh_hoat_data, x='Khoa', y=['Số lần sinh hoạt', 'Người tham dự'],
                                  title="Sinh hoạt người nhà theo khoa",
                                  barmode='group')
            st.plotly_chart(fig_sinh_hoat, use_container_width=True)
        
        with col2:
            # Chương trình hỗ trợ thuốc
            thuoc_data = pd.DataFrame({
                'Chỉ số': ['Chương trình', 'Người tham gia', 'Tài trợ (tỷ VNĐ)'],
                'Giá trị': [
                    ctxh_data['ho_tro_thuoc']['so_chuong_trinh']['value'],
                    ctxh_data['ho_tro_thuoc']['nguoi_benh_tham_gia']['value'],
                    ctxh_data['ho_tro_thuoc']['tien_tai_tro']['value'] / 1e9
                ]
            })
            
            fig_thuoc = px.bar(thuoc_data, x='Chỉ số', y='Giá trị',
                              title="Chương trình hỗ trợ thuốc miễn phí",
                              color='Giá trị',
                              color_continuous_scale='Greens')
            st.plotly_chart(fig_thuoc, use_container_width=True)
    
    # Tab Chăm sóc cộng đồng
    with subtab3:
        st.header("🌍 Chăm Sóc Sức Khỏe Cộng Đồng")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Tổng kinh phí",
                f"{ctxh_data['cham_soc_cong_dong']['tong_kinh_phi']['value']/1e9:.1f} tỷ VNĐ",
                f"{ctxh_data['cham_soc_cong_dong']['tong_kinh_phi']['comparison']:.0f}% vs cùng kỳ"
            )
        
        with col2:
            st.metric(
                "Số chương trình",
                f"{ctxh_data['cham_soc_cong_dong']['so_chuong_trinh']['value']}",
                f"{ctxh_data['cham_soc_cong_dong']['so_chuong_trinh']['comparison']:.0f}% vs cùng kỳ"
            )
        
        with col3:
            st.metric(
                "Người dân được khám",
                f"{ctxh_data['cham_soc_cong_dong']['luot_dan']['value']:,}",
                f"+{ctxh_data['cham_soc_cong_dong']['luot_dan']['comparison']:.0f}%"
            )
        
        with col4:
            st.metric(
                "Nạn nhân bị ảnh hưởng bởi chất độc màu da cam",
                f"{ctxh_data['cham_soc_cong_dong']['nan_nhan_da_cam']['value']:,}",
                f"+{ctxh_data['cham_soc_cong_dong']['nan_nhan_da_cam']['comparison']:.1f}%"
            )
        
        # Biểu đồ chăm sóc cộng đồng
        col1, col2 = st.columns(2)
        
        with col1:
            # Đối tượng thưởng
            doi_tuong_data = pd.DataFrame({
                'Đối tượng': ['Mẹ VNAH & Thương binh', 'Nạn nhân da cam', 'Người dân khác'],
                'Số lượng': [
                    ctxh_data['cham_soc_cong_dong']['me_vnah_tb']['value'],
                    ctxh_data['cham_soc_cong_dong']['nan_nhan_da_cam']['value'],
                    ctxh_data['cham_soc_cong_dong']['luot_dan']['value'] - 
                    ctxh_data['cham_soc_cong_dong']['me_vnah_tb']['value'] - 
                    ctxh_data['cham_soc_cong_dong']['nan_nhan_da_cam']['value']
                ]
            })
            
            fig_doi_tuong = px.pie(doi_tuong_data, values='Số lượng', names='Đối tượng',
                                  title="Đối tượng chăm sóc cộng đồng",
                                  color_discrete_sequence=['#FF6B6B', '#4ECDC4', '#FFA500'])
            st.plotly_chart(fig_doi_tuong, use_container_width=True)
        
        with col2:
            # Quà tặng
            qua_tang_data = pd.DataFrame({
                'Loại quà': ['Xe đạp', 'Công trình'],
                'Số lượng': [
                    ctxh_data['cham_soc_cong_dong']['tang_xe_dap']['value'],
                    ctxh_data['cham_soc_cong_dong']['cong_trinh']['value']
                ]
            })
            
            fig_qua_tang = px.bar(qua_tang_data, x='Loại quà', y='Số lượng',
                                 title="Quà tặng cho cộng đồng",
                                 color='Số lượng',
                                 color_continuous_scale='Oranges')
            st.plotly_chart(fig_qua_tang, use_container_width=True)
    
    # Tab Tài trợ & Góp ý
    with subtab4:
        st.header("💰 Vận Động Tài Trợ & Tiếp Nhận Góp Ý")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Vận động tài trợ",
                f"{ctxh_data['van_dong_tai_tro']['so_tien']['value']:.1f} tỷ VNĐ",
                f"+{ctxh_data['van_dong_tai_tro']['so_tien']['comparison']:.1f}%"
            )
        
        with col2:
            st.metric(
                "Thư khen",
                f"{ctxh_data['tiep_nhan_gop_y']['thu_khen']['value']}",
                f"{ctxh_data['tiep_nhan_gop_y']['thu_khen']['comparison']:.0f}% vs cùng kỳ"
            )
        
        with col3:
            st.metric(
                "Thư góp ý",
                f"{ctxh_data['tiep_nhan_gop_y']['thu_gop_y']['value']}",
                f"+{ctxh_data['tiep_nhan_gop_y']['thu_gop_y']['comparison']:.0f}%"
            )
        
        with col4:
            st.metric(
                "Đường dây nóng GĐ",
                f"{ctxh_data['tiep_nhan_gop_y']['duong_day_gd']['value']}",
                f"{ctxh_data['tiep_nhan_gop_y']['duong_day_gd']['comparison']:.1f}% vs cùng kỳ"
            )
        
        # Biểu đồ feedback
        feedback_data = pd.DataFrame({
            'Loại phản hồi': ['Thư khen', 'Thư góp ý', 'Đường dây GĐ', 'Đường dây BYT'],
            'Số lượng': [
                ctxh_data['tiep_nhan_gop_y']['thu_khen']['value'],
                ctxh_data['tiep_nhan_gop_y']['thu_gop_y']['value'],
                ctxh_data['tiep_nhan_gop_y']['duong_day_gd']['value'],
                ctxh_data['tiep_nhan_gop_y']['duong_day_byt']['value']
            ]
        })
        
        fig_feedback = px.bar(feedback_data, x='Loại phản hồi', y='Số lượng',
                             title="Phản hồi từ người bệnh và cộng đồng",
                             color='Số lượng',
                             color_continuous_scale='Reds')
        st.plotly_chart(fig_feedback, use_container_width=True)
    
    # Tổng kết và insights
    st.subheader("💡 Tổng Kết & Đánh Giá")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.success("🎉 **Thành tựu nổi bật:**")
        st.write("• Tư vấn nhập/xuất viện: **47,772 trường hợp**")
        st.write("• Hỗ trợ khó khăn: **8.6 tỷ VNĐ** (+295%)")
        st.write("• Hài lòng nội trú: **99.2%** (xuất sắc)")
        st.write("• Chăm sóc cộng đồng: **4,062 người dân**")
        st.write("• Hỗ trợ thuốc miễn phí: **57.9 tỷ VNĐ**")
        st.write("• Video call gia đình: **5,719 cuộc gọi**")
    
    with col2:
        st.info("🎯 **Kế hoạch phát triển:**")
        st.write("• Mở rộng chương trình hỗ trợ khó khăn")
        st.write("• Tăng cường sinh hoạt người nhà")
        st.write("• Phát triển ứng dụng UMC Care")
        st.write("• Mở rộng chăm sóc cộng đồng")
        st.write("• Vận động thêm nguồn tài trợ")
        st.write("• Cải thiện dịch vụ tư vấn tâm lý")

# ==================== TAB TRUNG TÂM TRUYỀN THÔNG ====================
with tab_tttt:
    st.markdown("""
    <div class="section-header">
        <h2>📱 HOẠT ĐỘNG TRUYỀN THÔNG</h2>
        <p>Truyền thông đa kênh - Nâng cao hình ảnh bệnh viện</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Tổng quan KPIs chính
    st.subheader("📊 Tổng Quan Hoạt Động Truyền Thông")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Tổng lượt tiếp cận",
            f"{(tttt_data['website']['luot_truy_cap_2025'] + tttt_data['fanpage']['luot_thich_2025'] + tttt_data['youtube']['luot_dang_ky_2025'])/1e6:.1f}M",
            "Đa nền tảng"
        )
    
    with col2:
        st.metric(
            "Bài viết/Video",
            f"{tttt_data['bai_viet_truyen_thong']['2025']:,}",
            f"{tttt_data['bai_viet_truyen_thong']['growth']:.0f}%"
        )
    
    with col3:
        st.metric(
            "Website truy cập",
            f"{tttt_data['website']['luot_truy_cap_2025']/1e6:.1f}M",
            f"+{tttt_data['website']['luot_truy_cap_growth']:.1f}%"
        )
    
    with col4:
        st.metric(
            "Ấn phẩm phát hành",
            f"{tttt_data['an_pham']['so_luong_2025']:,}",
            "Tờ/Quyển"
        )
    
    # Sub-tabs cho từng mảng hoạt động
    subtab1, subtab2, subtab3, subtab4 = st.tabs([
        "📊 Tổng Quan", "📰 Báo Chí & Truyền Thông", "🌐 Digital Marketing", "📚 Ấn Phẩm & Giáo Dục"
    ])
    
    # Tab Tổng quan
    with subtab1:
        st.header("📊 Tổng Quan Hoạt Động Truyền Thông")
        
        # Biểu đồ tổng quan các kênh
        col1, col2 = st.columns(2)
        
        with col1:
            # Biểu đồ so sánh lượt tiếp cận các kênh
            channels_data = pd.DataFrame({
                'Kênh': ['Website', 'Facebook', 'YouTube', 'Zalo', 'TikTok'],
                'Lượt tiếp cận 2025': [
                    tttt_data['website']['luot_truy_cap_2025'],
                    tttt_data['fanpage']['luot_thich_2025'],
                    tttt_data['youtube']['luot_dang_ky_2025'],
                    tttt_data['zalo']['luot_quan_tam_2025'],
                    tttt_data['tiktok']['luot_dang_ky_2025']
                ],
                'Lượt tiếp cận 2024': [
                    tttt_data['website']['luot_truy_cap_2024'],
                    tttt_data['fanpage']['luot_thich_2024'],
                    tttt_data['youtube']['luot_dang_ky_2024'],
                    tttt_data['zalo']['luot_quan_tam_2024'],
                    tttt_data['tiktok']['luot_dang_ky_2024']
                ]
            })
            
            # Chuyển đổi sang dạng log scale cho dễ nhìn
            fig_channels = px.bar(channels_data, x='Kênh', y=['Lượt tiếp cận 2025', 'Lượt tiếp cận 2024'],
                                 title="So sánh lượt tiếp cận các kênh truyền thông",
                                 barmode='group',
                                 color_discrete_sequence=['#00D4FF', '#090979'])
            fig_channels.update_yaxes(type="log", title="Lượt tiếp cận (log scale)")
            st.plotly_chart(fig_channels, use_container_width=True)
        
        with col2:
            # Biểu đồ tăng trưởng các kênh
            growth_data = pd.DataFrame({
                'Kênh': ['Website', 'Facebook', 'YouTube', 'Zalo', 'TikTok'],
                'Tăng trưởng (%)': [
                    tttt_data['website']['luot_truy_cap_growth'],
                    tttt_data['fanpage']['luot_thich_growth'],
                    tttt_data['youtube']['luot_dang_ky_growth'],
                    tttt_data['zalo']['luot_quan_tam_growth'],
                    100  # TikTok mới nên tính là 100%
                ]
            })
            
            fig_growth = px.bar(growth_data, x='Kênh', y='Tăng trưởng (%)',
                               title="Tăng trưởng các kênh truyền thông",
                               color='Tăng trưởng (%)',
                               color_continuous_scale='RdYlGn')
            fig_growth.add_hline(y=0, line_dash="dash", line_color="gray")
            st.plotly_chart(fig_growth, use_container_width=True)
        
        # Số lượng nội dung sản xuất
        st.subheader("📝 Sản Xuất Nội Dung")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Pie chart phân bổ nội dung
            content_data = pd.DataFrame({
                'Loại nội dung': ['Bài viết Web', 'Bài Facebook', 'Video YouTube', 'Bài Zalo', 'Video TikTok'],
                'Số lượng': [
                    tttt_data['website']['bai_viet_2025'],
                    tttt_data['fanpage']['bai_viet_2025'],
                    tttt_data['youtube']['video_2025'],
                    tttt_data['zalo']['bai_viet_2025'],
                    tttt_data['tiktok']['video_2025']
                ]
            })
            
            fig_content = px.pie(content_data, values='Số lượng', names='Loại nội dung',
                                title="Phân bổ nội dung theo kênh",
                                color_discrete_sequence=px.colors.sequential.Blues)
            st.plotly_chart(fig_content, use_container_width=True)
        
        with col2:
            # Xu hướng sản xuất nội dung
            trend_data = pd.DataFrame({
                'Tháng': ['T1', 'T2', 'T3', 'T4', 'T5', 'T6'],
                'Bài viết': [120, 135, 140, 138, 142, 147],
                'Video': [25, 28, 30, 32, 31, 35],
                'Chương trình': [30, 32, 35, 33, 36, 38]
            })
            
            fig_trend = px.line(trend_data, x='Tháng', y=['Bài viết', 'Video', 'Chương trình'],
                               title="Xu hướng sản xuất nội dung 6 tháng",
                               markers=True)
            st.plotly_chart(fig_trend, use_container_width=True)
    
    # Tab Báo chí & Truyền thông
    with subtab2:
        st.header("📰 Báo Chí & Truyền Thông Đại Chúng")
        
        # Metrics báo chí
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Bài viết/Video",
                f"{tttt_data['bai_viet_truyen_thong']['2025']:,}",
                f"{tttt_data['bai_viet_truyen_thong']['growth']:.0f}%"
            )
        
        with col2:
            st.metric(
                "Chương trình TV/Radio",
                f"{tttt_data['chuong_trinh_phong_su']['2025']}",
                f"{tttt_data['chuong_trinh_phong_su']['growth']:.0f}%"
            )
        
        with col3:
            st.metric(
                "Chương trình giáo dục SK",
                f"{tttt_data['chuong_trinh_giao_duc']['2025']}",
                f"{tttt_data['chuong_trinh_giao_duc']['growth']:.0f}%"
            )
        
        with col4:
            tong_chuong_trinh = tttt_data['chuong_trinh_phong_su']['2025'] + tttt_data['chuong_trinh_giao_duc']['2025']
            st.metric(
                "Tổng chương trình",
                f"{tong_chuong_trinh}",
                "chương trình"
            )
        
        # Biểu đồ phân tích
        col1, col2 = st.columns(2)
        
        with col1:
            # So sánh 2 kỳ
            media_comparison = pd.DataFrame({
                'Loại': ['Bài viết/Video', 'Phóng sự/Phỏng vấn', 'Giáo dục sức khỏe'],
                '6 tháng 2024': [
                    tttt_data['bai_viet_truyen_thong']['2024'],
                    tttt_data['chuong_trinh_phong_su']['2024'],
                    tttt_data['chuong_trinh_giao_duc']['2024']
                ],
                '6 tháng 2025': [
                    tttt_data['bai_viet_truyen_thong']['2025'],
                    tttt_data['chuong_trinh_phong_su']['2025'],
                    tttt_data['chuong_trinh_giao_duc']['2025']
                ]
            })
            
            fig_media = px.bar(media_comparison, x='Loại', y=['6 tháng 2024', '6 tháng 2025'],
                              title="So sánh hoạt động báo chí 2 kỳ",
                              barmode='group',
                              color_discrete_sequence=['#FF6B6B', '#00D4FF'])
            st.plotly_chart(fig_media, use_container_width=True)
        
        with col2:
            # Phân tích giảm sút
            decline_data = pd.DataFrame({
                'Hoạt động': ['Bài viết/Video', 'Phóng sự/PV', 'Giáo dục SK'],
                'Mức giảm (%)': [32, 48, 60]
            })
            
            fig_decline = px.bar(decline_data, x='Hoạt động', y='Mức giảm (%)',
                                title="Mức độ suy giảm hoạt động báo chí",
                                color='Mức giảm (%)',
                                color_continuous_scale='Reds')
            fig_decline.update_traces(marker_color=['#FFA07A', '#FF6B6B', '#DC143C'])
            st.plotly_chart(fig_decline, use_container_width=True)
        
        # Phân tích nguyên nhân
        st.warning("⚠️ **Phân tích suy giảm hoạt động báo chí:**")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Nguyên nhân có thể:**")
            st.write("• Chuyển dịch sang truyền thông số")
            st.write("• Tối ưu chất lượng thay vì số lượng")
            st.write("• Thay đổi chiến lược truyền thông")
            st.write("• Tập trung vào kênh sở hữu (owned media)")
        
        with col2:
            st.write("**Khuyến nghị:**")
            st.write("• Cân bằng giữa báo chí và digital")
            st.write("• Tăng cường quan hệ báo chí")
            st.write("• Đa dạng hóa nội dung")
            st.write("• Theo dõi hiệu quả truyền thông")
    
    # Tab Digital Marketing
    with subtab3:
        st.header("🌐 Digital Marketing & Social Media")
        
        # Website metrics
        st.subheader("🌍 Website")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Lượt truy cập", f"{tttt_data['website']['luot_truy_cap_2025']/1e6:.1f}M", 
                     f"+{tttt_data['website']['luot_truy_cap_growth']:.1f}%")
        
        with col2:
            st.metric("Bài viết", f"{tttt_data['website']['bai_viet_2025']}", 
                     f"+{tttt_data['website']['bai_viet_growth']:.0f}%")
        
        with col3:
            avg_daily = tttt_data['website']['luot_truy_cap_2025'] / 180
            st.metric("TB lượt/ngày", f"{avg_daily:,.0f}", "lượt")
        
        with col4:
            views_per_article = tttt_data['website']['luot_truy_cap_2025'] / tttt_data['website']['bai_viet_2025']
            st.metric("Lượt xem/bài", f"{views_per_article:,.0f}", "lượt")
        
        # Social Media Performance
        st.subheader("📱 Social Media Performance")
        
        # Tạo dataframe cho social metrics
        social_data = pd.DataFrame({
            'Platform': ['Facebook', 'YouTube', 'Zalo', 'TikTok'],
            'Followers 2025': [
                tttt_data['fanpage']['luot_thich_2025'],
                tttt_data['youtube']['luot_dang_ky_2025'],
                tttt_data['zalo']['luot_quan_tam_2025'],
                tttt_data['tiktok']['luot_dang_ky_2025']
            ],
            'Growth (%)': [
                tttt_data['fanpage']['luot_thich_growth'],
                tttt_data['youtube']['luot_dang_ky_growth'],
                tttt_data['zalo']['luot_quan_tam_growth'],
                100
            ],
            'Content 2025': [
                tttt_data['fanpage']['bai_viet_2025'],
                tttt_data['youtube']['video_2025'],
                tttt_data['zalo']['bai_viet_2025'],
                tttt_data['tiktok']['video_2025']
            ]
        })
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Biểu đồ followers
            fig_followers = px.bar(social_data, x='Platform', y='Followers 2025',
                                  title="Followers/Subscribers theo platform",
                                  color='Growth (%)',
                                  color_continuous_scale='Viridis',
                                  text='Followers 2025')
            fig_followers.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            st.plotly_chart(fig_followers, use_container_width=True)
        
        with col2:
            # Engagement metrics
            engagement_data = pd.DataFrame({
                'Metric': ['FB Hỏi-Đáp', 'FB Engagement Rate', 'YouTube Views/Video', 'Zalo Open Rate'],
                'Value': [
                    tttt_data['fanpage']['hoi_dap_2025'],
                    (tttt_data['fanpage']['hoi_dap_2025'] / tttt_data['fanpage']['luot_thich_2025']) * 100,
                    15000,  # Giả định
                    85  # Giả định
                ],
                'Unit': ['tin nhắn', '%', 'views', '%']
            })
            
            fig_engagement = px.bar(engagement_data.head(2), x='Metric', y='Value',
                                   title="Facebook Engagement Metrics",
                                   color='Value',
                                   color_continuous_scale='Blues')
            st.plotly_chart(fig_engagement, use_container_width=True)
        
        # Platform comparison table
        st.subheader("📊 So Sánh Chi Tiết Các Nền Tảng")
        
        platform_detail = pd.DataFrame({
            'Nền tảng': ['Website', 'Facebook', 'YouTube', 'Zalo', 'TikTok'],
            'Chỉ số chính 2024': [
                f"{tttt_data['website']['luot_truy_cap_2024']:,}",
                f"{tttt_data['fanpage']['luot_thich_2024']:,}",
                f"{tttt_data['youtube']['luot_dang_ky_2024']:,}",
                f"{tttt_data['zalo']['luot_quan_tam_2024']:,}",
                "Chưa có"
            ],
            'Chỉ số chính 2025': [
                f"{tttt_data['website']['luot_truy_cap_2025']:,}",
                f"{tttt_data['fanpage']['luot_thich_2025']:,}",
                f"{tttt_data['youtube']['luot_dang_ky_2025']:,}",
                f"{tttt_data['zalo']['luot_quan_tam_2025']:,}",
                f"{tttt_data['tiktok']['luot_dang_ky_2025']:,}"
            ],
            'Tăng trưởng': [
                f"+{tttt_data['website']['luot_truy_cap_growth']:.1f}%",
                f"+{tttt_data['fanpage']['luot_thich_growth']:.0f}%",
                f"+{tttt_data['youtube']['luot_dang_ky_growth']:.0f}%",
                f"+{tttt_data['zalo']['luot_quan_tam_growth']:.0f}%",
                "Mới"
            ],
            'Nội dung 2025': [
                f"{tttt_data['website']['bai_viet_2025']} bài",
                f"{tttt_data['fanpage']['bai_viet_2025']} bài",
                f"{tttt_data['youtube']['video_2025']} video",
                f"{tttt_data['zalo']['bai_viet_2025']} bài",
                f"{tttt_data['tiktok']['video_2025']} video"
            ]
        })
        
        st.dataframe(platform_detail, use_container_width=True)
    
    # Tab Ấn phẩm & Giáo dục
    with subtab4:
        st.header("📚 Ấn Phẩm Truyền Thông & Giáo Dục Sức Khỏe")
        
        # Metrics ấn phẩm
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Loại ấn phẩm",
                f"{tttt_data['an_pham']['loai_an_pham_2025']}",
                f"+{tttt_data['an_pham']['loai_an_pham_growth']:.0f}%"
            )
        
        with col2:
            st.metric(
                "Số lượng phát hành",
                f"{tttt_data['an_pham']['so_luong_2025']:,}",
                "tờ/quyển"
            )
        
        with col3:
            avg_per_type = tttt_data['an_pham']['so_luong_2025'] / tttt_data['an_pham']['loai_an_pham_2025']
            st.metric(
                "TB số lượng/loại",
                f"{avg_per_type:,.0f}",
                "ấn phẩm"
            )
        
        with col4:
            st.metric(
                "Tăng trưởng loại ấn phẩm",
                f"+{tttt_data['an_pham']['loai_an_pham_growth']:.0f}%",
                "Ấn tượng!"
            )
        
        # Biểu đồ phân tích
        col1, col2 = st.columns(2)
        
        with col1:
            # Tăng trưởng ấn phẩm
            growth_comparison = pd.DataFrame({
                'Chỉ số': ['Loại ấn phẩm 2024', 'Loại ấn phẩm 2025'],
                'Số lượng': [
                    tttt_data['an_pham']['loai_an_pham_2024'],
                    tttt_data['an_pham']['loai_an_pham_2025']
                ]
            })
            
            fig_growth = px.bar(growth_comparison, x='Chỉ số', y='Số lượng',
                               title="Tăng trưởng đa dạng hóa ấn phẩm",
                               color='Số lượng',
                               color_continuous_scale='Greens',
                               text='Số lượng')
            fig_growth.update_traces(texttemplate='%{text}', textposition='outside')
            st.plotly_chart(fig_growth, use_container_width=True)
        
        with col2:
            # Phân loại ấn phẩm (giả định)
            publication_types = pd.DataFrame({
                'Loại': ['Tờ rơi', 'Sổ tay', 'E-brochure', 'Banner', 'Poster', 'Infographic', 'Khác'],
                'Số lượng': [80000, 50000, 30000, 60000, 40000, 35000, 5713]
            })
            
            fig_types = px.pie(publication_types, values='Số lượng', names='Loại',
                              title="Phân bổ ấn phẩm theo loại (ước tính)",
                              color_discrete_sequence=px.colors.sequential.Viridis)
            st.plotly_chart(fig_types, use_container_width=True)
        

# ==================== TAB PHÒNG TỔ CHỨC CÁN BỘ ====================
with tab_tcbc:
    st.markdown("""
    <div class="section-header">
        <h2>👥 TỔ CHỨC CÁN BỘ</h2>
        <p>Quản lý tổ chức, nhân sự, đào tạo và công tác thi đua khen thưởng</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Tổng quan KPIs chính
    st.subheader("📊 Tổng quan hoạt động Tổ chức Cán bộ")
    
    # Tính tổng nhân sự
    tong_nhan_su = tcbc_data['nhan_su']['thuong_xuyen']['value'] + tcbc_data['nhan_su']['vu_viec_toan_tg']['value'] + tcbc_data['nhan_su']['vu_viec_ban_tg']['value']
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Tổng nhân sự",
            f"{tong_nhan_su:,}",
            f"{tcbc_data['nhan_su']['thuong_xuyen']['change'] + tcbc_data['nhan_su']['vu_viec_toan_tg']['change'] + tcbc_data['nhan_su']['vu_viec_ban_tg']['change']:+,} người"
        )
    
    with col2:
        tong_don_vi = tcbc_data['to_chuc']['phong_trung_tam']['value'] + tcbc_data['to_chuc']['khoa']['value'] + tcbc_data['to_chuc']['trung_tam']['value']
        st.metric(
            "Đơn vị tổ chức",
            f"{tong_don_vi}",
            "đơn vị chính"
        )
    
    with col3:
        st.metric(
            "Đào tạo nội bộ",
            f"{tcbc_data['dao_tao']['dao_tao_noi_bo']['luot_tham_gia']['value']:,}",
            f"{tcbc_data['dao_tao']['dao_tao_noi_bo']['luot_tham_gia']['change']:+,} lượt"
        )
    
    with col4:
        tong_khen_thuong = tcbc_data['thi_dua_khen_thuong']['khen_dinh_ky']['value'] + tcbc_data['thi_dua_khen_thuong']['khen_dot_xuat']['value']
        st.metric(
            "Thi đua khen thưởng",
            f"{tong_khen_thuong:,}",
            "lượt khen thưởng"
        )
    
    # Sub-tabs cho từng mảng hoạt động
    subtab1, subtab2, subtab3, subtab4, subtab5 = st.tabs([
        "🏢 Tổ Chức", "👤 Nhân Sự", "🎓 Đào Tạo", "🏆 Thi Đua Khen Thưởng", "📞 Khiếu Nại & Tố Cáo"
    ])
    
    # Tab Tổ chức
    with subtab1:
        st.header("🏢 Sơ Đồ Tổ Chức Bệnh Viện")
        
        # Metrics tổ chức chính
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Phòng/Trung tâm",
                f"{tcbc_data['to_chuc']['phong_trung_tam']['value']}",
                "không thay đổi"
            )
        
        with col2:
            st.metric(
                "Khoa",
                f"{tcbc_data['to_chuc']['khoa']['value']}",
                f"{tcbc_data['to_chuc']['khoa']['change']:+,} so với cùng kỳ"
            )
        
        with col3:
            st.metric(
                "Trung tâm",
                f"{tcbc_data['to_chuc']['trung_tam']['value']}",
                "không thay đổi"
            )
        
        with col4:
            st.metric(
                "Đơn nguyên",
                f"{tcbc_data['to_chuc']['don_nguyen']['value']}",
                f"+{tcbc_data['to_chuc']['don_nguyen']['change']} so với cùng kỳ"
            )
        
        # Biểu đồ cơ cấu tổ chức
        col1, col2 = st.columns(2)
        
        with col1:
            # Biểu đồ tổng quan đơn vị
            org_data = pd.DataFrame({
                'Loại đơn vị': ['Phòng/TT', 'Khoa', 'Trung tâm', 'Đơn nguyên', 'Đơn vị', 'Trạm'],
                'Số lượng': [
                    tcbc_data['to_chuc']['phong_trung_tam']['value'],
                    tcbc_data['to_chuc']['khoa']['value'],
                    tcbc_data['to_chuc']['trung_tam']['value'],
                    tcbc_data['to_chuc']['don_nguyen']['value'],
                    tcbc_data['to_chuc']['don_vi']['value'],
                    tcbc_data['to_chuc']['tram']['value']
                ]
            })
            
            fig_org = px.bar(org_data, x='Loại đơn vị', y='Số lượng',
                            title="Cơ cấu tổ chức theo loại đơn vị",
                            color='Số lượng',
                            color_continuous_scale='Blues',
                            text='Số lượng')
            fig_org.update_traces(texttemplate='%{text}', textposition='outside')
            fig_org.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_org, use_container_width=True)
        
        with col2:
            # Biểu đồ các hội đồng, ban, tổ
            support_data = pd.DataFrame({
                'Loại tổ chức': ['Hội đồng', 'Tổ', 'Ban/Tiểu ban', 'Mạng lưới'],
                'Số lượng': [
                    tcbc_data['to_chuc']['hoi_dong']['value'],
                    tcbc_data['to_chuc']['to']['value'],
                    tcbc_data['to_chuc']['ban_tieu_ban']['value'],
                    tcbc_data['to_chuc']['mang_luoi']['value']
                ]
            })
            
            fig_support = px.pie(support_data, values='Số lượng', names='Loại tổ chức',
                                title="Các tổ chức hỗ trợ",
                                color_discrete_sequence=['#FF6B6B', '#4ECDC4', '#FFA500', '#32CD32'])
            st.plotly_chart(fig_support, use_container_width=True)
        
        # Hoạt động sắp xếp đơn vị
        st.subheader("🔄 Hoạt Động Sắp Xếp Tổ Chức")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Thành lập mới",
                f"{tcbc_data['to_chuc']['sap_xep_don_vi']['thanh_lap']['value']}",
                f"+{tcbc_data['to_chuc']['sap_xep_don_vi']['thanh_lap']['change']} đơn vị"
            )
        
        with col2:
            st.metric(
                "Đổi tên",
                f"{tcbc_data['to_chuc']['sap_xep_don_vi']['doi_ten']['value']}",
                f"+{tcbc_data['to_chuc']['sap_xep_don_vi']['doi_ten']['change']} so với cùng kỳ"
            )
        
        with col3:
            st.metric(
                "Giải thể",
                f"{tcbc_data['to_chuc']['sap_xep_don_vi']['giai_the']['value']}",
                f"+{tcbc_data['to_chuc']['sap_xep_don_vi']['giai_the']['change']} so với cùng kỳ"
            )
        
        # Bảng chi tiết tổ chức
        st.subheader("📋 Bảng Chi Tiết Cơ Cấu Tổ Chức")
        
        org_detail = pd.DataFrame({
            'STT': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            'Loại tổ chức': [
                'Phòng/Trung tâm/Đơn vị',
                'Khoa',
                'Trung tâm chuyên môn',
                'Đơn nguyên',
                'Đơn vị',
                'Trạm',
                'Hội đồng',
                'Tổ',
                'Ban + Tiểu ban',
                'Mạng lưới'
            ],
            'Số lượng': [
                tcbc_data['to_chuc']['phong_trung_tam']['value'],
                tcbc_data['to_chuc']['khoa']['value'],
                tcbc_data['to_chuc']['trung_tam']['value'],
                tcbc_data['to_chuc']['don_nguyen']['value'],
                tcbc_data['to_chuc']['don_vi']['value'],
                tcbc_data['to_chuc']['tram']['value'],
                tcbc_data['to_chuc']['hoi_dong']['value'],
                tcbc_data['to_chuc']['to']['value'],
                tcbc_data['to_chuc']['ban_tieu_ban']['value'],
                tcbc_data['to_chuc']['mang_luoi']['value']
            ],
            'So sánh cùng kỳ': [
                'Không thay đổi',
                'Giảm 01',
                'Không thay đổi',
                'Tăng 01',
                'Không thay đổi',
                'Tăng 01',
                'Không thay đổi',
                'Không thay đổi',
                'Không thay đổi',
                'Không thay đổi'
            ],
            'Ghi chú': [
                'Đơn vị tham mưu chính',
                'Đơn vị khám chữa bệnh',
                'Đơn vị hỗ trợ chuyên môn',
                'Thuộc các khoa',
                'Thuộc phòng/cơ sở',
                'Đơn vị KCB',
                'Tổ chức tư vấn',
                'Đơn vị nhỏ',
                'Tổ chức điều phối',
                'Hệ thống liên kết'
            ]
        })
        
        st.dataframe(org_detail, use_container_width=True)
    
    # Tab Nhân sự
    with subtab2:
        st.header("👤 Quản Lý Nhân Sự")
        
        # PHẦN MỚI - Tổng quan nhân sự 3 cơ sở
        st.subheader("🏥 Tổng Quan Nhân Sự 3 Cơ Sở")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Tổng nhân sự (3 cơ sở)",
                f"{tcbc_data['nhan_su']['tong_nhan_su_3_co_so']['t6_2025']:,}",
                f"+{tcbc_data['nhan_su']['tong_nhan_su_3_co_so']['tang_giam']:,} so với T6.2024"
            )
        
        with col2:
            st.metric(
                "Tăng trưởng nhân sự",
                f"{tcbc_data['nhan_su']['tong_nhan_su_3_co_so']['tang_giam_percent']:.1f}%",
                "so với cùng kỳ năm trước"
            )
        
        with col3:
            # Tính tỷ lệ trình độ cao (sau ĐH + ĐH)
            trinh_do_cao = tcbc_data['nhan_su']['co_cau_trinh_do']['sau_dai_hoc']['t6_2025'] + tcbc_data['nhan_su']['co_cau_trinh_do']['dai_hoc']['t6_2025']
            ty_le_trinh_do_cao = (trinh_do_cao / tcbc_data['nhan_su']['tong_nhan_su_3_co_so']['t6_2025']) * 100
            st.metric(
                "Nhân sự trình độ cao",
                f"{trinh_do_cao:,}",
                f"{ty_le_trinh_do_cao:.1f}% tổng nhân sự"
            )
        
        with col4:
            # Tính tỷ lệ nhân sự có chuyên môn y tế
            chuyen_mon_yte = (tcbc_data['nhan_su']['co_cau_chi_tiet']['giao_su']['so_luong'] + 
                             tcbc_data['nhan_su']['co_cau_chi_tiet']['pho_giao_su']['so_luong'] + 
                             tcbc_data['nhan_su']['co_cau_chi_tiet']['tien_si']['so_luong'] + 
                             tcbc_data['nhan_su']['co_cau_chi_tiet']['bac_sy_ck2']['so_luong'] + 
                             tcbc_data['nhan_su']['co_cau_chi_tiet']['thac_si']['so_luong'] + 
                             tcbc_data['nhan_su']['co_cau_chi_tiet']['bac_sy_ck1']['so_luong'])
            st.metric(
                "Nhân sự chuyên môn cao",
                f"{chuyen_mon_yte:,}",
                f"{(chuyen_mon_yte/tcbc_data['nhan_su']['tong_nhan_su_3_co_so']['t6_2025']*100):.1f}% tổng NS"
            )
        
        # So sánh cơ cấu trình độ T6.2024 vs T6.2025
        st.subheader("📊 So Sánh Cơ Cấu Trình Độ (T6.2024 vs T6.2025)")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Biểu đồ so sánh 2 kỳ
            trinh_do_comparison = pd.DataFrame({
                'Trình độ': ['Sau đại học', 'Đại học', 'Cao đẳng/TH', 'Phổ thông TH'],
                'T6.2024': [
                    tcbc_data['nhan_su']['co_cau_trinh_do']['sau_dai_hoc']['t6_2024'],
                    tcbc_data['nhan_su']['co_cau_trinh_do']['dai_hoc']['t6_2024'],
                    tcbc_data['nhan_su']['co_cau_trinh_do']['cao_dang_trung_hoc']['t6_2024'],
                    tcbc_data['nhan_su']['co_cau_trinh_do']['pho_thong_trung_hoc']['t6_2024']
                ],
                'T6.2025': [
                    tcbc_data['nhan_su']['co_cau_trinh_do']['sau_dai_hoc']['t6_2025'],
                    tcbc_data['nhan_su']['co_cau_trinh_do']['dai_hoc']['t6_2025'],
                    tcbc_data['nhan_su']['co_cau_trinh_do']['cao_dang_trung_hoc']['t6_2025'],
                    tcbc_data['nhan_su']['co_cau_trinh_do']['pho_thong_trung_hoc']['t6_2025']
                ]
            })
            
            fig_trinh_do = px.bar(trinh_do_comparison, x='Trình độ', y=['T6.2024', 'T6.2025'],
                                 title="So sánh cơ cấu trình độ 2 kỳ",
                                 barmode='group',
                                 color_discrete_sequence=['#FF6B6B', '#4ECDC4'])
            fig_trinh_do.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_trinh_do, use_container_width=True)
        
        with col2:
            # Biểu đồ tăng trưởng
            tang_truong_data = pd.DataFrame({
                'Trình độ': ['Sau ĐH', 'Đại học', 'CĐ/TH', 'PT TH'],
                'Tăng trưởng (%)': [
                    tcbc_data['nhan_su']['co_cau_trinh_do']['sau_dai_hoc']['tang_giam_percent'],
                    tcbc_data['nhan_su']['co_cau_trinh_do']['dai_hoc']['tang_giam_percent'],
                    tcbc_data['nhan_su']['co_cau_trinh_do']['cao_dang_trung_hoc']['tang_giam_percent'],
                    tcbc_data['nhan_su']['co_cau_trinh_do']['pho_thong_trung_hoc']['tang_giam_percent']
                ]
            })
            
            fig_tang_truong = px.bar(tang_truong_data, x='Trình độ', y='Tăng trưởng (%)',
                                    title="Tăng trưởng theo trình độ (%)",
                                    color='Tăng trưởng (%)',
                                    color_continuous_scale='RdYlGn',
                                    color_continuous_midpoint=0)
            fig_tang_truong.add_hline(y=0, line_dash="dash", line_color="black")
            st.plotly_chart(fig_tang_truong, use_container_width=True)
        
        # Cơ cấu chi tiết theo chức danh và chuyên môn
        st.subheader("🎓 Cơ Cấu Chi Tiết Theo Chức Danh & Chuyên Môn")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Pie chart cơ cấu chức danh cao cấp
            chuc_danh_cao = pd.DataFrame({
                'Chức danh': ['Giáo sư', 'Phó Giáo sư', 'Tiến sĩ', 'BS CKII', 'Thạc sĩ', 'BS CKI', 'Khác'],
                'Số lượng': [
                    tcbc_data['nhan_su']['co_cau_chi_tiet']['giao_su']['so_luong'],
                    tcbc_data['nhan_su']['co_cau_chi_tiet']['pho_giao_su']['so_luong'],
                    tcbc_data['nhan_su']['co_cau_chi_tiet']['tien_si']['so_luong'],
                    tcbc_data['nhan_su']['co_cau_chi_tiet']['bac_sy_ck2']['so_luong'],
                    tcbc_data['nhan_su']['co_cau_chi_tiet']['thac_si']['so_luong'],
                    tcbc_data['nhan_su']['co_cau_chi_tiet']['bac_sy_ck1']['so_luong'],
                    tcbc_data['nhan_su']['co_cau_chi_tiet']['dai_hoc_chi_tiet']['so_luong'] + 
                    tcbc_data['nhan_su']['co_cau_chi_tiet']['cao_dang']['so_luong'] + 
                    tcbc_data['nhan_su']['co_cau_chi_tiet']['trung_hoc']['so_luong'] + 
                    tcbc_data['nhan_su']['co_cau_chi_tiet']['nhan_vien_yte_khac']['so_luong']
                ]
            })
            
            fig_chuc_danh = px.pie(chuc_danh_cao, values='Số lượng', names='Chức danh',
                                  title="Cơ cấu theo chức danh & chuyên môn",
                                  color_discrete_sequence=px.colors.qualitative.Set3)
            fig_chuc_danh.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_chuc_danh, use_container_width=True)
        
        with col2:
            # Bar chart top chức danh
            top_chuc_danh = pd.DataFrame({
                'Chức danh': ['Đại học', 'Trung học', 'Thạc sĩ', 'NV Y tế khác', 'BS CKI'],
                'Số lượng': [
                    tcbc_data['nhan_su']['co_cau_chi_tiet']['dai_hoc_chi_tiet']['so_luong'],
                    tcbc_data['nhan_su']['co_cau_chi_tiet']['trung_hoc']['so_luong'],
                    tcbc_data['nhan_su']['co_cau_chi_tiet']['thac_si']['so_luong'],
                    tcbc_data['nhan_su']['co_cau_chi_tiet']['nhan_vien_yte_khac']['so_luong'],
                    tcbc_data['nhan_su']['co_cau_chi_tiet']['bac_sy_ck1']['so_luong']
                ]
            })
            
            fig_top_chuc_danh = px.bar(top_chuc_danh, x='Chức danh', y='Số lượng',
                                      title="Top 5 nhóm nhân sự đông nhất",
                                      color='Số lượng',
                                      color_continuous_scale='Blues',
                                      text='Số lượng')
            fig_top_chuc_danh.update_traces(texttemplate='%{text:,}', textposition='outside')
            fig_top_chuc_danh.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_top_chuc_danh, use_container_width=True)
        
        # Bảng chi tiết cơ cấu nhân sự
        st.subheader("📋 Bảng Chi Tiết Cơ Cấu Nhân Sự (T6.2025)")
        
        # Bảng so sánh trình độ
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**📊 So sánh theo trình độ**")
            trinh_do_detail = pd.DataFrame({
                'STT': [1, 2, 3, 4],
                'Trình độ': ['Sau đại học', 'Đại học', 'Cao đẳng, trung học', 'Phổ thông trung học'],
                'T6.2024': [
                    f"{tcbc_data['nhan_su']['co_cau_trinh_do']['sau_dai_hoc']['t6_2024']:,}",
                    f"{tcbc_data['nhan_su']['co_cau_trinh_do']['dai_hoc']['t6_2024']:,}",
                    f"{tcbc_data['nhan_su']['co_cau_trinh_do']['cao_dang_trung_hoc']['t6_2024']:,}",
                    f"{tcbc_data['nhan_su']['co_cau_trinh_do']['pho_thong_trung_hoc']['t6_2024']:,}"
                ],
                'T6.2025': [
                    f"{tcbc_data['nhan_su']['co_cau_trinh_do']['sau_dai_hoc']['t6_2025']:,}",
                    f"{tcbc_data['nhan_su']['co_cau_trinh_do']['dai_hoc']['t6_2025']:,}",
                    f"{tcbc_data['nhan_su']['co_cau_trinh_do']['cao_dang_trung_hoc']['t6_2025']:,}",
                    f"{tcbc_data['nhan_su']['co_cau_trinh_do']['pho_thong_trung_hoc']['t6_2025']:,}"
                ],
                'Tăng/Giảm': [
                    f"{tcbc_data['nhan_su']['co_cau_trinh_do']['sau_dai_hoc']['tang_giam']:+,}",
                    f"{tcbc_data['nhan_su']['co_cau_trinh_do']['dai_hoc']['tang_giam']:+,}",
                    f"{tcbc_data['nhan_su']['co_cau_trinh_do']['cao_dang_trung_hoc']['tang_giam']:+,}",
                    f"{tcbc_data['nhan_su']['co_cau_trinh_do']['pho_thong_trung_hoc']['tang_giam']:+,}"
                ],
                'Tăng/Giảm (%)': [
                    f"{tcbc_data['nhan_su']['co_cau_trinh_do']['sau_dai_hoc']['tang_giam_percent']:+.1f}%",
                    f"{tcbc_data['nhan_su']['co_cau_trinh_do']['dai_hoc']['tang_giam_percent']:+.1f}%",
                    f"{tcbc_data['nhan_su']['co_cau_trinh_do']['cao_dang_trung_hoc']['tang_giam_percent']:+.1f}%",
                    f"{tcbc_data['nhan_su']['co_cau_trinh_do']['pho_thong_trung_hoc']['tang_giam_percent']:+.1f}%"
                ]
            })
            st.dataframe(trinh_do_detail, use_container_width=True)
        
        with col2:
            st.write("**🎓 Cơ cấu theo chức danh chi tiết**")
            chuc_danh_detail = pd.DataFrame({
                'STT': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                'Cơ cấu': [
                    'Giáo sư', 'Phó Giáo sư', 'Tiến sĩ', 'Bác sỹ chuyên khoa II',
                    'Thạc sĩ', 'Bác sỹ chuyên khoa I', 'Đại học', 'Cao đẳng',
                    'Trung học', 'Nhân viên y tế khác'
                ],
                'Số lượng': [
                    tcbc_data['nhan_su']['co_cau_chi_tiet']['giao_su']['so_luong'],
                    tcbc_data['nhan_su']['co_cau_chi_tiet']['pho_giao_su']['so_luong'],
                    tcbc_data['nhan_su']['co_cau_chi_tiet']['tien_si']['so_luong'],
                    tcbc_data['nhan_su']['co_cau_chi_tiet']['bac_sy_ck2']['so_luong'],
                    tcbc_data['nhan_su']['co_cau_chi_tiet']['thac_si']['so_luong'],
                    tcbc_data['nhan_su']['co_cau_chi_tiet']['bac_sy_ck1']['so_luong'],
                    tcbc_data['nhan_su']['co_cau_chi_tiet']['dai_hoc_chi_tiet']['so_luong'],
                    tcbc_data['nhan_su']['co_cau_chi_tiet']['cao_dang']['so_luong'],
                    tcbc_data['nhan_su']['co_cau_chi_tiet']['trung_hoc']['so_luong'],
                    tcbc_data['nhan_su']['co_cau_chi_tiet']['nhan_vien_yte_khac']['so_luong']
                ],
                'Tỷ lệ (%)': [
                    f"{tcbc_data['nhan_su']['co_cau_chi_tiet']['giao_su']['ty_le']:.2f}%",
                    f"{tcbc_data['nhan_su']['co_cau_chi_tiet']['pho_giao_su']['ty_le']:.2f}%",
                    f"{tcbc_data['nhan_su']['co_cau_chi_tiet']['tien_si']['ty_le']:.2f}%",
                    f"{tcbc_data['nhan_su']['co_cau_chi_tiet']['bac_sy_ck2']['ty_le']:.2f}%",
                    f"{tcbc_data['nhan_su']['co_cau_chi_tiet']['thac_si']['ty_le']:.2f}%",
                    f"{tcbc_data['nhan_su']['co_cau_chi_tiet']['bac_sy_ck1']['ty_le']:.2f}%",
                    f"{tcbc_data['nhan_su']['co_cau_chi_tiet']['dai_hoc_chi_tiet']['ty_le']:.2f}%",
                    f"{tcbc_data['nhan_su']['co_cau_chi_tiet']['cao_dang']['ty_le']:.2f}%",
                    f"{tcbc_data['nhan_su']['co_cau_chi_tiet']['trung_hoc']['ty_le']:.2f}%",
                    f"{tcbc_data['nhan_su']['co_cau_chi_tiet']['nhan_vien_yte_khac']['ty_le']:.2f}%"
                ]
            })
            st.dataframe(chuc_danh_detail, use_container_width=True)
        
        # Metrics nhân sự cũ (giữ lại phần này)
        st.subheader("👤 Quản Lý Nhân Sự Hợp Đồng")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Nhân viên thường xuyên",
                f"{tcbc_data['nhan_su']['thuong_xuyen']['value']:,}",
                f"+{tcbc_data['nhan_su']['thuong_xuyen']['change']:+,} người"
            )
        
        with col2:
            st.metric(
                "Vụ việc toàn thời gian",
                f"{tcbc_data['nhan_su']['vu_viec_toan_tg']['value']:,}",
                f"{tcbc_data['nhan_su']['vu_viec_toan_tg']['change']:+,} người"
            )
        
        with col3:
            st.metric(
                "Vụ việc bán thời gian",
                f"{tcbc_data['nhan_su']['vu_viec_ban_tg']['value']:,}",
                f"+{tcbc_data['nhan_su']['vu_viec_ban_tg']['change']:+,} người"
            )
        
        with col4:
            st.metric(
                "Tuyển dụng 6 tháng",
                f"{tcbc_data['nhan_su']['tuyen_dung']['value']:,}",
                f"{tcbc_data['nhan_su']['tuyen_dung']['change']:+,} người"
            )
        
        # Phân tích và insights 
        st.subheader("💡 Phân Tích & Đánh Giá")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.success("🎯 **Điểm mạnh cơ cấu nhân sự:**")
            st.write(f"• **{tcbc_data['nhan_su']['tong_nhan_su_3_co_so']['t6_2025']:,} nhân sự** tại 3 cơ sở")
            st.write(f"• **{ty_le_trinh_do_cao:.1f}%** có trình độ từ đại học trở lên")
            st.write(f"• **{chuyen_mon_yte:,} người** ({(chuyen_mon_yte/tcbc_data['nhan_su']['tong_nhan_su_3_co_so']['t6_2025']*100):.1f}%) có chuyên môn cao")
            st.write(f"• **{tcbc_data['nhan_su']['co_cau_chi_tiet']['thac_si']['so_luong']:,} Thạc sĩ** ({tcbc_data['nhan_su']['co_cau_chi_tiet']['thac_si']['ty_le']:.1f}%)")
            st.write(f"• **{tcbc_data['nhan_su']['co_cau_chi_tiet']['giao_su']['so_luong'] + tcbc_data['nhan_su']['co_cau_chi_tiet']['pho_giao_su']['so_luong']} GS/PGS** đẳng cấp quốc gia")
        
        with col2:
            st.info("📈 **Xu hướng phát triển:**")
            st.write("• **Tăng trưởng tích cực:** +163 nhân sự (+3.9%)")
            st.write("• **Nâng cao trình độ:** Sau ĐH +6.7%, ĐH +13.7%")
            st.write("• **Tối ưu cơ cấu:** Giảm CĐ/TH (-11.6%)")
            st.write("• **Đầu tư chất lượng:** Ưu tiên nhân sự trình độ cao")
            st.write("• **Định hướng:** Xây dựng đội ngũ chuyên môn sâu")
        
        # Xu hướng biến động (giữ lại phần cũ)
        st.subheader("📈 Xu Hướng Biến Động Hợp Đồng Lao Động")
        
        months = ['Tháng 1', 'Tháng 2', 'Tháng 3', 'Tháng 4', 'Tháng 5', 'Tháng 6']
        
        # Phân bổ tuyển dụng và chấm dứt qua 6 tháng
        tuyen_dung_trend = [18, 20, 15, 22, 16, 14]  # Tổng = 105
        cham_dut_trend = [8, 5, 6, 7, 4, 6]  # Tổng = 36
        
        fig_hr_trend = go.Figure()
        fig_hr_trend.add_trace(go.Scatter(x=months, y=tuyen_dung_trend,
                                         mode='lines+markers', name='Tuyển dụng',
                                         line=dict(color='#4ECDC4', width=3)))
        fig_hr_trend.add_trace(go.Scatter(x=months, y=cham_dut_trend,
                                         mode='lines+markers', name='Chấm dứt HĐLĐ',
                                         line=dict(color='#FF6B6B', width=3)))
        
        fig_hr_trend.update_layout(
            title="Xu hướng tuyển dụng và chấm dứt hợp đồng",
            xaxis_title="Tháng",
            yaxis_title="Số người",
            height=400
        )
        st.plotly_chart(fig_hr_trend, use_container_width=True)
    
    # Tab Đào tạo
    with subtab3:
        st.header("🎓 Đào Tạo & Phát Triển Nhân Sự")
        
        # Metrics đào tạo
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Cử đi đào tạo",
                f"{tcbc_data['dao_tao']['cu_dao_tao']['value']:,}",
                f"+{tcbc_data['dao_tao']['cu_dao_tao']['change']:+,} lượt"
            )
        
        with col2:
            st.metric(
                "Đào tạo trong nước",
                f"{tcbc_data['dao_tao']['cu_dao_tao']['detail']['trong_nuoc']:,}",
                f"{(tcbc_data['dao_tao']['cu_dao_tao']['detail']['trong_nuoc']/tcbc_data['dao_tao']['cu_dao_tao']['value']*100):.1f}%"
            )
        
        with col3:
            st.metric(
                "Đào tạo nước ngoài",
                f"{tcbc_data['dao_tao']['cu_dao_tao']['detail']['nuoc_ngoai']:,}",
                f"{(tcbc_data['dao_tao']['cu_dao_tao']['detail']['nuoc_ngoai']/tcbc_data['dao_tao']['cu_dao_tao']['value']*100):.1f}%"
            )
        
        with col4:
            st.metric(
                "Đào tạo nội bộ",
                f"{tcbc_data['dao_tao']['dao_tao_noi_bo']['luot_tham_gia']['value']:,}",
                f"+{tcbc_data['dao_tao']['dao_tao_noi_bo']['luot_tham_gia']['change']:+,} lượt"
            )
        
        # Biểu đồ đào tạo
        col1, col2 = st.columns(2)
        
        with col1:
            # So sánh đào tạo trong/ngoài nước
            training_location = pd.DataFrame({
                'Địa điểm': ['Trong nước', 'Nước ngoài'],
                'Số lượt': [
                    tcbc_data['dao_tao']['cu_dao_tao']['detail']['trong_nuoc'],
                    tcbc_data['dao_tao']['cu_dao_tao']['detail']['nuoc_ngoai']
                ]
            })
            
            fig_location = px.pie(training_location, values='Số lượt', names='Địa điểm',
                                 title="Cơ cấu đào tạo theo địa điểm",
                                 color_discrete_sequence=['#4ECDC4', '#FF6B6B'])
            fig_location.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_location, use_container_width=True)
        
        with col2:
            # So sánh đào tạo bên ngoài vs nội bộ
            training_type = pd.DataFrame({
                'Loại đào tạo': ['Cử đi đào tạo', 'Đào tạo nội bộ'],
                'Số lượt': [
                    tcbc_data['dao_tao']['cu_dao_tao']['value'],
                    tcbc_data['dao_tao']['dao_tao_noi_bo']['luot_tham_gia']['value']
                ]
            })
            
            fig_type = px.bar(training_type, x='Loại đào tạo', y='Số lượt',
                             title="So sánh đào tạo bên ngoài vs nội bộ",
                             color='Số lượt',
                             color_continuous_scale='Viridis',
                             text='Số lượt')
            fig_type.update_traces(texttemplate='%{text:,}', textposition='outside')
            st.plotly_chart(fig_type, use_container_width=True)
        
        # Xu hướng đào tạo (mock data)
        st.subheader("📊 Xu Hướng Đào Tạo 6 Tháng")
        
        # Phân bổ đào tạo qua 6 tháng
        cu_dao_tao_trend = [45, 52, 48, 55, 51, 50]  # Tổng ≈ 301
        dao_tao_noi_bo_trend = [85, 95, 110, 125, 102, 100]  # Tổng ≈ 617
        
        fig_training_trend = go.Figure()
        fig_training_trend.add_trace(go.Scatter(x=months, y=cu_dao_tao_trend,
                                               mode='lines+markers', name='Cử đi đào tạo',
                                               line=dict(color='#4ECDC4', width=3)))
        fig_training_trend.add_trace(go.Scatter(x=months, y=dao_tao_noi_bo_trend,
                                               mode='lines+markers', name='Đào tạo nội bộ',
                                               line=dict(color='#FF6B6B', width=3)))
        
        fig_training_trend.update_layout(
            title="Xu hướng hoạt động đào tạo theo tháng",
            xaxis_title="Tháng",
            yaxis_title="Số lượt",
            height=400
        )
        st.plotly_chart(fig_training_trend, use_container_width=True)
        
        # Insights
        col1, col2 = st.columns(2)
        
        with col1:
            st.success("🎯 **Thành tựu đào tạo:**")
            st.write(f"• Tổng lượt đào tạo: **{tcbc_data['dao_tao']['cu_dao_tao']['value'] + tcbc_data['dao_tao']['dao_tao_noi_bo']['luot_tham_gia']['value']:,} lượt**")
            st.write(f"• Tăng trưởng cử đi đào tạo: **+{tcbc_data['dao_tao']['cu_dao_tao']['change']} lượt** (+59%)")
            st.write(f"• Đào tạo nội bộ: **{tcbc_data['dao_tao']['dao_tao_noi_bo']['so_lop']['value']} lớp**")
            st.write(f"• Tỷ lệ đào tạo nước ngoài: **{(tcbc_data['dao_tao']['cu_dao_tao']['detail']['nuoc_ngoai']/tcbc_data['dao_tao']['cu_dao_tao']['value']*100):.1f}%**")
        
        with col2:
            st.info("📈 **Kế hoạch phát triển:**")
            st.write("• Tăng cường đào tạo chuyên sâu")
            st.write("• Mở rộng hợp tác quốc tế")
            st.write("• Phát triển e-learning")
            st.write("• Đào tạo kỹ năng lãnh đạo")
            st.write("• Chương trình mentoring")
    
    # Tab Thi đua khen thưởng
    with subtab4:
        st.header("🏆 Thi Đua Khen Thưởng")
        
        # Metrics khen thưởng
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Khen thưởng định kỳ",
                f"{tcbc_data['thi_dua_khen_thuong']['khen_dinh_ky']['value']:,}",
                "lượt khen thưởng"
            )
        
        with col2:
            st.metric(
                "Khen thưởng đột xuất",
                f"{tcbc_data['thi_dua_khen_thuong']['khen_dot_xuat']['value']:,}",
                "lượt khen thưởng"
            )
        
        with col3:
            tong_khen_thuong = tcbc_data['thi_dua_khen_thuong']['khen_dinh_ky']['value'] + tcbc_data['thi_dua_khen_thuong']['khen_dot_xuat']['value']
            st.metric(
                "Tổng khen thưởng",
                f"{tong_khen_thuong:,}",
                "lượt"
            )
        
        with col4:
            ty_le_khen_thuong = (tong_khen_thuong / tong_nhan_su) * 100
            st.metric(
                "Tỷ lệ khen thưởng",
                f"{ty_le_khen_thuong:.1f}%",
                "so với tổng nhân sự"
            )
        
        # Biểu đồ khen thưởng
        col1, col2 = st.columns(2)
        
        with col1:
            # So sánh khen thưởng định kỳ vs đột xuất
            reward_comparison = pd.DataFrame({
                'Loại khen thưởng': ['Định kỳ', 'Đột xuất'],
                'Số lượng': [
                    tcbc_data['thi_dua_khen_thuong']['khen_dinh_ky']['value'],
                    tcbc_data['thi_dua_khen_thuong']['khen_dot_xuat']['value']
                ]
            })
            
            fig_reward = px.pie(reward_comparison, values='Số lượng', names='Loại khen thưởng',
                               title="Cơ cấu khen thưởng",
                               color_discrete_sequence=['#FFD700', '#FFA500'])
            fig_reward.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_reward, use_container_width=True)
        
        with col2:
            # Chi tiết khen thưởng đột xuất
            detail_reward = pd.DataFrame({
                'Đối tượng': ['Tập thể', 'Cá nhân'],
                'Số lượng': [
                    tcbc_data['thi_dua_khen_thuong']['khen_dot_xuat']['detail']['tap_the'],
                    tcbc_data['thi_dua_khen_thuong']['khen_dot_xuat']['detail']['ca_nhan']
                ]
            })
            
            fig_detail = px.bar(detail_reward, x='Đối tượng', y='Số lượng',
                               title="Khen thưởng đột xuất theo đối tượng",
                               color='Số lượng',
                               color_continuous_scale='Oranges',
                               text='Số lượng')
            fig_detail.update_traces(texttemplate='%{text}', textposition='outside')
            st.plotly_chart(fig_detail, use_container_width=True)
        
        # Xu hướng khen thưởng (mock data)
        st.subheader("🏅 Xu Hướng Khen Thưởng 6 Tháng")
        
        # Phân bổ khen thưởng qua 6 tháng (ưu tiên khen đột xuất)
        khen_dinh_ky_trend = [8, 8, 8, 8, 9, 8]  # Tổng ≈ 49
        khen_dot_xuat_trend = [150, 180, 165, 175, 158, 155]  # Tổng ≈ 983
        
        fig_reward_trend = go.Figure()
        fig_reward_trend.add_trace(go.Bar(x=months, y=khen_dinh_ky_trend,
                                         name='Khen thưởng định kỳ',
                                         marker_color='#FFD700'))
        fig_reward_trend.add_trace(go.Bar(x=months, y=khen_dot_xuat_trend,
                                         name='Khen thưởng đột xuất',
                                         marker_color='#FFA500'))
        
        fig_reward_trend.update_layout(
            title="Xu hướng khen thưởng theo tháng",
            xaxis_title="Tháng",
            yaxis_title="Số lượt",
            barmode='group',
            height=400
        )
        st.plotly_chart(fig_reward_trend, use_container_width=True)
        
        # Bảng thống kê khen thưởng
        st.subheader("📋 Thống Kê Chi Tiết Khen Thưởng")
        
        reward_stats = pd.DataFrame({
            'Loại khen thưởng': ['Định kỳ - Tập thể', 'Định kỳ - Cá nhân', 'Đột xuất - Tập thể', 'Đột xuất - Cá nhân', 'Đột xuất - Phụ thuộc'],
            'Số lượt': [
                tcbc_data['thi_dua_khen_thuong']['khen_dinh_ky']['detail']['tap_the'],
                tcbc_data['thi_dua_khen_thuong']['khen_dinh_ky']['detail']['ca_nhan'],
                tcbc_data['thi_dua_khen_thuong']['khen_dot_xuat']['detail']['tap_the'],
                tcbc_data['thi_dua_khen_thuong']['khen_dot_xuat']['detail']['ca_nhan'],
                tcbc_data['thi_dua_khen_thuong']['khen_dot_xuat']['detail']['phu_thuoc']
            ],
            'Tỷ lệ (%)': [
                f"{(tcbc_data['thi_dua_khen_thuong']['khen_dinh_ky']['detail']['tap_the']/tong_khen_thuong*100):.1f}%",
                f"{(tcbc_data['thi_dua_khen_thuong']['khen_dinh_ky']['detail']['ca_nhan']/tong_khen_thuong*100):.1f}%",
                f"{(tcbc_data['thi_dua_khen_thuong']['khen_dot_xuat']['detail']['tap_the']/tong_khen_thuong*100):.1f}%",
                f"{(tcbc_data['thi_dua_khen_thuong']['khen_dot_xuat']['detail']['ca_nhan']/tong_khen_thuong*100):.1f}%",
                f"{(tcbc_data['thi_dua_khen_thuong']['khen_dot_xuat']['detail']['phu_thuoc']/tong_khen_thuong*100):.1f}%"
            ]
        })
        
        st.dataframe(reward_stats, use_container_width=True)
        
        # Insights
        col1, col2 = st.columns(2)
        
        with col1:
            st.success("🌟 **Điểm nổi bật:**")
            st.write(f"• Tổng **{tong_khen_thuong:,} lượt** khen thưởng")
            st.write(f"• Khen đột xuất chiếm **{(tcbc_data['thi_dua_khen_thuong']['khen_dot_xuat']['value']/tong_khen_thuong*100):.1f}%**")
            st.write(f"• Tỷ lệ khen/nhân sự: **{ty_le_khen_thuong:.1f}%**")
            st.write("• Động viên tinh thần tích cực")
        
        with col2:
            st.info("🎯 **Định hướng:**")
            st.write("• Đa dạng hóa hình thức khen thưởng")
            st.write("• Tăng cường khen tập thể")
            st.write("• Khen thưởng kịp thời")
            st.write("• Gắn khen thưởng với KPI")
    
    # Tab Khiếu nại tố cáo
    with subtab5:
        st.header("📞 Khiếu Nại, Tố Cáo & Phản Ánh")
        
        # Metrics khiếu nại
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Đơn thư khiếu nại",
                f"{tcbc_data['khieu_nai_to_cao']['don_thu_khieu_nai']['value']}",
                "vụ việc"
            )
        
        with col2:
            st.metric(
                "Đơn thư tố cáo",
                f"{tcbc_data['khieu_nai_to_cao']['don_thu_to_cao']['value']}",
                "vụ việc"
            )
        
        with col3:
            st.metric(
                "Đã giải quyết",
                f"{tcbc_data['khieu_nai_to_cao']['da_giai_quyet']['value']}",
                "vụ việc"
            )
        
        with col4:
            st.metric(
                "Chưa giải quyết",
                f"{tcbc_data['khieu_nai_to_cao']['chua_giai_quyet']['value']}",
                "vụ việc"
            )
        
        # Biểu đồ trạng thái khiếu nại
        if tcbc_data['khieu_nai_to_cao']['don_thu_khieu_nai']['value'] > 0:
            complaint_status = pd.DataFrame({
                'Trạng thái': ['Đã tiếp nhận', 'Đã giải quyết', 'Chưa giải quyết'],
                'Số lượng': [
                    tcbc_data['khieu_nai_to_cao']['don_thu_khieu_nai']['value'],
                    tcbc_data['khieu_nai_to_cao']['da_giai_quyet']['value'],
                    tcbc_data['khieu_nai_to_cao']['chua_giai_quyet']['value']
                ]
            })
            
            fig_complaint = px.bar(complaint_status, x='Trạng thái', y='Số lượng',
                                  title="Tình hình xử lý khiếu nại",
                                  color='Số lượng',
                                  color_continuous_scale='RdYlGn')
            st.plotly_chart(fig_complaint, use_container_width=True)
        else:
            st.success("✅ **Tình hình ổn định:** Không có khiếu nại, tố cáo trong 6 tháng đầu năm 2025")
        
        # Thông tin tích cực
        st.subheader("🌟 Đánh Giá Tình Hình")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.success("✅ **Tình hình tích cực:**")
            st.write("• **0 đơn tố cáo** - Minh bạch hoạt động")
            st.write("• **1 khiếu nai** đã được xử lý kịp thời")
            st.write("• **0 vụ việc khởi kiện** - Giải quyết hiệu quả")
            st.write("• **0 phản ánh** từ viên chức, NLĐ")
            st.write("• Môi trường làm việc hài hòa")
        
        with col2:
            st.info("🎯 **Cam kết duy trì:**")
            st.write("• Xử lý khiếu nại kịp thời, công khai")
            st.write("• Tăng cường đối화hợp tác nội bộ") 
            st.write("• Minh bạch trong quản lý nhân sự")
            st.write("• Lắng nghe ý kiến NLĐ")
            st.write("• Xây dựng văn hóa tích cực")
        
        # Timeline xử lý (nếu có)
        if tcbc_data['khieu_nai_to_cao']['don_thu_khieu_nai']['value'] > 0:
            st.subheader("📅 Quy Trình Xử Lý Khiếu Nại")
            
            timeline_data = pd.DataFrame({
                'Bước': ['Tiếp nhận', 'Xác minh', 'Giải quyết', 'Thông báo kết quả'],
                'Thời gian (ngày)': [1, 15, 30, 45],
                'Trạng thái': ['✅ Hoàn thành', '✅ Hoàn thành', '🔄 Đang thực hiện', '⏳ Chờ thực hiện']
            })
            
            fig_timeline = px.bar(timeline_data, x='Bước', y='Thời gian (ngày)',
                                 title="Timeline xử lý khiếu nại",
                                 color='Thời gian (ngày)',
                                 color_continuous_scale='Blues')
            st.plotly_chart(fig_timeline, use_container_width=True)
    
    # Tổng kết và insights chung
    st.subheader("💡 Tổng kết hoạt động Tổ chức Cán bộ")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.success("🎉 **Thành tựu nổi bật 6 tháng đầu năm:**")
        st.write(f"• **{tong_nhan_su:,} nhân sự** ({tcbc_data['nhan_su']['thuong_xuyen']['change'] + tcbc_data['nhan_su']['vu_viec_ban_tg']['change'] - 5:+,})")
        st.write(f"• **{tong_khen_thuong:,} lượt khen thưởng** (cao)")
        st.write(f"• **{tcbc_data['dao_tao']['cu_dao_tao']['value']:,} lượt đào tạo** (+{tcbc_data['dao_tao']['cu_dao_tao']['change']:+,})")
        st.write(f"• **{tcbc_data['dao_tao']['dao_tao_noi_bo']['luot_tham_gia']['value']:,} lượt** đào tạo nội bộ")
        st.write(f"• **30 đơn vị** được sắp xếp, đổi tên")
        st.write("• **0 khiếu nại nghiêm trọng** - Ổn định")
    
    with col2:
        st.info("🎯 **Định hướng phát triển:**")
        st.write("• Tối ưu hóa cơ cấu tổ chức")
        st.write("• Nâng cao chất lượng đào tạo")
        st.write("• Phát triển năng lực lãnh đạo")
        st.write("• Số hóa quy trình quản lý nhân sự")
        st.write("• Xây dựng văn hóa doanh nghiệp")
        st.write("• Tăng cường gắn kết nội bộ")

with tab_qttn:
    st.markdown("""
    <div class="section-header">
        <h2>🏢 QUẢN TRỊ TÒA NHÀ</h2>
        <p>Quản lý cơ sở hạ tầng, khí y tế, chất thải và vận hành tòa nhà</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Tổng quan KPIs chính
    st.subheader("📊 Tổng Quan Hiệu Suất Hoạt Động")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Hoàn thành đề nghị K/P/ĐV",
            f"{qttn_data['hieu_suat_hoat_dong']['ty_le_hoan_thanh_de_nghi']['value']}%",
            f"{qttn_data['hieu_suat_hoat_dong']['ty_le_hoan_thanh_de_nghi']['value'] - qttn_data['hieu_suat_hoat_dong']['ty_le_hoan_thanh_de_nghi']['target']:+}% vs target {qttn_data['hieu_suat_hoat_dong']['ty_le_hoan_thanh_de_nghi']['target']}%"
        )
    
    with col2:
        st.metric(
            "Sửa chữa qua điện thoại",
            f"{qttn_data['hieu_suat_hoat_dong']['ty_le_hoan_thanh_sua_chua']['value']}%",
            f"+{qttn_data['hieu_suat_hoat_dong']['ty_le_hoan_thanh_sua_chua']['value'] - qttn_data['hieu_suat_hoat_dong']['ty_le_hoan_thanh_sua_chua']['target']:+}% vs target"
        )
    
    with col3:
        st.metric(
            "Hoàn thành kế hoạch",
            f"{qttn_data['hieu_suat_hoat_dong']['ty_le_hoan_thanh_ke_hoach']['value']}%",
            f"{qttn_data['hieu_suat_hoat_dong']['ty_le_hoan_thanh_ke_hoach']['value'] - qttn_data['hieu_suat_hoat_dong']['ty_le_hoan_thanh_ke_hoach']['target']:+}% vs target"
        )
    
    with col4:
        st.metric(
            "Hoàn thành mua sắm",
            f"{qttn_data['hieu_suat_hoat_dong']['ty_le_hoan_thanh_mua_sam']['value']}%",
            f"{qttn_data['hieu_suat_hoat_dong']['ty_le_hoan_thanh_mua_sam']['value'] - qttn_data['hieu_suat_hoat_dong']['ty_le_hoan_thanh_mua_sam']['target']:+}% vs target"
        )
    
    # Sub-tabs cho từng mảng hoạt động
    subtab1, subtab2, subtab3, subtab4 = st.tabs([
        "📈 Hiệu Suất Hoạt Động", "♻️ Quản Lý Chất Thải", "⚡ Kho Khí Y Tế", "📊 Phân Tích Theo Tháng"
    ])
    
    # Tab Hiệu suất hoạt động
    with subtab1:
        st.header("📈 Hiệu Suất Hoạt Động 6 Tháng Đầu Năm")
        
        # Biểu đồ so sánh với target
        col1, col2 = st.columns(2)
        
        with col1:
            # Gauge chart cho các KPI
            performance_data = pd.DataFrame({
                'Chỉ tiêu': ['Đề nghị K/P/ĐV', 'Sửa chữa ĐT', 'Kế hoạch 6T', 'Mua sắm 6T'],
                'Thực tế (%)': [
                    qttn_data['hieu_suat_hoat_dong']['ty_le_hoan_thanh_de_nghi']['value'],
                    qttn_data['hieu_suat_hoat_dong']['ty_le_hoan_thanh_sua_chua']['value'],
                    qttn_data['hieu_suat_hoat_dong']['ty_le_hoan_thanh_ke_hoach']['value'],
                    qttn_data['hieu_suat_hoat_dong']['ty_le_hoan_thanh_mua_sam']['value']
                ],
                'Mục tiêu (%)': [
                    qttn_data['hieu_suat_hoat_dong']['ty_le_hoan_thanh_de_nghi']['target'],
                    qttn_data['hieu_suat_hoat_dong']['ty_le_hoan_thanh_sua_chua']['target'],
                    qttn_data['hieu_suat_hoat_dong']['ty_le_hoan_thanh_ke_hoach']['target'],
                    qttn_data['hieu_suat_hoat_dong']['ty_le_hoan_thanh_mua_sam']['target']
                ]
            })
            
            fig_performance = px.bar(performance_data, x='Chỉ tiêu', y=['Thực tế (%)', 'Mục tiêu (%)'],
                                    title="So sánh thực tế vs mục tiêu",
                                    barmode='group',
                                    color_discrete_sequence=['#2E8B57', '#FFB6C1'])
            fig_performance.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_performance, use_container_width=True)
        
        with col2:
            # Biểu đồ radar cho hiệu suất tổng thể
            categories = ['Đề nghị K/P/ĐV', 'Sửa chữa ĐT', 'Kế hoạch 6T', 'Mua sắm 6T']
            values = [
                qttn_data['hieu_suat_hoat_dong']['ty_le_hoan_thanh_de_nghi']['value'],
                qttn_data['hieu_suat_hoat_dong']['ty_le_hoan_thanh_sua_chua']['value'],
                qttn_data['hieu_suat_hoat_dong']['ty_le_hoan_thanh_ke_hoach']['value'],
                qttn_data['hieu_suat_hoat_dong']['ty_le_hoan_thanh_mua_sam']['value']
            ]
            targets = [
                qttn_data['hieu_suat_hoat_dong']['ty_le_hoan_thanh_de_nghi']['target'],
                qttn_data['hieu_suat_hoat_dong']['ty_le_hoan_thanh_sua_chua']['target'],
                qttn_data['hieu_suat_hoat_dong']['ty_le_hoan_thanh_ke_hoach']['target'],
                qttn_data['hieu_suat_hoat_dong']['ty_le_hoan_thanh_mua_sam']['target']
            ]
            
            fig_radar = go.Figure()
            
            fig_radar.add_trace(go.Scatterpolar(
                r=values + [values[0]],  # Close the polygon
                theta=categories + [categories[0]],
                fill='toself',
                name='Thực tế',
                fillcolor='rgba(46, 139, 87, 0.3)',
                line_color='#2E8B57'
            ))
            
            fig_radar.add_trace(go.Scatterpolar(
                r=targets + [targets[0]],
                theta=categories + [categories[0]],
                fill='toself',
                name='Mục tiêu',
                fillcolor='rgba(255, 182, 193, 0.3)',
                line_color='#FFB6C1'
            ))
            
            fig_radar.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, 100]
                    )),
                showlegend=True,
                title="Biểu đồ radar hiệu suất tổng thể"
            )
            st.plotly_chart(fig_radar, use_container_width=True)
        
        # Phân tích chi tiết
        st.subheader("🔍 Phân Tích Chi Tiết Hiệu Suất")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.success("✅ **Đạt/Vượt mục tiêu:**")
            if qttn_data['hieu_suat_hoat_dong']['ty_le_hoan_thanh_sua_chua']['value'] >= qttn_data['hieu_suat_hoat_dong']['ty_le_hoan_thanh_sua_chua']['target']:
                st.write("• **Sửa chữa qua điện thoại: 100%** (Vượt 5%)")
            if qttn_data['hieu_suat_hoat_dong']['ty_le_hoan_thanh_mua_sam']['value'] >= qttn_data['hieu_suat_hoat_dong']['ty_le_hoan_thanh_mua_sam']['target']:
                st.write("• **Mua sắm 6 tháng: 78%** (Đạt mục tiêu)")
        
        with col2:
            st.warning("⚠️ **Cần cải thiện:**")
            if qttn_data['hieu_suat_hoat_dong']['ty_le_hoan_thanh_de_nghi']['value'] < qttn_data['hieu_suat_hoat_dong']['ty_le_hoan_thanh_de_nghi']['target']:
                st.write("• **Đề nghị K/P/ĐV: 63%** (Thiếu 17%)")
            if qttn_data['hieu_suat_hoat_dong']['ty_le_hoan_thanh_ke_hoach']['value'] < qttn_data['hieu_suat_hoat_dong']['ty_le_hoan_thanh_ke_hoach']['target']:
                st.write("• **Kế hoạch 6 tháng: 70%** (Thiếu 15%)")
        
        # Bảng chi tiết
        st.subheader("📋 Bảng Chi Tiết Hiệu Suất Hoạt Động")
        
        performance_detail = pd.DataFrame({
            'STT': [1, 2, 3, 4],
            'Chỉ tiêu': [
                'Tỷ lệ hoàn thành đề nghị của Khoa/Phòng/Đơn vị',
                'Tỷ lệ hoàn thành sửa chữa theo yêu cầu qua điện thoại',
                'Tỷ lệ hoàn thành kế hoạch hoạt động 6 tháng đầu năm',
                'Tỷ lệ hoàn thành kế hoạch mua sắm 6 tháng đầu năm'
            ],
            'Thực tế': ['63%', '100%', '70%', '78%'],
            'Mục tiêu': ['80%', '95%', '85%', '80%'],
            'Chênh lệch': ['-17%', '+5%', '-15%', '-2%'],
            'Đánh giá': ['Cần cải thiện', 'Xuất sắc', 'Cần cải thiện', 'Gần đạt']
        })
        
        st.dataframe(performance_detail, use_container_width=True)
    
    # Tab Quản lý chất thải
    with subtab2:
        st.header("♻️ Quản Lý Chất Thải Bệnh Viện")
        
        # Metrics chất thải
        tong_chat_thai = qttn_data['chat_thai']['rac_thai_thong_thuong']['value'] + qttn_data['chat_thai']['chat_thai_nguy_hai_lay_nhiem']['value'] + qttn_data['chat_thai']['chat_thai_nguy_hai']['value']
        tong_tai_che = qttn_data['chat_thai']['tai_che']['giay']['value'] + qttn_data['chat_thai']['tai_che']['nhua']['value']
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Tổng chất thải",
                f"{tong_chat_thai:.1f}",
                "tấn"
            )
        
        with col2:
            st.metric(
                "Rác thải thông thường",
                f"{qttn_data['chat_thai']['rac_thai_thong_thuong']['value']}",
                f"{(qttn_data['chat_thai']['rac_thai_thong_thuong']['value']/tong_chat_thai*100):.1f}%"
            )
        
        with col3:
            st.metric(
                "Chất thải nguy hại",
                f"{qttn_data['chat_thai']['chat_thai_nguy_hai_lay_nhiem']['value'] + qttn_data['chat_thai']['chat_thai_nguy_hai']['value']:.1f}",
                f"{((qttn_data['chat_thai']['chat_thai_nguy_hai_lay_nhiem']['value'] + qttn_data['chat_thai']['chat_thai_nguy_hai']['value'])/tong_chat_thai*100):.1f}%"
            )
        
        with col4:
            st.metric(
                "Chất thải tái chế",
                f"{tong_tai_che:.1f}",
                f"Tỷ lệ: {(tong_tai_che/tong_chat_thai*100):.1f}%"
            )
        
        # Biểu đồ phân tích chất thải
        col1, col2 = st.columns(2)
        
        with col1:
            # Pie chart phân loại chất thải
            waste_data = pd.DataFrame({
                'Loại chất thải': [
                    'Rác thải thông thường',
                    'Chất thải nguy hại lây nhiễm', 
                    'Chất thải nguy hại',
                    'Tái chế (Giấy)',
                    'Tái chế (Nhựa)'
                ],
                'Khối lượng (tấn)': [
                    qttn_data['chat_thai']['rac_thai_thong_thuong']['value'],
                    qttn_data['chat_thai']['chat_thai_nguy_hai_lay_nhiem']['value'],
                    qttn_data['chat_thai']['chat_thai_nguy_hai']['value'],
                    qttn_data['chat_thai']['tai_che']['giay']['value'],
                    qttn_data['chat_thai']['tai_che']['nhua']['value']
                ]
            })
            
            fig_waste = px.pie(waste_data, values='Khối lượng (tấn)', names='Loại chất thải',
                              title="Phân loại chất thải theo khối lượng",
                              color_discrete_sequence=['#90EE90', '#FF6B6B', '#DC143C', '#4169E1', '#00CED1'])
            fig_waste.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_waste, use_container_width=True)
        
        with col2:
            # Bar chart so sánh
            waste_comparison = pd.DataFrame({
                'Phân loại': ['Chất thải thông thường', 'Chất thải nguy hại', 'Tái chế'],
                'Khối lượng (tấn)': [
                    qttn_data['chat_thai']['rac_thai_thong_thuong']['value'],
                    qttn_data['chat_thai']['chat_thai_nguy_hai_lay_nhiem']['value'] + qttn_data['chat_thai']['chat_thai_nguy_hai']['value'],
                    tong_tai_che
                ],
                'Màu sắc': ['Xanh lá', 'Đỏ', 'Xanh dương']
            })
            
            fig_comparison = px.bar(waste_comparison, x='Phân loại', y='Khối lượng (tấn)',
                                   title="So sánh khối lượng chất thải",
                                   color='Phân loại',
                                   color_discrete_sequence=['#90EE90', '#FF6B6B', '#4169E1'])
            fig_comparison.update_traces(text=waste_comparison['Khối lượng (tấn)'], textposition='outside')
            st.plotly_chart(fig_comparison, use_container_width=True)
        
        # Xu hướng chất thải (mock data theo tháng)
        st.subheader("📈 Xu Hướng Chất Thải 6 Tháng")
        
        months = ['Tháng 1', 'Tháng 2', 'Tháng 3', 'Tháng 4', 'Tháng 5', 'Tháng 6']
        
        # Chia đều khối lượng chất thải cho 6 tháng với một chút biến động
        rac_thuong_trend = [105, 110, 108, 112, 106, 114]  # Tổng ≈ 655
        nguy_hai_trend = [38, 39, 37, 40, 36, 41]  # Tổng ≈ 231.2
        tai_che_trend = [16, 17, 15, 18, 16, 17]  # Tổng ≈ 99.3
        
        fig_waste_trend = go.Figure()
        fig_waste_trend.add_trace(go.Scatter(x=months, y=rac_thuong_trend,
                                            mode='lines+markers', name='Rác thải thông thường',
                                            line=dict(color='#90EE90', width=3)))
        fig_waste_trend.add_trace(go.Scatter(x=months, y=nguy_hai_trend,
                                            mode='lines+markers', name='Chất thải nguy hại',
                                            line=dict(color='#FF6B6B', width=3)))
        fig_waste_trend.add_trace(go.Scatter(x=months, y=tai_che_trend,
                                            mode='lines+markers', name='Tái chế',
                                            line=dict(color='#4169E1', width=3)))
        
        fig_waste_trend.update_layout(
            title="Xu hướng chất thải theo tháng (tấn)",
            xaxis_title="Tháng",
            yaxis_title="Khối lượng (tấn)",
            height=400
        )
        st.plotly_chart(fig_waste_trend, use_container_width=True)
        
        # Insights và khuyến nghị
        col1, col2 = st.columns(2)
        
        with col1:
            st.info("📊 **Phân tích:**")
            ty_le_tai_che = (tong_tai_che/tong_chat_thai*100)
            st.write(f"• Tỷ lệ tái chế: **{ty_le_tai_che:.1f}%**")
            st.write(f"• Rác thông thường chiếm **{(qttn_data['chat_thai']['rac_thai_thong_thuong']['value']/tong_chat_thai*100):.1f}%**")
            st.write(f"• Chất thải nguy hại: **{((qttn_data['chat_thai']['chat_thai_nguy_hai_lay_nhiem']['value'] + qttn_data['chat_thai']['chat_thai_nguy_hai']['value'])/tong_chat_thai*100):.1f}%**")
            st.write(f"• TB chất thải/tháng: **{tong_chat_thai/6:.1f} tấn**")
        
        with col2:
            st.success("🎯 **Khuyến nghị:**")
            st.write("• Tăng cường phân loại rác tại nguồn")
            st.write("• Mở rộng chương trình tái chế")
            st.write("• Giảm thiểu chất thải nguy hại")
            st.write("• Đào tạo ý thức bảo vệ môi trường")
    
    # Tab Kho khí y tế
    with subtab3:
        st.header("⚡ Quản Lý Kho Khí Y Tế")
        
        # Metrics kho khí y tế
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Tồn đầu kỳ",
                f"{qttn_data['kho_khi_y_te']['tong_hop']['ton_dau_ky']/1e6:.1f}M",
                "VNĐ"
            )
        
        with col2:
            st.metric(
                "Nhập trong kỳ",
                f"{qttn_data['kho_khi_y_te']['tong_hop']['nhap_trong_ky']/1e9:.1f}B",
                "VNĐ"
            )
        
        with col3:
            st.metric(
                "Xuất trong kỳ", 
                f"{qttn_data['kho_khi_y_te']['tong_hop']['xuat_trong_ky']/1e9:.1f}B",
                "VNĐ"
            )
        
        with col4:
            st.metric(
                "Tồn cuối kỳ",
                f"{qttn_data['kho_khi_y_te']['tong_hop']['ton_cuoi_ky']/1e6:.1f}M",
                f"{((qttn_data['kho_khi_y_te']['tong_hop']['ton_cuoi_ky'] - qttn_data['kho_khi_y_te']['tong_hop']['ton_dau_ky'])/qttn_data['kho_khi_y_te']['tong_hop']['ton_dau_ky']*100):+.1f}%"
            )
        
        # Biểu đồ nhập xuất tồn
        col1, col2 = st.columns(2)
        
        with col1:
            # Biểu đồ tổng quan nhập xuất tồn
            nxt_data = pd.DataFrame({
                'Hoạt động': ['Tồn đầu kỳ', 'Nhập trong kỳ', 'Xuất trong kỳ', 'Tồn cuối kỳ'],
                'Giá trị (tỷ VNĐ)': [
                    qttn_data['kho_khi_y_te']['tong_hop']['ton_dau_ky']/1e9,
                    qttn_data['kho_khi_y_te']['tong_hop']['nhap_trong_ky']/1e9,
                    qttn_data['kho_khi_y_te']['tong_hop']['xuat_trong_ky']/1e9,
                    qttn_data['kho_khi_y_te']['tong_hop']['ton_cuoi_ky']/1e9
                ]
            })
            
            fig_nxt = px.bar(nxt_data, x='Hoạt động', y='Giá trị (tỷ VNĐ)',
                            title="Tổng quan Nhập-Xuất-Tồn kho khí y tế",
                            color='Giá trị (tỷ VNĐ)',
                            color_continuous_scale='Teal',
                            text='Giá trị (tỷ VNĐ)')
            fig_nxt.update_traces(texttemplate='%{text:.2f}B', textposition='outside')
            fig_nxt.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_nxt, use_container_width=True)
        
        with col2:
            # Pie chart cơ cấu tồn kho cuối kỳ theo loại khí
            inventory_structure = pd.DataFrame({
                'Loại khí': ['CO2 25kg', 'CO2 8kg', 'Nitơ 6m³', 'Oxy lớn 6m³', 'Argon 1m³', 'Oxy nhỏ 2m³'],
                'Giá trị (triệu VNĐ)': [
                    qttn_data['kho_khi_y_te']['chi_tiet_ton_cuoi_ky']['co2_25kg']['value']/1e6,
                    qttn_data['kho_khi_y_te']['chi_tiet_ton_cuoi_ky']['co2_8kg']['value']/1e6,
                    qttn_data['kho_khi_y_te']['chi_tiet_ton_cuoi_ky']['nitro_6m3']['value']/1e6,
                    qttn_data['kho_khi_y_te']['chi_tiet_ton_cuoi_ky']['oxy_lon_6m3']['value']/1e6,
                    qttn_data['kho_khi_y_te']['chi_tiet_ton_cuoi_ky']['argon_1m3']['value']/1e6,
                    qttn_data['kho_khi_y_te']['chi_tiet_ton_cuoi_ky']['oxy_nho_2m3']['value']/1e6
                ]
            })
            
            fig_structure = px.pie(inventory_structure, values='Giá trị (triệu VNĐ)', names='Loại khí',
                                  title="Cơ cấu tồn kho cuối kỳ theo loại khí",
                                  color_discrete_sequence=px.colors.qualitative.Set3)
            fig_structure.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_structure, use_container_width=True)
        
        # Chi tiết tồn kho theo từng loại
        st.subheader("📦 Chi Tiết Tồn Kho Cuối Kỳ")
        
        inventory_detail = pd.DataFrame({
            'STT': [1, 2, 3, 4, 5, 6],
            'Loại khí y tế': [
                'Argon loại 1m³/bình',
                'CO2 loại 25kg/bình', 
                'CO2 loại 8kg/bình',
                'Nitơ khí loại 6m³/bình',
                'Oxy khí loại lớn 6m³/bình',
                'Oxy khí loại nhỏ 2m³/bình'
            ],
            'Số lượng (bình)': [
                qttn_data['kho_khi_y_te']['chi_tiet_ton_cuoi_ky']['argon_1m3']['quantity'],
                qttn_data['kho_khi_y_te']['chi_tiet_ton_cuoi_ky']['co2_25kg']['quantity'],
                qttn_data['kho_khi_y_te']['chi_tiet_ton_cuoi_ky']['co2_8kg']['quantity'],
                qttn_data['kho_khi_y_te']['chi_tiet_ton_cuoi_ky']['nitro_6m3']['quantity'],
                qttn_data['kho_khi_y_te']['chi_tiet_ton_cuoi_ky']['oxy_lon_6m3']['quantity'],
                qttn_data['kho_khi_y_te']['chi_tiet_ton_cuoi_ky']['oxy_nho_2m3']['quantity']
            ],
            'Giá trị (VNĐ)': [
                f"{qttn_data['kho_khi_y_te']['chi_tiet_ton_cuoi_ky']['argon_1m3']['value']:,}",
                f"{qttn_data['kho_khi_y_te']['chi_tiet_ton_cuoi_ky']['co2_25kg']['value']:,}",
                f"{qttn_data['kho_khi_y_te']['chi_tiet_ton_cuoi_ky']['co2_8kg']['value']:,}",
                f"{qttn_data['kho_khi_y_te']['chi_tiet_ton_cuoi_ky']['nitro_6m3']['value']:,}",
                f"{qttn_data['kho_khi_y_te']['chi_tiet_ton_cuoi_ky']['oxy_lon_6m3']['value']:,}",
                f"{qttn_data['kho_khi_y_te']['chi_tiet_ton_cuoi_ky']['oxy_nho_2m3']['value']:,}"
            ],
            'Tỷ lệ (%)': [
                f"{(qttn_data['kho_khi_y_te']['chi_tiet_ton_cuoi_ky']['argon_1m3']['value']/qttn_data['kho_khi_y_te']['tong_hop']['ton_cuoi_ky']*100):.1f}%",
                f"{(qttn_data['kho_khi_y_te']['chi_tiet_ton_cuoi_ky']['co2_25kg']['value']/qttn_data['kho_khi_y_te']['tong_hop']['ton_cuoi_ky']*100):.1f}%",
                f"{(qttn_data['kho_khi_y_te']['chi_tiet_ton_cuoi_ky']['co2_8kg']['value']/qttn_data['kho_khi_y_te']['tong_hop']['ton_cuoi_ky']*100):.1f}%",
                f"{(qttn_data['kho_khi_y_te']['chi_tiet_ton_cuoi_ky']['nitro_6m3']['value']/qttn_data['kho_khi_y_te']['tong_hop']['ton_cuoi_ky']*100):.1f}%",
                f"{(qttn_data['kho_khi_y_te']['chi_tiet_ton_cuoi_ky']['oxy_lon_6m3']['value']/qttn_data['kho_khi_y_te']['tong_hop']['ton_cuoi_ky']*100):.1f}%",
                f"{(qttn_data['kho_khi_y_te']['chi_tiet_ton_cuoi_ky']['oxy_nho_2m3']['value']/qttn_data['kho_khi_y_te']['tong_hop']['ton_cuoi_ky']*100):.1f}%"
            ]
        })
        
        st.dataframe(inventory_detail, use_container_width=True)
        
        # Phân tích hiệu quả kho
        col1, col2 = st.columns(2)
        
        with col1:
            st.info("📈 **Phân tích hiệu quả:**")
            ty_le_xuat_nhap = (qttn_data['kho_khi_y_te']['tong_hop']['xuat_trong_ky']/qttn_data['kho_khi_y_te']['tong_hop']['nhap_trong_ky']*100)
            st.write(f"• Tỷ lệ xuất/nhập: **{ty_le_xuat_nhap:.1f}%**")
            st.write(f"• Vòng quay kho: **{ty_le_xuat_nhap:.1f}%** (Tốt)")
            st.write(f"• CO2 25kg chiếm **{(qttn_data['kho_khi_y_te']['chi_tiet_ton_cuoi_ky']['co2_25kg']['value']/qttn_data['kho_khi_y_te']['tong_hop']['ton_cuoi_ky']*100):.1f}%** tồn kho")
            st.write(f"• Tồn kho tăng **{((qttn_data['kho_khi_y_te']['tong_hop']['ton_cuoi_ky'] - qttn_data['kho_khi_y_te']['tong_hop']['ton_dau_ky'])/qttn_data['kho_khi_y_te']['tong_hop']['ton_dau_ky']*100):+.1f}%**")
        
        with col2:
            st.success("🎯 **Khuyến nghị quản lý:**")
            st.write("• Tối ưu lượng tồn kho CO2")
            st.write("• Theo dõi chu kỳ sử dụng")
            st.write("• Cải thiện dự báo nhu cầu")
            st.write("• Kiểm tra định kỳ chất lượng khí")
    
    # Tab Phân tích theo tháng
    with subtab4:
        st.header("📊 Phân Tích Kho Khí Y Tế Theo Tháng")
        
        # Xu hướng nhập xuất tồn theo tháng
        months = ['Tháng 1', 'Tháng 2', 'Tháng 3', 'Tháng 4', 'Tháng 5', 'Tháng 6']
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Biểu đồ nhập xuất theo tháng
            fig_monthly_nxt = go.Figure()
            
            fig_monthly_nxt.add_trace(go.Scatter(
                x=months, 
                y=[x/1e6 for x in qttn_data['kho_khi_y_te']['theo_thang']['nhap']],
                mode='lines+markers', 
                name='Nhập kho',
                line=dict(color='#2E8B57', width=3),
                marker=dict(size=8)
            ))
            
            fig_monthly_nxt.add_trace(go.Scatter(
                x=months, 
                y=[x/1e6 for x in qttn_data['kho_khi_y_te']['theo_thang']['xuat']],
                mode='lines+markers', 
                name='Xuất kho',
                line=dict(color='#FF6B6B', width=3),
                marker=dict(size=8)
            ))
            
            fig_monthly_nxt.update_layout(
                title="Xu hướng nhập-xuất kho theo tháng",
                xaxis_title="Tháng",
                yaxis_title="Giá trị (triệu VNĐ)",
                height=400,
                hovermode='x unified'
            )
            st.plotly_chart(fig_monthly_nxt, use_container_width=True)
        
        with col2:
            # Biểu đồ tồn kho theo tháng
            fig_inventory_trend = go.Figure()
            
            fig_inventory_trend.add_trace(go.Scatter(
                x=months,
                y=[x/1e6 for x in qttn_data['kho_khi_y_te']['theo_thang']['ton_cuoi_ky']],
                mode='lines+markers+text',
                name='Tồn kho cuối kỳ',
                line=dict(color='#20B2AA', width=3),
                marker=dict(size=10),
                text=[f"{x/1e6:.1f}M" for x in qttn_data['kho_khi_y_te']['theo_thang']['ton_cuoi_ky']],
                textposition="top center"
            ))
            
            fig_inventory_trend.update_layout(
                title="Xu hướng tồn kho cuối kỳ theo tháng",
                xaxis_title="Tháng", 
                yaxis_title="Tồn kho (triệu VNĐ)",
                height=400
            )
            st.plotly_chart(fig_inventory_trend, use_container_width=True)
        
        # Bảng dữ liệu chi tiết theo tháng
        st.subheader("📋 Bảng Chi Tiết Nhập-Xuất-Tồn Theo Tháng")
        
        monthly_detail = pd.DataFrame({
            'Tháng': ['Tháng 1', 'Tháng 2', 'Tháng 3', 'Tháng 4', 'Tháng 5', 'Tháng 6'],
            'Tồn đầu kỳ (VNĐ)': [f"{x:,}" for x in qttn_data['kho_khi_y_te']['theo_thang']['ton_dau_ky']],
            'Nhập trong kỳ (VNĐ)': [f"{x:,}" for x in qttn_data['kho_khi_y_te']['theo_thang']['nhap']],
            'Xuất trong kỳ (VNĐ)': [f"{x:,}" for x in qttn_data['kho_khi_y_te']['theo_thang']['xuat']],
            'Tồn cuối kỳ (VNĐ)': [f"{x:,}" for x in qttn_data['kho_khi_y_te']['theo_thang']['ton_cuoi_ky']],
            'Tỷ lệ xuất/nhập (%)': [
                f"{(qttn_data['kho_khi_y_te']['theo_thang']['xuat'][i]/qttn_data['kho_khi_y_te']['theo_thang']['nhap'][i]*100):.1f}%"
                for i in range(6)
            ]
        })
        
        st.dataframe(monthly_detail, use_container_width=True)
        
        # Phân tích xu hướng
        st.subheader("📈 Phân Tích Xu Hướng & Insights")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.info("🔍 **Phân tích xu hướng:**")
            # Tìm tháng có nhập cao nhất và thấp nhất
            max_nhap_idx = qttn_data['kho_khi_y_te']['theo_thang']['nhap'].index(max(qttn_data['kho_khi_y_te']['theo_thang']['nhap']))
            min_nhap_idx = qttn_data['kho_khi_y_te']['theo_thang']['nhap'].index(min(qttn_data['kho_khi_y_te']['theo_thang']['nhap']))
            
            st.write(f"• Nhập cao nhất: **Tháng {max_nhap_idx + 1}** ({qttn_data['kho_khi_y_te']['theo_thang']['nhap'][max_nhap_idx]/1e6:.1f}M VNĐ)")
            st.write(f"• Nhập thấp nhất: **Tháng {min_nhap_idx + 1}** ({qttn_data['kho_khi_y_te']['theo_thang']['nhap'][min_nhap_idx]/1e6:.1f}M VNĐ)")
            
            # Tính TB nhập/xuất hàng tháng
            avg_nhap = sum(qttn_data['kho_khi_y_te']['theo_thang']['nhap']) / 6
            avg_xuat = sum(qttn_data['kho_khi_y_te']['theo_thang']['xuat']) / 6
            st.write(f"• TB nhập/tháng: **{avg_nhap/1e6:.1f}M VNĐ**")
            st.write(f"• TB xuất/tháng: **{avg_xuat/1e6:.1f}M VNĐ**")
        
        with col2:
            st.success("💡 **Khuyến nghị:**")
            st.write("• Duy trì mức tồn kho ổn định 20-25M VNĐ")
            st.write("• Tháng 4 có nhu cầu cao, cần dự trù tốt")
            st.write("• Cân bằng nhập-xuất để tránh tồn đọng")
            st.write("• Theo dõi chu kỳ sử dụng theo mùa")
        
        # Biểu đồ combo cuối cùng
        st.subheader("📊 Biểu Đồ Tổng Hợp Hoạt Động Kho")
        
        fig_combo = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Nhập - Xuất kho theo tháng (triệu VNĐ)', 'Tồn kho cuối kỳ theo tháng (triệu VNĐ)'),
            vertical_spacing=0.1
        )
        
        # Nhập xuất
        fig_combo.add_trace(
            go.Bar(x=months, y=[x/1e6 for x in qttn_data['kho_khi_y_te']['theo_thang']['nhap']], 
                   name='Nhập kho', marker_color='#2E8B57'),
            row=1, col=1
        )
        fig_combo.add_trace(
            go.Bar(x=months, y=[x/1e6 for x in qttn_data['kho_khi_y_te']['theo_thang']['xuat']], 
                   name='Xuất kho', marker_color='#FF6B6B'),
            row=1, col=1
        )
        
        # Tồn kho
        fig_combo.add_trace(
            go.Scatter(x=months, y=[x/1e6 for x in qttn_data['kho_khi_y_te']['theo_thang']['ton_cuoi_ky']], 
                      mode='lines+markers', name='Tồn cuối kỳ', 
                      line=dict(color='#20B2AA', width=3), marker=dict(size=8)),
            row=2, col=1
        )
        
        fig_combo.update_layout(height=700, showlegend=True, 
                               title_text="Tổng Hợp Hoạt Động Kho Khí Y Tế 6 Tháng Đầu Năm 2025")
        st.plotly_chart(fig_combo, use_container_width=True)
    
    # Tổng kết và insights chung
    st.subheader("💡 Tổng kết hoạt động Quản trị Tòa nhà")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.success("🎉 **Thành tựu nổi bật:**")
        st.write("• **100% hoàn thành** sửa chữa qua điện thoại")
        st.write(f"• Quản lý **{tong_chat_thai:.1f} tấn chất thải** an toàn")
        st.write(f"• Vận hành kho khí y tế **{qttn_data['kho_khi_y_te']['tong_hop']['nhap_trong_ky']/1e9:.1f} tỷ VNĐ**")
        st.write(f"• Tỷ lệ tái chế đạt **{(tong_tai_che/tong_chat_thai*100):.1f}%**")
        st.write("• Đảm bảo cung cấp khí y tế liên tục")
        st.write("• Tuân thủ quy định môi trường")
    
    with col2:
        st.info("🎯 **Kế hoạch cải thiện:**")
        st.write("• **Nâng cao tỷ lệ hoàn thành đề nghị** lên 80%")
        st.write("• **Cải thiện kế hoạch hoạt động** đạt 85%")
        st.write("• **Tối ưu hóa quản lý tồn kho** khí y tế")
        st.write("• **Mở rộng chương trình tái chế** lên 15%")
        st.write("• **Số hóa quy trình** quản lý tòa nhà")
        st.write("• **Nâng cao năng lực** dự báo nhu cầu")

# Footer
st.markdown("---")
st.markdown(f"""
<div style='text-align: center; color: gray; padding: 20px;'>
    <p>🏥 Dashboard Bệnh Viện Multi-Department - VTTB | KSKTYC | CNTT | CTXH | TTTT 📊 Dữ liệu 6 tháng đầu năm 2025</p>
    <p>Cập nhật lần cuối: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
</div>
""", unsafe_allow_html=True)
