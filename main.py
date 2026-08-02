import flet as ft
import re
import math
import time
import random
from datetime import datetime

CURRENT_VERSION = "1.0.0-FULL"

# تبدیل تاریخ میلادی به شمسی
def gregorian_to_jalali(gy, gm, gd):
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    if gy > 1600:
        jy = 979
        gy -= 1600
    else:
        jy = 0
        gy -= 621
    gy2 = gy + 1 if gm > 2 else gy
    days = (365 * gy) + (gy2 // 4) - (gy2 // 100) + (gy2 // 400) + g_d_m[gm - 1] + gd - 1
    jy += 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 186:
        jm = 1 + (days // 31)
        jd = 1 + (days % 31)
    else:
        jm = 7 + ((days - 186) // 30)
        jd = 1 + ((days - 186) % 30)
    return f"{jy}/{jm:02d}/{jd:02d}"

def get_now_shamsi():
    now = datetime.now()
    shamsi_date = gregorian_to_jalali(now.year, now.month, now.day)
    return f"{shamsi_date} - {now.strftime('%H:%M:%S')}"

user_store = {
    "notes": [],
    "user_logs": [],
    "user_counter": 1,
    "user_pin": "0011300",
    "admin_pin": "f09931807880F",
    "panic_pin": "9999",
    "sound_alert": True,
    "online_mode": True,
    "current_role": None,
    "current_user_name": "",
    "failed_attempts": 0,
    "lockout_until": 0
}

def sanitize_input(text: str) -> str:
    return re.sub(r'[\';\"\\<>]', '', text)

def calculate_fspl_distance(rssi_dbm: float, freq_mhz: float = 2400.0) -> float:
    try:
        exp = (27.55 - (20 * math.log10(freq_mhz)) + abs(rssi_dbm)) / 20.0
        return round(math.pow(10, exp), 1)
    except:
        return 0.0

def main(page: ft.Page):
    page.title = "سامانه جامع پایش، رادار و صفحات شخصی"
    page.theme_mode = ft.ThemeMode.DARK
    page.rtl = True
    page.padding = 12

    calc_expression = ""

    def show_toast(msg: str):
        page.snack_bar = ft.SnackBar(ft.Text(msg))
        page.snack_bar.open = True
        page.update()

    def show_splash():
        page.controls.clear()
        flag = ft.Container(
            content=ft.Column([
                ft.Container(height=45, bgcolor="#239f40", border_radius=ft.border_radius.only(top_left=10, top_right=10)),
                ft.Container(height=45, bgcolor="white", alignment=ft.Alignment(0, 0), content=ft.Text("🇮🇷", size=26)),
                ft.Container(height=45, bgcolor="#da0000", border_radius=ft.border_radius.only(bottom_left=10, bottom_right=10))
            ], spacing=0),
            width=240,
            border=ft.border.all(1, "white24"),
            border_radius=10,
            shadow=ft.BoxShadow(blur_radius=15, color="green900")
        )
        page.add(
            ft.Container(
                content=ft.Column([
                    ft.Text("به نام خدا", size=18, weight=ft.FontWeight.BOLD, color="white"),
                    flag,
                    ft.Text("سامانه جامع پایش و مدیریت امنیتی", size=14, weight=ft.FontWeight.BOLD, color="green400"),
                    ft.ElevatedButton("ورود به برنامه 🚀", on_click=lambda e: show_login(), bgcolor="green800", color="white")
                ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15),
                alignment=ft.Alignment(0, 0),
                expand=True
            )
        )
        page.update()

    def open_change_pin_dialog(e):
        is_admin = (user_store["current_role"] == "admin")
        user_pin_input = ft.TextField(label="رمز عبور جدید کاربران", password=True, can_reveal_password=True, value=user_store["user_pin"])
        admin_pin_input = ft.TextField(label="رمز عبور جدید ادمین", password=True, can_reveal_password=True, value=user_store["admin_pin"]) if is_admin else None

        def save_new_pins(e):
            if user_pin_input.value and user_pin_input.value.strip():
                user_store["user_pin"] = user_pin_input.value.strip()
                if is_admin and admin_pin_input and admin_pin_input.value.strip():
                    user_store["admin_pin"] = admin_pin_input.value.strip()
                page.close(change_pin_dialog)
                show_toast("🔑 رمزهای عبور با موفقیت به‌روزرسانی شدند.")
            else:
                show_toast("⚠️ لطفاً رمز معتبر وارد کنید.")

        dialog_controls = [ft.Text("رمزهای عبور جدید را تعیین کنید:", size=11, color="grey300"), user_pin_input]
        if is_admin and admin_pin_input:
            dialog_controls.append(admin_pin_input)

        change_pin_dialog = ft.AlertDialog(
            title=ft.Text("🔑 تغییر رمزهای عبور ورود", size=14, weight=ft.FontWeight.BOLD, color="amber400"),
            content=ft.Container(content=ft.Column(dialog_controls, spacing=10), width=280, height=180 if is_admin else 120, padding=5),
            actions=[
                ft.TextButton("انصراف", on_click=lambda e: page.close(change_pin_dialog)),
                ft.ElevatedButton("ذخیره رمزها", on_click=save_new_pins, bgcolor="green800", color="white")
            ]
        )
        page.open(change_pin_dialog)

    def open_admin_logs_dialog(e):
        log_items = []
        for log in reversed(user_store["user_logs"]):
            log_items.append(
                ft.Container(
                    content=ft.Column([
                        ft.Text(f"👤 {log['user']} ({log['role']})", size=12, weight=ft.FontWeight.BOLD, color="cyan300"),
                        ft.Text(f"📥 ورود: {log['login_time']}", size=10, color="green300"),
                        ft.Text(f"📤 خروج: {log.get('logout_time', 'در حال استفاده...')}", size=10, color="amber300" if 'logout_time' in log else "grey400"),
                    ], spacing=2),
                    padding=6, bgcolor="white10", border_radius=6
                )
            )
        logs_dialog = ft.AlertDialog(
            title=ft.Text("📋 گزارش جامع ورود و خروج کاربران", size=14, weight=ft.FontWeight.BOLD, color="amber400"),
            content=ft.Container(content=ft.Column(log_items, scroll=ft.ScrollMode.AUTO, spacing=8), width=300, height=350, padding=5),
            actions=[ft.TextButton("بستن", on_click=lambda e: page.close(logs_dialog))]
        )
        page.open(logs_dialog)

    def open_radar_map(e):
        is_admin = (user_store["current_role"] == "admin")
        mode_status = "🌐 حالت آنلاین" if user_store["online_mode"] else "🇮🇷 حالت نت ملی"
        center_lat, center_lng = 35.6892, 51.3890
        scale = 8000

        radar_elements = [
            ft.Container(width=240, height=240, border=ft.border.all(1, "green900"), border_radius=120, alignment=ft.Alignment(0, 0)),
            ft.Container(width=160, height=160, border=ft.border.all(1, "green800"), border_radius=80, alignment=ft.Alignment(0, 0)),
            ft.Container(width=80, height=80, border=ft.border.all(1, "green700"), border_radius=40, alignment=ft.Alignment(0, 0)),
            ft.Container(content=ft.Text("🎯", size=18), alignment=ft.Alignment(0, 0))
        ]

        visible_notes = user_store["notes"] if is_admin else [n for n in user_store["notes"] if n.get("by") == user_store["current_user_name"]]

        for n in visible_notes:
            color = "red400" if n["suspicious"] else "cyan400"
            dx = (n["lng"] - center_lng) * scale
            dy = (center_lat - n["lat"]) * scale
            dx = max(-120, min(120, dx))
            dy = max(-120, min(120, dy))
            radar_elements.append(
                ft.Container(
                    content=ft.Column([ft.Text("📍", size=14), ft.Text(n['text'][:8], size=8, color=color, weight=ft.FontWeight.BOLD)], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
                    alignment=ft.Alignment(dx / 140, dy / 140),
                    tooltip=f"{n['text']} ({n['gps']})"
                )
            )

        map_dialog = ft.AlertDialog(
            title=ft.Text("🗺️ رادار اختصاصی شما", size=14, weight=ft.FontWeight.BOLD, color="green400"),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(mode_status, size=11, color="green300", weight=ft.FontWeight.BOLD),
                    ft.Container(content=ft.Stack(controls=radar_elements, alignment=ft.Alignment(0, 0)), width=280, height=280, bgcolor="black", border_radius=14, border=ft.border.all(1.5, "green600")),
                    ft.Row([ft.Text("🟢 موقعیت شما", size=10, color="green400"), ft.Text("🔴 مشکوک", size=10, color="red400"), ft.Text("🔵 عادی", size=10, color="cyan400")], alignment=ft.MainAxisAlignment.SPACE_AROUND)
                ], spacing=10),
                width=300, height=370, padding=5
            ),
            actions=[ft.TextButton("بستن", on_click=lambda e: page.close(map_dialog))]
        )
        page.open(map_dialog)

    calc_display = ft.TextField(value="0", read_only=True, text_align=ft.TextAlign.RIGHT, text_size=20, color="green400", bgcolor="black46", border_radius=10)

    def on_calc_btn_click(e):
        nonlocal calc_expression
        val = e.control.text

        if time.time() < user_store["lockout_until"]:
            remaining = int(user_store["lockout_until"] - time.time())
            show_toast(f"🛑 ورود قفل است ({remaining} ثانیه باقی‌مانده)")
            return

        if val == "C":
            calc_expression = ""
            calc_display.value = "0"
        elif val == "=":
            if calc_expression == user_store["user_pin"]:
                calc_expression = ""
                user_store["failed_attempts"] = 0
                user_name = f"کاربر {user_store['user_counter']}"
                user_store["user_counter"] += 1
                user_store["current_role"] = "user"
                user_store["current_user_name"] = user_name
                user_store["user_logs"].append({"user": user_name, "role": "کاربر عادی", "login_time": get_now_shamsi()})
                show_dashboard()
                show_toast(f"👤 خوش آمدید به صفحه شخصی ({user_name})")
                return
            elif calc_expression == user_store["admin_pin"]:
                calc_expression = ""
                user_store["failed_attempts"] = 0
                user_store["current_role"] = "admin"
                user_store["current_user_name"] = "مدیر سیستم (ادمین)"
                user_store["user_logs"].append({"user": "مدیر سیستم", "role": "ادمین", "login_time": get_now_shamsi()})
                show_dashboard()
                show_toast("👑 ورود موفق در سطح ادمین")
                return
            elif calc_expression == user_store["panic_pin"]:
                calc_expression = ""
                user_store["notes"].clear()
                user_store["user_logs"].clear()
                show_login_view()
                show_toast("🚨 امحای اضطراری انجام شد.")
                return
            try:
                calc_display.value = str(eval(calc_expression))
                calc_expression = calc_display.value
            except:
                user_store["failed_attempts"] += 1
                if user_store["failed_attempts"] >= 3:
                    user_store["lockout_until"] = time.time() + 15
                    show_toast("🚨 سیستم به دلیل ۳ ورود اشتباه قفل شد.")
                calc_display.value = "Error"
                calc_expression = ""
        else:
            calc_expression += val
            calc_display.value = calc_expression
        page.update()

    def build_calc_button(text, color="white10"):
        return ft.ElevatedButton(text, on_click=on_calc_btn_click, bgcolor=color, expand=True, height=50)

    def logout_action(e=None):
        if user_store["user_logs"]:
            user_store["user_logs"][-1]["logout_time"] = get_now_shamsi()
        show_login_view()

    def show_login_view():
        user_store["current_role"] = None
        user_store["current_user_name"] = ""
        page.controls.clear()
        calc_view = ft.Column([
            ft.Row([ft.Text("🔢 ماشین حساب", size=16, weight=ft.FontWeight.BOLD)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            calc_display,
            ft.Column([
                ft.Row([build_calc_button("f", "blue900"), build_calc_button("F", "blue900"), build_calc_button("C", "red800"), build_calc_button("/", "orange800")]),
                ft.Row([build_calc_button("7"), build_calc_button("8"), build_calc_button("9"), build_calc_button("*", "orange800")]),
                ft.Row([build_calc_button("4"), build_calc_button("5"), build_calc_button("6"), build_calc_button("-", "orange800")]),
                ft.Row([build_calc_button("1"), build_calc_button("2"), build_calc_button("3"), build_calc_button("+", "orange800")]),
                ft.Row([build_calc_button("0"), build_calc_button("=", "green800")], spacing=8)
            ], spacing=6)
        ], spacing=12)
        page.add(calc_view)
        page.update()

    def show_dashboard():
        page.controls.clear()
        is_admin = (user_store["current_role"] == "admin")
        
        role_badge = ft.Text(f"👤 صفحه شخصی: {user_store['current_user_name']}", size=12, color="amber400" if is_admin else "cyan300", weight=ft.FontWeight.BOLD)
        network_status_text = ft.Text("🌐 اینترنت بین‌المللی متصل" if user_store["online_mode"] else "🇮🇷 نت ملی / آفلاین فعال", size=11, color="green400" if user_store["online_mode"] else "amber400", weight=ft.FontWeight.BOLD)

        def toggle_network_mode(e):
            if not is_admin:
                show_toast("⚠️ تغییر وضعیت شبکه فقط برای ادمین امکان‌پذیر است.")
                return
            user_store["online_mode"] = not user_store["online_mode"]
            show_toast("وضعیت شبکه به " + ("آنلاین" if user_store["online_mode"] else "نت ملی / آفلاین") + " تغییر یافت.")
            show_dashboard()

        rssi_val_text = ft.Text("-65 dBm", size=14, weight=ft.FontWeight.BOLD, color="green400")
        distance_text = ft.Text("تخمین فاصله: ~8.5 متر", size=12, color="amber200")
        rssi_progress = ft.ProgressBar(value=0.65, color="green400", bgcolor="white10")

        def simulate_signal_scan(e):
            val = random.randint(35, 90)
            dist = calculate_fspl_distance(-val)
            rssi_val_text.value = f"-{val} dBm ({'عالی/نزدیک' if val < 50 else 'متوسط' if val < 75 else 'ضعیف'})"
            distance_text.value = f"تخمین فاصله (FSPL): ~{dist} متر"
            rssi_progress.value = (100 - val) / 100
            rssi_progress.color = "red400" if val < 50 else "green400" if val < 75 else "amber400"
            if val < 50 and user_store["sound_alert"]:
                show_toast("🔊 [هشدار صوتی گایگر] سیگنال بسیار نزدیک است!")
            page.update()

        note_input = ft.TextField(label="متن یادداشت یا نقطه مشکوک شخصی", expand=True)
        is_suspicious_check = ft.Checkbox(label="⚠️ نقطه مشکوک", value=False)
        gps_check = ft.Checkbox(label="📍 ثبت موقعیت (GPS)", value=True)
        notes_list_view = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO)

        def add_note(e):
            if note_input.value.strip():
                lat, lng = 35.6892 + random.uniform(-0.01, 0.01), 51.3890 + random.uniform(-0.01, 0.01)
                gps_loc = f"{lat:.4f}, {lng:.4f}" if gps_check.value else "بدون GPS"
                note_item = {
                    "id": time.time(),
                    "text": sanitize_input(note_input.value),
                    "suspicious": is_suspicious_check.value,
                    "gps": gps_loc,
                    "lat": lat if gps_check.value else 35.6892,
                    "lng": lng if gps_check.value else 51.3890,
                    "mode": "آنلاین" if user_store["online_mode"] else "نت ملی",
                    "by": user_store["current_user_name"]
                }
                user_store["notes"].append(note_item)
                note_input.value = ""
                is_suspicious_check.value = False
                render_notes()

        def delete_note(note_id):
            user_store["notes"] = [n for n in user_store["notes"] if n["id"] != note_id]
            render_notes()

        def render_notes():
            notes_list_view.controls.clear()
            user_notes = user_store["notes"] if is_admin else [n for n in user_store["notes"] if n.get("by") == user_store["current_user_name"]]
            for n in user_notes:
                color = "red400" if n["suspicious"] else "cyan200"
                prefix = "⚠️ [مشکوک] " if n["suspicious"] else "📌 "
                actions = [ft.ElevatedButton("حذف ❌", on_click=lambda e, nid=n["id"]: delete_note(nid), bgcolor="red900", color="white", height=30)]
                card = ft.Container(
                    content=ft.Row([
                        ft.Column([ft.Text(f"{prefix}{n['text']}", size=13, weight=ft.FontWeight.BOLD, color=color), ft.Text(f"ثبت توسط: {n.get('by', 'شما')} | 🌐 {n['mode']} | 📍 {n['gps']}", size=10, color="grey400")], expand=True),
                        *actions
                    ]),
                    padding=8, bgcolor="white10", border_radius=8
                )
                notes_list_view.controls.append(card)
            page.update()

        admin_logs_btn = ft.ElevatedButton("📋 گزارش ورود/خروج کاربران", on_click=open_admin_logs_dialog, bgcolor="amber900", color="white", height=32) if is_admin else ft.Container()

        dashboard_controls = [
            ft.Row([
                ft.Text("📱 سامانه پایش و رادار", size=15, weight=ft.FontWeight.BOLD, color="green400"),
                ft.Row([
                    ft.ElevatedButton("🚨 قفل سریع (ماشین حساب)", on_click=logout_action, bgcolor="red900", color="white", height=32),
                    ft.ElevatedButton("🔑 تغییر رمز", on_click=open_change_pin_dialog, bgcolor="blue800", color="white", height=32)
                ], spacing=5)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([role_badge, admin_logs_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([network_status_text, ft.ElevatedButton("تغییر شبکه 🔄", on_click=toggle_network_mode, height=30, disabled=not is_admin)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(),
            ft.Row([ft.Text("📈 اسکن شدت سیگنال و پایش شخصی:", size=13, weight=ft.FontWeight.BOLD)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(content=ft.Column([ft.Row([rssi_val_text, distance_text], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), rssi_progress, ft.ElevatedButton("بروزرسانی اسکن 🔄", on_click=simulate_signal_scan)]), padding=10, bgcolor="black26", border_radius=8),
            ft.Divider(),
            ft.Row([ft.Text("📍 یادداشت‌ها و نقاط شخصی شما:", size=13, weight=ft.FontWeight.BOLD)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([note_input]),
            ft.Row([is_suspicious_check, gps_check]),
            ft.ElevatedButton("ثبت نقطه شخصی 📍", on_click=add_note),
            ft.Row([ft.Text("📋 یادداشت‌های ذخیره‌شده شما:", size=13, weight=ft.FontWeight.BOLD), ft.ElevatedButton("رادار شخصی 🗺️", on_click=open_radar_map, bgcolor="green700", color="white")], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            notes_list_view
        ]

        page.add(ft.Column(dashboard_controls, scroll=ft.ScrollMode.AUTO))
        render_notes()

    show_splash()

ft.app(target=main)
