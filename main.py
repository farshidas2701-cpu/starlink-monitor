import flet as ft
import subprocess
import re
import platform

# پیش‌شماره‌های آدرس مک (OUI) مربوط به شرکت SpaceX / Starlink
STARLINK_MAC_PREFIXES = [
    "70:18:8B", "28:EE:52", "00:7E:56", "38:8C:50", "34:8F:27", "80:8D:B9", "F8:2F:A8"
]

# پسوردهای اختصاصی
ADMIN_PASSWORD = "f09931807880F"
USER_PASSWORD = "0011300"

def get_wifi_networks():
    networks = []
    try:
        if platform.system() in ["Linux", "Android"]:
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
            ssids = re.findall(r"SSID \d+ : (.*)", res)
            signals = re.findall(r"Signal\s*:\s*(\d+)%", res)
            bssids = re.findall(r"BSSID \d+\s*:\s*([0-9a-fA-F:]+)", res)
            for i in range(min(len(ssids), len(signals))):
                bssid_val = bssids[i] if i < len(bssids) else "N/A"
                networks.append({"ssid": ssids[i].strip() or "شبکه مخفی", "signal": int(signals[i]), "bssid": bssid_val})
    except Exception:
        pass
    
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
    page.title = "سامانه پایش استارلینک"
    page.theme_mode = ft.ThemeMode.DARK
    page.rtl = True
    page.padding = 20

    # ----- عناصر صفحه ورود -----
    user_pass_input = ft.TextField(label="رمز ورود کاربران", password=True, can_reveal_password=True, width=280)
    admin_pass_input = ft.TextField(label="رمز ورود ادمین", password=True, can_reveal_password=True, width=280)
    login_err = ft.Text("", color=ft.colors.RED_400, size=13)

    def check_user_login(e):
        if user_pass_input.value.strip() == USER_PASSWORD:
            show_user_panel()
        else:
            login_err.value = "رمز ورود کاربران اشتباه است!"
            page.update()

    def check_admin_login(e):
        if admin_pass_input.value.strip() == ADMIN_PASSWORD:
            show_admin_panel()
        else:
            login_err.value = "رمز ورود ادمین اشتباه است!"
            page.update()

    # طراحی دو کارت جداگانه برای ورود
    user_box = ft.Container(
        content=ft.Column([
            ft.Text("🔑 ورود کاربران", size=18, weight=ft.FontWeight.BOLD, color=ft.colors.BLUE_200),
            user_pass_input,
            ft.ElevatedButton("ورود کاربر", on_click=check_user_login, icon=ft.icons.LOGIN, bgcolor=ft.colors.BLUE_600, color=ft.colors.WHITE)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
        padding=15,
        border=ft.border.all(1, ft.colors.BLUE_400),
        border_radius=10
    )

    admin_box = ft.Container(
        content=ft.Column([
            ft.Text("🔐 ورود ادمین", size=18, weight=ft.FontWeight.BOLD, color=ft.colors.RED_200),
            admin_pass_input,
            ft.ElevatedButton("ورود ادمین", on_click=check_admin_login, icon=ft.icons.ADMIN_PANEL_SETTINGS, bgcolor=ft.colors.RED_700, color=ft.colors.WHITE)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
        padding=15,
        border=ft.border.all(1, ft.colors.RED_400),
        border_radius=10
    )

    login_view = ft.Column(
        [
            ft.Text("⚡ سامانه پایش و شناسایی استارلینک", size=20, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            ft.ResponsiveRow([
                ft.Column([user_box], col={"sm": 12, "md": 6}),
                ft.Column([admin_box], col={"sm": 12, "md": 6}),
            ], spacing=20),
            login_err
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=20
    )

    # ----- صفحه پنل کاربران -----
    wifi_list_view = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)

    def scan_wifi(e=None):
        wifi_list_view.controls.clear()
        networks = get_wifi_networks()
        for net in networks:
            ssid = net["ssid"]
            signal = net["signal"]
            bssid = net["bssid"]
            
            if signal >= 70:
                sig_color = ft.colors.GREEN_400
                sig_text = f"خط‌دهی عالی ({signal}%)"
            elif signal >= 40:
                sig_color = ft.colors.AMBER_400
                sig_text = f"خط‌دهی متوسط ({signal}%)"
            else:
                sig_color = ft.colors.RED_400
                sig_text = f"خط‌دهی ضعیف ({signal}%)"

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

    def logout(e):
        page.controls.clear()
        user_pass_input.value = ""
        admin_pass_input.value = ""
        login_err.value = ""
        page.add(login_view)
        page.update()

    user_view = ft.Column([
        ft.Row([
            ft.Text("📡 اسکنر وای‌فای‌های اطراف", size=18, weight=ft.FontWeight.BOLD, color=ft.colors.BLUE_200),
            ft.IconButton(ft.icons.LOGOUT, on_click=logout, tooltip="خروج")
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Divider(),
        ft.ElevatedButton("🔄 اسکن مجدد شبکه‌های اطراف", on_click=scan_wifi, icon=ft.icons.REFRESH),
        ft.Text("لیست شبکه‌های وای‌فای شناسایی‌شده:", size=14, color=ft.colors.GREY_300),
        wifi_list_view
    ])

    # ----- صفحه پنل ادمین -----
    admin_view = ft.Column([
        ft.Row([
            ft.Text("🔐 پنل مدیریت سیستم", size=18, weight=ft.FontWeight.BOLD, color=ft.colors.RED_400),
            ft.IconButton(ft.icons.LOGOUT, on_click=logout, tooltip="خروج")
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Divider(),
        ft.Text("تنظیمات و دسترسی‌های مدیریت:", size=15, weight=ft.FontWeight.BOLD),
        ft.Text("• وضعیت سیستم: فعال", size=13),
        ft.Text("• رمز کاربران: 0011300", size=13),
        ft.Divider(),
        ft.ElevatedButton("ورود به محیط اسکنر شبکه", on_click=lambda e: show_user_panel(), icon=ft.icons.WIFI)
    ])

    def show_user_panel():
        page.controls.clear()
        page.add(user_view)
        scan_wifi()
        page.update()

    def show_admin_panel():
        page.controls.clear()
        page.add(admin_view)
        page.update()

    # صفحه شروع
    page.add(login_view)

ft.app(target=main)
