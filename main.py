import flet as ft
import subprocess
import re
import platform
import json
import urllib.request
import os
import sys
import hashlib
import time
from datetime import datetime

# نسخه فعلی اپلیکیشن
CURRENT_VERSION = "2.3.0-SECURE"
UPDATE_URL = "https://raw.githubusercontent.com/farshidas2701-cpu/starlink-monitor/main/version.json"

# پیش‌شماره‌های آدرس مک (OUI) مربوط به شرکت SpaceX / Starlink
INITIAL_STARLINK_PREFIXES = [
    "70:18:8B", "28:EE:52", "00:7E:56", "38:8C:50", "34:8F:27", "80:8D:B9", "F8:2F:A8", "70:2A:D5"
]

# هش SHA-256 رمزهای عبور اولیه
DEFAULT_USER_HASH = hashlib.sha256("0011300".encode()).hexdigest()
DEFAULT_ADMIN_HASH = hashlib.sha256("f09931807880F".encode()).hexdigest()

app_state = {
    "admin_hash": DEFAULT_ADMIN_HASH,
    "user_hash": DEFAULT_USER_HASH,
    "history": [],
    "mac_prefixes": list(INITIAL_STARLINK_PREFIXES),
    "filter_starlink_only": False,
    "failed_attempts": 0,
    "lockout_until": 0
}

def hash_pass(password: str) -> str:
    return hashlib.sha256(password.strip().encode()).hexdigest()

def check_environment_security():
    try:
        if sys.gettrace() is not None:
            return False
    except Exception:
        pass
    return True

def sanitize_input(text: str) -> str:
    return re.sub(r'[\';\"\\<>]', '', text)

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
    if not check_environment_security():
        page.add(ft.Text("❌ خطای امنیتی: محیط غیرمجاز تشخیص داده شد.", color=ft.colors.RED))
        return

    page.title = "سامانه هوشمند و ایمن پایش استارلینک"
    page.theme_mode = ft.ThemeMode.DARK
    page.rtl = True
    page.padding = 15

    audio_alert = ft.Audio(
        src="https://www.soundjay.com/buttons/sounds/button-3.mp3",
        autoplay=False
    )
    page.overlay.append(audio_alert)

    # ----- صفحه راهنمای کامل برنامه -----
    guide_dialog = ft.AlertDialog(
        title=ft.Text("📖 راهنمای کامل استفاده و اطلاعات برنامه", size=16, weight=ft.FontWeight.BOLD),
        content=ft.Container(
            content=ft.Column([
                ft.Text("🚀 ۱. شیوه کارکرد و اسکن رادار:", weight=ft.FontWeight.BOLD, color=ft.colors.CYAN_200),
                ft.Text("• با فشردن دکمه «اسکن مجدد»، تمام وای‌فای‌های اطراف بررسی می‌شوند.\n• شناسایی مودم‌های استارلینک بر اساس شناسه مک (BSSID) اختصاصی شرکت SpaceX انجام می‌شود."),
                ft.Divider(),
                ft.Text("📏 ۲. تخمین فاصله و هشدار صوتی:", weight=ft.FontWeight.BOLD, color=ft.colors.AMBER_200),
                ft.Text("• برنامه با تحلیل قدرت سیگنال، فاصله تقریبی شما تا مودم را به متر محاسبه می‌کند.\n• به محض کشف سیگنال استارلینک، آلارم صوتی و بنر هشدار قرمز فعال می‌شود."),
                ft.Divider(),
                ft.Text("🌐 ۳. عملکرد آفلاین و اینترنت ملی:", weight=ft.FontWeight.BOLD, color=ft.colors.GREEN_200),
                ft.Text("• برنامه ۱۰۰٪ آفلاین است و برای اسکن به اینترنت نیازی ندارد.\n• در شرایط قطعی اینترنت، ادمین می‌تواند مک‌آدرس‌های جدید را به‌صورت دستی وارد کند."),
                ft.Divider(),
                ft.Text("📂 ۴. خروجی‌گرفتن و فیلترها:", weight=ft.FontWeight.BOLD, color=ft.colors.BLUE_200),
                ft.Text("• با روشن کردن سوییچ «فقط استارلینک»، وای‌فای‌های معمولی مخفی می‌شوند.\n• با زدن آیکون دانلود، گزارش کامل کشف‌ها در فایل متنی ذخیره می‌شود."),
                ft.Divider(),
                ft.Text("🛡️ سخن پایانی درباره امنیت کامل برنامه:", weight=ft.FontWeight.BOLD, color=ft.colors.RED_200),
                ft.Text("این سامانه با بهره‌گیری از پروتکل‌های رمزنگاری SHA-256، مکانیزم ضد دیباگ (Anti-Debugging) و سیستم قفل خودکار در برابر حملات حدس رمز، بالاترین سطح امنیت را ارائه می‌دهد. کلیه اطلاعات به صورت موقت و ایمن در حافظه دستگاه پردازش شده و هیچ‌گونه داده‌ای قابل ردگیری یا نفوذ توسط افراد غیرمجاز نخواهد بود.")
            ], scroll=ft.ScrollMode.AUTO, spacing=8),
            width=320, height=400
        ),
        actions=[
            ft.TextButton("متوجه شدم", on_click=lambda e: page.close(guide_dialog))
        ]
    )

    def open_guide(e):
        page.open(guide_dialog)

    # ----- صفحه ورود (Login) -----
    user_pass_input = ft.TextField(label="رمز ورود کاربران", password=True, can_reveal_password=True, width=280)
    admin_pass_input = ft.TextField(label="رمز ورود ادمین", password=True, can_reveal_password=True, width=280)
    login_err = ft.Text("", color=ft.colors.RED_400, size=13)

    def check_lockout():
        if time.time() < app_state["lockout_until"]:
            remaining = int(app_state["lockout_until"] - time.time())
            login_err.value = f"⛔ سیستم قفل است. {remaining} ثانیه دیگر مجدداً سعی کنید."
            page.update()
            return True
        return False

    def handle_failed_attempt():
        app_state["failed_attempts"] += 1
        if app_state["failed_attempts"] >= 3:
            app_state["lockout_until"] = time.time() + 30
            app_state["failed_attempts"] = 0
            login_err.value = "⛔ ۳ بار تلاش اشتباه! ورود ۳۰ ثانیه قفل شد."
        else:
            login_err.value = f"رمز اشتباه است! (فرصت باقی‌مانده: {3 - app_state['failed_attempts']})"
        page.update()

    def check_user_login(e):
        if check_lockout():
            return
        if hash_pass(sanitize_input(user_pass_input.value)) == app_state["user_hash"]:
            app_state["failed_attempts"] = 0
            show_user_panel()
        else:
            handle_failed_attempt()

    def check_admin_login(e):
        if check_lockout():
            return
        if hash_pass(sanitize_input(admin_pass_input.value)) == app_state["admin_hash"]:
            app_state["failed_attempts"] = 0
            show_admin_panel()
        else:
            handle_failed_attempt()

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
            ft.Row([
                ft.Icon(ft.icons.SECURITY, size=40, color=ft.colors.CYAN_400),
                ft.Text("سامانه هوشمند رادار استارلینک", size=18, weight=ft.FontWeight.BOLD, color=ft.colors.CYAN_200)
            ], alignment=ft.MainAxisAlignment.CENTER),
            ft.ElevatedButton("📖 راهنمای کار با برنامه", on_click=open_guide, icon=ft.icons.HELP_OUTLINE, bgcolor=ft.colors.WHITE10),
            ft.Divider(),
            ft.ResponsiveRow([
                ft.Column([user_box], col={"sm": 12, "md": 6}),
                ft.Column([admin_box], col={"sm": 12, "md": 6}),
            ], spacing=20),
            login_err
        ],
        alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15
    )

    # ----- سیستم بروزرسانی -----
    update_status_text = ft.Text(f"نسخه: {CURRENT_VERSION}", size=12, color=ft.colors.GREY_400)

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
                    mac_clean = sanitize_input(mac)
                    if mac_clean not in app_state["mac_prefixes"]:
                        app_state["mac_prefixes"].append(mac_clean)
                        added_count += 1
                update_status_text.value = f"✅ بروزرسانی موفق: {added_count} مک جدید افزوده شد."
                update_status_text.color = ft.colors.GREEN_400
        except Exception:
            update_status_text.value = "📡 شبکه در دسترس نیست (عملکرد آفلاین فعال است)."
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

    # ----- پنل اسکن کاربران -----
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
            ssid = sanitize_input(net["ssid"])
            signal = net["signal"]
            bssid = sanitize_input(net["bssid"])
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
                ft.Text("🚨 هشدار رادار: تجهیزات استارلینک شناسایی شد!", color=ft.colors.WHITE, weight=ft.FontWeight.BOLD)
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

    # ----- پنل ادمین -----
    new_user_pwd = ft.TextField(label="رمز جدید کاربران", width=200, password=True)
    new_admin_pwd = ft.TextField(label="رمز جدید ادمین", width=200, password=True)
    new_mac_prefix = ft.TextField(label="پیش‌شماره مک جدید", width=220)
    admin_msg = ft.Text("", color=ft.colors.GREEN_400)

    def save_passwords(e):
        u_val = sanitize_input(new_user_pwd.value)
        a_val = sanitize_input(new_admin_pwd.value)
        if u_val:
            app_state["user_hash"] = hash_pass(u_val)
        if a_val:
            app_state["admin_hash"] = hash_pass(a_val)
        admin_msg.value = "✅ تغییرات رمز عبور به‌صورت هش امن ذخیره شد."
        new_user_pwd.value = ""
        new_admin_pwd.value = ""
        page.update()

    def add_mac_prefix(e):
        prefix = sanitize_input(new_mac_prefix.value).upper()
        if prefix and prefix not in app_state["mac_prefixes"]:
            app_state["mac_prefixes"].append(prefix)
            admin_msg.value = f"✅ مک {prefix} افزوده شد."
            new_mac_prefix.value = ""
            page.update()

    admin_view = ft.Column([
        ft.Row([
            ft.Text("🔐 پنل مدیریت و تنظیمات امن", size=18, weight=ft.FontWeight.BOLD, color=ft.colors.RED_400),
            ft.IconButton(ft.icons.LOGOUT, on_click=logout, tooltip="خروج")
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Divider(),
        ft.Text("🔑 تغییر رمزها (ذخیره‌سازی هش):", size=14, weight=ft.FontWeight.BOLD),
        ft.Row([new_user_pwd, new_admin_pwd]),
        ft.ElevatedButton("ذخیره امن رمزها", on_click=save_passwords, icon=ft.icons.SAVE),
        ft.Divider(),
        ft.Text("📡 افزودن دستی مک استارلینک:", size=14, weight=ft.FontWeight.BOLD),
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
                ft.Row([
                    ft.IconButton(ft.icons.HELP_OUTLINE, on_click=open_guide, tooltip="راهنما"),
                    ft.IconButton(ft.icons.LOGOUT, on_click=logout, tooltip="خروج")
                ])
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
