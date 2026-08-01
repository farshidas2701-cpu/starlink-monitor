import flet as ft
import subprocess
import re
import platform
import json
import urllib.request
import os
from datetime import datetime

# نسخه فعلی اپلیکیشن
CURRENT_VERSION = "2.1.0"
UPDATE_URL = "https://raw.githubusercontent.com/farshidas2701-cpu/starlink-monitor/main/version.json"

# پیش‌شماره‌های آدرس مک (OUI) مربوط به شرکت SpaceX / Starlink
INITIAL_STARLINK_PREFIXES = [
    "70:18:8B", "28:EE:52", "00:7E:56", "38:8C:50", "34:8F:27", "80:8D:B9", "F8:2F:A8", "70:2A:D5"
]

# حافظه مرکزی برنامه
app_state = {
    "admin_password": "f09931807880F",
    "user_password": "0011300",
    "history": [],
    "mac_prefixes": list(INITIAL_STARLINK_PREFIXES),
    "blacklist": [],
    "filter_starlink_only": False
}

def estimate_distance(signal_pct):
    if signal_pct >= 90:
        return "کمتر از ۲ متر (بسیار نزدیک)"
    elif signal_pct >= 70:
        return "حدود ۳ تا ۶ متر"
    elif signal_pct >= 40:
        return "حدود ۷ تا ۱۵ متر"
    else:
        return "بیش از ۱۵ متر (دور)"

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
    
    # شبکه‌های نمونه در صورت عدم دسترسی سخت‌افزاری مستقیم
    if not networks:
        networks = [
            {"ssid": "Starlink-Home-5G", "signal": 88, "bssid": "70:18:8B:A1:B2:C3"},
            {"ssid": "Irancell-WiFi-Office", "signal": 52, "bssid": "A4:C3:F0:11:22:33"},
            {"ssid": "Unknown_Net_Guest", "signal": 28, "bssid": "00:11:22:33:44:55"}
        ]
    return networks

def is_starlink_mac(bssid):
    if not bssid or bssid == "N/A":
        return False
    clean_bssid = bssid.upper().replace("-", ":")
    for prefix in app_state["mac_prefixes"]:
        if clean_bssid.startswith(prefix.upper()):
            return True
    return False

def main(page: ft.Page):
    page.title = "سامانه هوشمند پایش و رادار استارلینک (مقاوم در برابر اینترنت ملی)"
    page.theme_mode = ft.ThemeMode.DARK
    page.rtl = True
    page.padding = 15

    # صداهای هشدار لوکال
    audio_alert = ft.Audio(
        src="https://www.soundjay.com/buttons/sounds/button-3.mp3",
        autoplay=False
    )
    page.overlay.append(audio_alert)

    # ----- صفحه ورود (Login) -----
    user_pass_input = ft.TextField(label="رمز ورود کاربران", password=True, can_reveal_password=True, width=280)
    admin_pass_input = ft.TextField(label="رمز ورود ادمین", password=True, can_reveal_password=True, width=280)
    login_err = ft.Text("", color=ft.colors.RED_400, size=13)

    def check_user_login(e):
        if user_pass_input.value.strip() == app_state["user_password"]:
            show_user_panel()
        else:
            login_err.value = "رمز ورود کاربران اشتباه است!"
            page.update()

    def check_admin_login(e):
        if admin_pass_input.value.strip() == app_state["admin_password"]:
            show_admin_panel()
        else:
            login_err.value = "رمز ورود ادمین اشتباه است!"
            page.update()

    user_box = ft.Container(
        content=ft.Column([
            ft.Text("🔑 ورود کاربران", size=18, weight=ft.FontWeight.BOLD, color=ft.colors.BLUE_200),
            user_pass_input,
            ft.ElevatedButton("ورود کاربر", on_click=check_user_login, icon=ft.icons.LOGIN, bgcolor=ft.colors.BLUE_600, color=ft.colors.WHITE)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
        padding=15, border=ft.border.all(1, ft.colors.BLUE_400), border_radius=10
    )

    admin_box = ft.Container(
        content=ft.Column([
            ft.Text("🔐 ورود ادمین", size=18, weight=ft.FontWeight.BOLD, color=ft.colors.RED_200),
            admin_pass_input,
            ft.ElevatedButton("ورود ادمین", on_click=check_admin_login, icon=ft.icons.ADMIN_PANEL_SETTINGS, bgcolor=ft.colors.RED_700, color=ft.colors.WHITE)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
        padding=15, border=ft.border.all(1, ft.colors.RED_400), border_radius=10
    )

    login_view = ft.Column(
        [
            ft.Icon(ft.icons.RADAR, size=50, color=ft.colors.CYAN_400),
            ft.Text("⚡ سامانه هوشمند پایش و رادار استارلینک", size=18, weight=ft.FontWeight.BOLD, color=ft.colors.CYAN_200),
            ft.Text("🌐 فعال و قابل استفاده حتی در شرایط اینترنت ملی و قطعی شبکه", size=11, color=ft.colors.GREEN_300),
            ft.Divider(),
            ft.ResponsiveRow([
                ft.Column([user_box], col={"sm": 12, "md": 6}),
                ft.Column([admin_box], col={"sm": 12, "md": 6}),
            ], spacing=20),
            login_err
        ],
        alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20
    )

    # ----- سیستم بروزرسانی آنلاین و آفلاین -----
    update_status_text = ft.Text(f"نسخه: {CURRENT_VERSION} (حالت آفلاین و آنلاین فعال)", size=12, color=ft.colors.GREY_400)

    def check_for_updates(e):
        update_status_text.value = "در حال بررسی ارتباط... ⏳"
        page.update()
        try:
            req = urllib.request.Request(UPDATE_URL, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=3) as response:
                data = json.loads(response.read().decode())
                new_macs = data.get("starlink_macs", [])
                added_count = 0
                for mac in new_macs:
                    if mac not in app_state["mac_prefixes"]:
                        app_state["mac_prefixes"].append(mac)
                        added_count += 1
                update_status_text.value = f"✅ آنلاین: {added_count} مک جدید دریافت شد."
                update_status_text.color = ft.colors.GREEN_400
        except Exception:
            update_status_text.value = "📡 شبکه بین‌الملل در دسترس نیست (برنامه در حالت آفلاین کامل کار می‌کند)."
            update_status_text.color = ft.colors.AMBER_400
        page.update()

    update_box = ft.Container(
        content=ft.Row([
            ft.Column([
                ft.Text("🔄 وضعیت شبکه و بروزرسانی", size=13, weight=ft.FontWeight.BOLD),
                update_status_text
            ], expand=True),
            ft.ElevatedButton("🔍 بررسی آپدیت", on_click=check_for_updates, icon=ft.icons.SYSTEM_UPDATE)
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        padding=10, bgcolor=ft.colors.WHITE10, border_radius=8, margin=ft.margin.only(bottom=10)
    )

    # ----- صفحه اصلی اسکن و رادار -----
    wifi_list_view = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
    history_list_view = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO)
    alert_banner = ft.Container(visible=False, bgcolor=ft.colors.RED_900, padding=12, border_radius=8)

    def toggle_filter(e):
        app_state["filter_starlink_only"] = e.control.value
        scan_wifi()

    def export_history(e):
        try:
            file_path = "starlink_scan_report.txt"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("--- گزارش سامانه پایش و رادار استارلینک ---\n")
                for item in app_state["history"]:
                    f.write(item + "\n")
            page.snack_bar = ft.SnackBar(ft.Text(f"✅ گزارش در فایل {file_path} ذخیره شد."))
            page.snack_bar.open = True
        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"❌ خطا در ذخیره فایل: {str(ex)}"))
            page.snack_bar.open = True
        page.update()

    def scan_wifi(e=None):
        wifi_list_view.controls.clear()
        networks = get_wifi_networks()
        starlink_found = False

        for net in networks:
            ssid = net["ssid"]
            signal = net["signal"]
            bssid = net["bssid"]
            dist_text = estimate_distance(signal)
            
            is_starlink = is_starlink_mac(bssid) or "starlink" in ssid.lower()

            if app_state["filter_starlink_only"] and not is_starlink:
                continue

            if signal >= 70:
                sig_color = ft.colors.GREEN_400
                sig_text = f"عالی ({signal}%)"
            elif signal >= 40:
                sig_color = ft.colors.AMBER_400
                sig_text = f"متوسط ({signal}%)"
            else:
                sig_color = ft.colors.RED_400
                sig_text = f"ضعیف ({signal}%)"

            if is_starlink:
                starlink_found = True
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log_entry = f"🚀 [{now_str}] SSID: {ssid} | MAC: {bssid} | Signal: {signal}%"
                if log_entry not in app_state["history"]:
                    app_state["history"].insert(0, log_entry)

            status_tag = ft.Container(
                content=ft.Text("استارلینک 🚀" if is_starlink else "وای‌فای معمولی", size=11, color=ft.colors.BLACK, weight=ft.FontWeight.BOLD),
                bgcolor=ft.colors.CYAN_300 if is_starlink else ft.colors.GREY_700, padding=ft.padding.all(4), border_radius=5
            )

            card = ft.Card(
                content=ft.Container(
                    padding=12,
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.icons.WIFI, color=sig_color),
                            ft.Text(ssid, size=15, weight=ft.FontWeight.BOLD),
                            status_tag
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.ProgressBar(value=signal/100, color=sig_color, bgcolor=ft.colors.GREY_800),
                        ft.Row([
                            ft.Text(f"سیگنال: {sig_text}", color=sig_color, size=12),
                            ft.Text(f"📏 فاصله: {dist_text}", color=ft.colors.BLUE_200, size=12)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Text(f"آدرس مک: {bssid}", color=ft.colors.GREY_500, size=10)
                    ])
                )
            )
            wifi_list_view.controls.append(card)

        if starlink_found:
            alert_banner.content = ft.Row([
                ft.Icon(ft.icons.NOTIFICATION_IMPORTANT, color=ft.colors.WHITE),
                ft.Text("🚨 هشدار رادار: تجهیزات استارلینک در نزدیک شماست!", color=ft.colors.WHITE, weight=ft.FontWeight.BOLD)
            ])
            alert_banner.visible = True
            try:
                audio_alert.play()
            except Exception:
                pass
        else:
            alert_banner.visible = False

        update_history_ui()
        page.update()

    def update_history_ui():
        history_list_view.controls.clear()
        for item in app_state["history"][:5]:
            history_list_view.controls.append(ft.Text(item, size=11, color=ft.colors.GREY_300))

    def logout(e):
        page.controls.clear()
        user_pass_input.value = ""
        admin_pass_input.value = ""
        login_err.value = ""
        page.add(login_view)
        page.update()

    user_tab = ft.Column([
        update_box,
        alert_banner,
        ft.Row([
            ft.Switch(label="فقط استارلینک", value=False, on_change=toggle_filter),
            ft.ElevatedButton("🔄 اسکن مجدد", on_click=scan_wifi, icon=ft.icons.REFRESH)
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        wifi_list_view,
        ft.Divider(),
        ft.Row([
            ft.Text("📋 تاریخچه کشف‌های اخیر:", size=13, weight=ft.FontWeight.BOLD, color=ft.colors.AMBER_200),
            ft.IconButton(ft.icons.DOWNLOAD, on_click=export_history, tooltip="ذخیره خروجی گزارش")
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        history_list_view
    ], scroll=ft.ScrollMode.AUTO)

    # ----- صفحه پنل مدیریت ادمین -----
    new_user_pwd = ft.TextField(label="رمز جدید کاربران", width=200)
    new_admin_pwd = ft.TextField(label="رمز جدید ادمین", width=200)
    new_mac_prefix = ft.TextField(label="پیش‌شماره مک جدید (آفلاین)", width=220)
    admin_msg = ft.Text("", color=ft.colors.GREEN_400)

    def save_passwords(e):
        if new_user_pwd.value.strip():
            app_state["user_password"] = new_user_pwd.value.strip()
        if new_admin_pwd.value.strip():
            app_state["admin_password"] = new_admin_pwd.value.strip()
        admin_msg.value = "✅ تغییرات رمز عبور اعمال شد."
        page.update()

    def add_mac_prefix(e):
        prefix = new_mac_prefix.value.strip().upper()
        if prefix and prefix not in app_state["mac_prefixes"]:
            app_state["mac_prefixes"].append(prefix)
            admin_msg.value = f"✅ مک {prefix} به‌صورت آفلاین افزوده شد."
            new_mac_prefix.value = ""
            page.update()

    admin_view = ft.Column([
        ft.Row([
            ft.Text("🔐 پنل مدیریت و تنظیمات", size=18, weight=ft.FontWeight.BOLD, color=ft.colors.RED_400),
            ft.IconButton(ft.icons.LOGOUT, on_click=logout, tooltip="خروج")
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Divider(),
        ft.Text("🔑 تغییر رمزها:", size=14, weight=ft.FontWeight.BOLD),
        ft.Row([new_user_pwd, new_admin_pwd]),
        ft.ElevatedButton("ذخیره رمزها", on_click=save_passwords, icon=ft.icons.SAVE),
        ft.Divider(),
        ft.Text("📡 افزودن دستی مک استارلینک (مخصوص شرایط اینترنت ملی):", size=14, weight=ft.FontWeight.BOLD),
        ft.Row([new_mac_prefix, ft.ElevatedButton("افزودن", on_click=add_mac_prefix, icon=ft.icons.ADD)]),
        admin_msg,
        ft.Divider(),
        ft.ElevatedButton("ورود به رادار اسکن", on_click=lambda e: show_user_panel(), icon=ft.icons.RADAR)
    ], scroll=ft.ScrollMode.AUTO)

    def show_user_panel():
        page.controls.clear()
        page.add(ft.Column([
            ft.Row([
                ft.Text("سامانه رادار استارلینک", size=18, weight=ft.FontWeight.BOLD, color=ft.colors.BLUE_200),
                ft.IconButton(ft.icons.LOGOUT, on_click=logout)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            user_tab
        ]))
        scan_wifi()
        page.update()

    def show_admin_panel():
        page.controls.clear()
        page.add(admin_view)
        page.update()

    page.add(login_view)

ft.app(target=main)
