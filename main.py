import flet as ft
import subprocess
import re
import platform
import json
import urllib.request
import sys
import hashlib
import time
from datetime import datetime
import jdatetime

# نسخه و تنظیمات پایه
CURRENT_VERSION = "3.0.0-PRO"
UPDATE_URL = "https://raw.githubusercontent.com/farshidas2701-cpu/starlink-monitor/main/version.json"
SPLASH_IMAGE_URL = "https://v3.fasturl.cloud/file/fasturl/2026/08/02/images.jpeg_627fbbf54522930ed6b1fc910e5362bf.jpeg"

INITIAL_STARLINK_PREFIXES = [
    "70:18:8B", "28:EE:52", "00:7E:56", "38:8C:50", "34:8F:27", "80:8D:B9", "F8:2F:A8", "70:2A:D5"
]

DEFAULT_USER_HASH = hashlib.sha256("0011300".encode()).hexdigest()
DEFAULT_ADMIN_HASH = hashlib.sha256("f09931807880F".encode()).hexdigest()

# دیتابیس هوشمند در حافظه (جداسازی بر اساس هر کاربر)
app_state = {
    "admin_hash": DEFAULT_ADMIN_HASH,
    "user_hash": DEFAULT_USER_HASH,
    "mac_prefixes": list(INITIAL_STARLINK_PREFIXES),
    "user_data": {},  # داده‌های اختصاصی هر کاربر: { username: { notes: [], 2fa: False, suggestions: [] } }
    "failed_attempts": 0,
    "lockout_until": 0
}

# متون ۳ زبانه برنامه
LANGUAGES = {
    "fa": {
        "title": "سامانه هوشمند پایش و رادار",
        "welcome": "به سامانه پایش و رادار خوش آمدید",
        "enter": "ورود به برنامه",
        "scan": "اسکن مجدد",
        "suspicious": "علامت‌گذاری نقطه مشکوک",
        "notes": "یادداشت‌های اختصاصی روی نقشه",
        "2fa": "تایید دو مرحله‌ای",
        "suggest": "ارسال پیشنهاد به ادمین",
        "lang": "زبان",
        "dark": "حالت تاریک"
    },
    "en": {
        "title": "Smart Radar System",
        "welcome": "Welcome to Radar System",
        "enter": "Enter App",
        "scan": "Rescan",
        "suspicious": "Mark Suspicious Point",
        "notes": "Map Notes",
        "2fa": "2-Factor Auth",
        "suggest": "Send Suggestion",
        "lang": "Language",
        "dark": "Dark Mode"
    },
    "ar": {
        "title": "نظام الرادار الذكي",
        "welcome": "مرحبا بكم في نظام الرادار",
        "enter": "الدخول إلى التطبيق",
        "scan": "إعادة المسح",
        "suspicious": "تحديد نقطة مشبوهة",
        "notes": "ملاحظات الخريطة",
        "2fa": "المصادقة الثنائية",
        "suggest": "إرسال اقتراح",
        "lang": "اللغة",
        "dark": "الوضع الداكن"
    }
}

def hash_pass(password: str) -> str:
    return hashlib.sha256(password.strip().encode()).hexdigest()

def sanitize_input(text: str) -> str:
    return re.sub(r'[\';\"\\<>]', '', text)

def get_tehran_shamsi_datetime():
    # تاریخ دقیق شمسی و ساعت تهران
    now_shamsi = jdatetime.datetime.now()
    date_str = now_shamsi.strftime("%Y/%m/%d")
    time_str = now_shamsi.strftime("%H:%M:%S")
    return date_str, time_str

def main(page: ft.Page):
    page.title = "سامانه هوشمند رادار استارلینک"
    page.theme_mode = ft.ThemeMode.DARK
    page.rtl = True
    page.padding = 10

    current_lang = "fa"
    active_user = None

    # ----- 1. صفحه ورودی (Welcome / Splash) -----
    username_field = ft.TextField(label="نام کاربری شما", width=280, text_align=ft.TextAlign.CENTER)
    pass_field = ft.TextField(label="رمز عبور", password=True, can_reveal_password=True, width=280)
    login_err = ft.Text("", color=ft.colors.RED_400, size=12)

    def start_app(e):
        nonlocal active_user
        uname = sanitize_input(username_field.value)
        pwd = sanitize_input(pass_field.value)

        if not uname or not pwd:
            login_err.value = "لطفاً نام کاربری و رمز را وارد کنید!"
            page.update()
            return

        if hash_pass(pwd) == app_state["user_hash"] or hash_pass(pwd) == app_state["admin_hash"]:
            active_user = uname
            if active_user not in app_state["user_data"]:
                # ایجاد فضای کاری و پنجره اختصاصی برای کاربر جدید
                app_state["user_data"][active_user] = {
                    "notes": [],
                    "2fa_enabled": False,
                    "suggestions": []
                }
            show_dashboard()
        else:
            login_err.value = "رمز عبور نادرست است!"
            page.update()

    splash_view = ft.Container(
        content=ft.Column([
            ft.Image(src=SPLASH_IMAGE_URL, width=250, height=320, fit=ft.ImageFit.CONTAIN, border_radius=15),
            ft.Text("به سامانه هوشمند پایش و رادار خوش آمدید", size=16, weight=ft.FontWeight.BOLD, color=ft.colors.WHITE),
            username_field,
            pass_field,
            ft.ElevatedButton("ورود به برنامه 🚀", on_click=start_app, bgcolor=ft.colors.GREEN_700, color=ft.colors.WHITE, width=280),
            login_err
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12),
        alignment=ft.alignment.center,
        expand=True
    )

    # ----- 2. داشبورد اختصاصی کاربر -----
    def show_dashboard():
        page.controls.clear()
        
        # هدر ساعت و تاریخ تهران
        date_shamsi, time_tehran = get_tehran_shamsi_datetime()
        clock_text = ft.Text(f"📅 {date_shamsi} | ⏰ {time_tehran} (تهران)", size=12, color=ft.colors.CYAN_200, weight=ft.FontWeight.BOLD)

        # تغییر تم (تاریک/روشن)
        def toggle_theme(e):
            page.theme_mode = ft.ThemeMode.LIGHT if page.theme_mode == ft.ThemeMode.DARK else ft.ThemeMode.DARK
            page.update()

        # فعال‌سازی 2FA اختیاری
        def toggle_2fa(e):
            udata = app_state["user_data"][active_user]
            udata["2fa_enabled"] = e.control.value
            page.snack_bar = ft.SnackBar(ft.Text(f"تایید دو مرحله‌ای {'فعال' if e.control.value else 'غیرفعال'} شد."))
            page.snack_bar.open = True
            page.update()

        # بخش ثبت یادداشت و نقاط مشکوک
        note_input = ft.TextField(label="متن یادداشت یا نقطه مشکوک", expand=True)
        is_suspicious_check = ft.Checkbox(label="⚠️ نقطه مشکوک است", value=False)
        notes_list_view = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO)

        def add_note(e):
            if note_input.value.strip():
                d_sh, t_teh = get_tehran_shamsi_datetime()
                note_item = {
                    "id": time.time(),
                    "text": sanitize_input(note_input.value),
                    "suspicious": is_suspicious_check.value,
                    "date": f"{d_sh} - {t_teh}"
                }
                app_state["user_data"][active_user]["notes"].append(note_item)
                note_input.value = ""
                is_suspicious_check.value = False
                render_notes()

        def delete_note(note_id):
            app_state["user_data"][active_user]["notes"] = [
                n for n in app_state["user_data"][active_user]["notes"] if n["id"] != note_id
            ]
            render_notes()

        def render_notes():
            notes_list_view.controls.clear()
            for n in app_state["user_data"][active_user]["notes"]:
                color = ft.colors.RED_400 if n["suspicious"] else ft.colors.BLUE_200
                prefix = "⚠️ [مشکوک] " if n["suspicious"] else "📌 "
                card = ft.Container(
                    content=ft.Row([
                        ft.Column([
                            ft.Text(f"{prefix}{n['text']}", size=13, weight=ft.FontWeight.BOLD, color=color),
                            ft.Text(n["date"], size=10, color=ft.colors.GREY_400)
                        ], expand=True),
                        ft.IconButton(ft.icons.DELETE, icon_color=ft.colors.RED_500, on_click=lambda e, nid=n["id"]: delete_note(nid))
                    ]),
                    padding=8, bgcolor=ft.colors.WHITE10, border_radius=8
                )
                notes_list_view.controls.append(card)
            page.update()

        # بخش ارسال پیشنهاد به ادمین
        sug_input = ft.TextField(label="ارسال پیشنهاد یا پیام به ادمین...", multiline=True, rows=2)
        def send_suggestion(e):
            if sug_input.value.strip():
                app_state["user_data"][active_user]["suggestions"].append(sanitize_input(sug_input.value))
                sug_input.value = ""
                page.snack_bar = ft.SnackBar(ft.Text("✅ پیشنهاد شما با موفقیت به ادمین ارسال شد."))
                page.snack_bar.open = True
                page.update()

        # چیدمان اصلی پنل اختصاصی
        user_panel = ft.Column([
            ft.Row([
                ft.Text(f"👤 پنل اختصاصی: {active_user}", size=16, weight=ft.FontWeight.BOLD, color=ft.colors.GREEN_400),
                ft.Row([
                    ft.IconButton(ft.icons.BRIGHTNESS_4, on_click=toggle_theme, tooltip="تغییر تم تاریک/روشن"),
                    ft.IconButton(ft.icons.LOGOUT, on_click=lambda e: main(page), tooltip="خروج")
                ])
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            clock_text,
            ft.Divider(),
            ft.Switch(label="🔐 فعال‌سازی تایید دو مرحله‌ای (2FA)", value=app_state["user_data"][active_user]["2fa_enabled"], on_change=toggle_2fa),
            ft.Divider(),
            ft.Text("📌 ثبت یادداشت و نقاط مشکوک (ذخیره دائمی):", size=14, weight=ft.FontWeight.BOLD),
            ft.Row([note_input, is_suspicious_check]),
            ft.ElevatedButton("ثبت یادداشت روی نقشه", on_click=add_note, icon=ft.icons.ADD_LOCATION),
            notes_list_view,
            ft.Divider(),
            ft.Text("📩 ارسال پیشنهاد به ادمین:", size=14, weight=ft.FontWeight.BOLD),
            sug_input,
            ft.ElevatedButton("ارسال پیام", on_click=send_suggestion, icon=ft.icons.SEND)
        ], scroll=ft.ScrollMode.AUTO)

        page.add(user_panel)
        render_notes()

    page.add(splash_view)

ft.app(target=main)
