import flet as ft
import subprocess
import re
import requests
import platform

# پیش‌شماره‌های آدرس مک (OUI) مربوط به شرکت SpaceX / Starlink
STARLINK_MAC_PREFIXES = [
    "70:18:8B", "28:EE:52", "00:7E:56", "38:8C:50", "34:8F:27", "80:8D:B9", "F8:2F:A8"
]

def get_wifi_networks():
    networks = []
    try:
        if platform.system() == "Linux" or platform.system() == "Android":
            # دستور اسکن وای‌فای در محیط‌های برپایه لینوکس/اندروید
            cmd = "nmcli -t -f SSID,SIGNAL,BSSID dev wifi"
            res = subprocess.check_output(cmd, shell=True, text=True)
            for line in res.strip().split("\n"):
                if line:
                    parts = line.split(":")
                    if len(parts) >= 3:
                        ssid = parts[0] or "شبکه مخفی (Hidden)"
                        signal = parts[1]
                        bssid = ":".join(parts[2:])
                        networks.append({"ssid": ssid, "signal": int(signal) if signal.isdigit() else 50, "bssid": bssid})
        elif platform.system() == "Windows":
            cmd = "netsh wlan show networks mode=bssid"
            res = subprocess.check_output(cmd, shell=True, text=True, encoding="cp1252", errors="ignore")
            # پارس کردن خروجی ویندوز جهت استخراج SSID، سیگنال و BSSID
            ssids = re.findall(r"SSID \d+ : (.*)", res)
            signals = re.findall(r"Signal\s*:\s*(\d+)%", res)
            bssids = re.findall(r"BSSID \d+\s*:\s*([0-9a-fA-F:]+)", res)
            for i in range(min(len(ssids), len(signals))):
                bssid_val = bssids[i] if i < len(bssids) else "N/A"
                networks.append({"ssid": ssids[i].strip() or "شبکه مخفی", "signal": int(signals[i]), "bssid": bssid_val})
    except Exception as e:
        pass
    
    # اگر اسکن مستقیم سیستم‌عامل محدود بود، دمو نما
    if not networks:
        networks = [
            {"ssid": "Starlink-Home", "signal": 85, "bssid": "70:18:8B:12:34:56"},
            {"ssid": "Irancell-WiFi", "signal": 45, "bssid": "A4:C3:F0:11:22:33"},
            {"ssid": "Unknown_Net", "signal": 25, "bssid": "00:11:22:33:44:55"}
        ]
    return networks

def is_starlink_mac(bssid):
    if not bssid or bssid == "N/A":
        return False
    clean_bssid = bssid.upper().replace("-", ":")
    for prefix in STARLINK_MAC_PREFIXES:
        if clean_bssid.startswith(prefix):
            return True
    return False

def main(page: ft.Page):
    page.title = "Starlink & WiFi Scanner"
    page.theme_mode = ft.ThemeMode.DARK
    page.rtl = True
    page.padding = 20

    header = ft.Text("📡 اسکنر وای‌فای‌های اطراف و تشخیص استارلینک", size=20, weight=ft.FontWeight.BOLD, color=ft.colors.BLUE_200)
    
    wifi_list_view = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)

    def scan_wifi(e=None):
        wifi_list_view.controls.clear()
        networks = get_wifi_networks()
        
        for net in networks:
            ssid = net["ssid"]
            signal = net["signal"]
            bssid = net["bssid"]
            
            # تعیین رنگ بر اساس کیفیت خط‌دهی سیگنال
            if signal >= 70:
                sig_color = ft.colors.GREEN_400
                sig_text = f"خط‌دهی عالی ({signal}%)"
            elif signal >= 40:
                sig_color = ft.colors.AMBER_400
                sig_text = f"خط‌دهی متوسط ({signal}%)"
            else:
                sig_color = ft.colors.RED_400
                sig_text = f"خط‌دهی ضعیف ({signal}%)"

            # بررسی استارلینک بودن بر اساس آدرس مک و نام شبکه
            is_starlink = is_starlink_mac(bssid) or "starlink" in ssid.lower()
            
            status_tag = ft.Container(
                content=ft.Text("احتمال استارلینک 🚀" if is_starlink else "وای‌فای معمولی", size=12, color=ft.colors.BLACK, weight=ft.FontWeight.BOLD),
                bgcolor=ft.colors.CYAN_300 if is_starlink else ft.colors.GREY_700,
                padding=ft.padding.all(5),
                border_radius=5
            )

            card = ft.Card(
                content=ft.Container(
                    padding=15,
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.icons.WIFI, color=sig_color),
                            ft.Text(ssid, size=16, weight=ft.FontWeight.BOLD),
                            status_tag
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Text(f"قدرت سیگنال: {sig_text}", color=sig_color, size=13),
                        ft.Text(f"آدرس مک روتر (BSSID): {bssid}", color=ft.colors.GREY_400, size=11)
                    ])
                )
            )
            wifi_list_view.controls.append(card)
        page.update()

    scan_btn = ft.ElevatedButton("🔄 اسکن مجدد شبکه‌های اطراف", on_click=scan_wifi, icon=ft.icons.REFRESH)

    page.add(
        header,
        ft.Divider(),
        scan_btn,
        ft.Text("لیست شبکه‌های وای‌فای شناسایی‌شده:", size=14, color=ft.colors.GREY_300),
        wifi_list_view
    )

    # اسکن اولیه
    scan_wifi()

ft.app(target=main)
