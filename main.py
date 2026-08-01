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
CURRENT_VERSION = "3.5.0-PRO"
SPLASH_IMAGE_URL = "https://v3.fasturl.cloud/file/fasturl/2026/08/02/images.jpeg_627fbbf54522930ed6b1fc910e5362bf.jpeg"

INITIAL_STARLINK_PREFIXES = [
    "70:18:8B", "28:EE:52", "00:7E:56", "38:8C:50", "34:8F:27", "80:8D:B9", "F8:2F:A8", "70:2A:D5"
]

DEFAULT_USER_HASH = hashlib.sha256("0011300".encode()).hexdigest()
DEFAULT_ADMIN_HASH = hashlib.sha256("f09931807880F".encode()).hexdigest()

# دیتابیس مرکز کنترل و داده‌ها
app_state = {
    "is_app_active": True,       # کلید خاموش/روشن کردن کل برنامه توسط ادمین
    "user_counter": 1,           # شمارنده ساخت شناسه کاربران (کاربر ۱، کاربر ۲، ...)
    "user_id_map": {},          # نگاشت نام کاربری به شماره اختصاصی
    "admin_hash": DEFAULT_ADMIN_HASH,
    "user_hash": DEFAULT_USER_HASH,
    "mac_prefixes": list(INITIAL_STARLINK_PREFIXES),
    "user_data": {},            # داده‌های کاربر: یادداشت‌ها، پیشنهادها و...
    "access_logs": []           # گزارش‌های ورود و خروج کاربران برای ادمین
}

def hash_pass(password: str) -> str:
    return hashlib.sha256(password.strip().encode()).hexdigest()

def sanitize_input(text: str) -> str:
    return re.sub(r'[\';\"\\<>]', '', text)

def get_tehran_shamsi_datetime():
    now_shamsi = jdatetime.datetime.now()
    date_str = now_shamsi.strftime("%Y/%m/%d")
    time_str = now_shamsi.strftime("%H:%M:%S")
    return date_str, time_str

def main(page: ft.Page):
    page.title = "سامانه هوشمند رادار و پایش استارلینک"
    page.theme_mode = ft.ThemeMode.DARK
    page.rtl = True
    page.padding = 10

    active_user = None
    is_admin = False

    # ----- 1. صفحه ورودی (Splash Screen / Login) -----
    username_field = ft.TextField(label="نام کاربری", width=280, text_align=ft.TextAlign.CENTER)
    pass_field = ft.TextField(label="رمز عبور", password=True, can_reveal_password=True, width=280)
    login_err = ft.Text("", color=ft.colors.RED_400, size=12, weight=ft.FontWeight.BOLD)

    def start_app(e):
        nonlocal active_user, is_admin
        uname = sanitize_input(username_field.value)
        pwd = sanitize_input(pass_field.value)

        if not uname or not pwd:
            login_err.value = "لطفاً نام کاربری و رمز را وارد کنید!"
            page.update()
            return

        user_h = hash_pass(pwd)

        # بررسی ورود ادمین
        if user_h == app_state["admin_hash"]:
            is_admin = True
            active_user = "ادمین سیستم"
            show_admin_dashboard()
            return

        # بررسی ورود کاربر عادی
        if user_h == app_state["user_hash"]:
            # اگر برنامه توسط ادمین خاموش شده باشد
            if not app_state["is_app_active"]:
                login_err.value = "⛔ برنامه توسط مدیریت غیرفعال شده است."
                page.update()
                return

            is_admin = False
            active_user = uname

            # اختصاص شناسه عددی ثابت (کاربر ۱، کاربر ۲، ...) در صورت اولین ورود
            if active_user not in app_state["user_id_map"]:
                user_code = f"کاربر {app_state['user_counter']}"
                app_state["user_id_map"][active_user] = user_code
                app_state["user_counter"] += 1
                app_state["user_data"][active_user] = {
                    "notes": [],
                    "2fa_enabled": False,
                    "suggestions": []
                }

            # ثبت گزارش ورود برای ادمین
            d_sh, t_teh = get_tehran_shamsi_datetime()
            user_code = app_state["user_id_map"][active_user]
            app_state["access_logs"].append({
                "user_code": user_code,
                "action": "ورود",
                "time": f"{d_sh} ساعت {t_teh}"
            })

            show_user_dashboard()
        else:
            login_err.value = "رمز عبور نادرست است!"
            page.update()

    splash_view = ft.Container(
        content=ft.Column([
            ft.Image(src=SPLASH_IMAGE_URL, width=240, height=300, fit=ft.ImageFit.CONTAIN, border_radius=15),
            ft.Text("به سامانه هوشمند پایش و رادار خوش آمدید", size=15, weight=ft.FontWeight.BOLD, color=ft.colors.WHITE),
            username_field,
            pass_field,
            ft.ElevatedButton("ورود به برنامه 🚀", on_click=start_app, bgcolor=ft.colors.GREEN_700, color=ft.colors.WHITE, width=280),
            login_err
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
        alignment=ft.alignment.center,
        expand=True
    )

    def logout_user(e):
        nonlocal active_user, is_admin
        if active_user and not is_admin and active_user in app_state["user_id_map"]:
            d_sh, t_teh = get_tehran_shamsi_datetime()
            user_code = app_state["user_id_map"][active_user]
            app_state["access_logs"].append({
                "user_code": user_code,
                "action": "خروج",
                "time": f"{d_sh} ساعت {t_teh}"
            })
        active_user = None
        is_admin = False
        main(page)

    # ----- 2. پنل مدیریت (ادمین) -----
    def show_admin_dashboard():
        page.controls.clear()
        
        status_text = ft.Text(
            f"وضعیت برنامه: {'🟢 روشن (فعال)' if app_state['is_app_active'] else '🔴 خاموش (غیرفعال)'}",
            size=15, weight=ft.FontWeight.BOLD
        )

        def toggle_app_status(e):
            app_state["is_app_active"] = e.control.value
            status_text.value = f"وضعیت برنامه: {'🟢 روشن (فعال)' if app_state['is_app_active'] else '🔴 خاموش (غیرفعال)'}"
            page.update()

        # نمایش گزارش ورود و خروج کاربران با شناسه عددی
        logs_list = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO, height=250)
        for log in reversed(app_state["access_logs"]):
            color = ft.colors.GREEN_400 if log["action"] == "ورود" else ft.colors.AMBER_400
            logs_list.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text(f"👤 {log['user_code']}", weight=ft.FontWeight.BOLD, color=ft.colors.CYAN_200),
                        ft.Text(f"عملکرد: {log['action']}", color=color),
                        ft.Text(f"⏰ {log['time']}", size=11, color=ft.colors.GREY_400)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=8, bgcolor=ft.colors.WHITE10, border_radius=6
                )
            )

        admin_panel = ft.Column([
            ft.Row([
                ft.Text("👑 پنل اختصاصی مدیریت (ادمین)", size=16, weight=ft.FontWeight.BOLD, color=ft.colors.AMBER_400),
                ft.IconButton(ft.icons.LOGOUT, on_click=logout_user, tooltip="خروج ادمین")
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(),
            status_text,
            ft.Switch(label="خاموش / روشن کردن سراسری برنامه برای کاربران", value=app_state["is_app_active"], on_change=toggle_app_status),
            ft.Divider(),
            ft.Text("📊 گزارش ورود و خروج کاربران (فقط ادمین):", size=14, weight=ft.FontWeight.BOLD),
            logs_list
        ], scroll=ft.ScrollMode.AUTO)

        page.add(admin_panel)

    # ----- 3. داشبورد اختصاصی کاربران عادی -----
    def show_user_dashboard():
        page.controls.clear()
        
        date_shamsi, time_tehran = get_tehran_shamsi_datetime()
        clock_text = ft.Text(f"📅 {date_shamsi} | ⏰ {time_tehran} (تهران)", size=12, color=ft.colors.CYAN_200, weight=ft.FontWeight.BOLD)

        def toggle_theme(e):
            page.theme_mode = ft.ThemeMode.LIGHT if page.theme_mode == ft.ThemeMode.DARK else ft.ThemeMode.DARK
            page.update()

        def toggle_2fa(e):
            udata = app_state["user_data"][active_user]
            udata["2fa_enabled"] = e.control.value
            page.snack_bar = ft.SnackBar(ft.Text(f"تایید دو مرحله‌ای {'فعال' if e.control.value else 'غیرفعال'} شد."))
            page.snack_bar.open = True
            page.update()

        note_input = ft.TextField(label="متن یادداشت یا نقطه مشکوک", expand=True)
        is_suspicious_check = ft.Checkbox(label="⚠️ نقطه مشکوک", value=False)
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

        sug_input = ft.TextField(label="ارسال پیشنهاد به ادمین...", multiline=True, rows=2)
        def send_suggestion(e):
            if sug_input.value.strip():
                app_state["user_data"][active_user]["suggestions"].append(sanitize_input(sug_input.value))
                sug_input.value = ""
                page.snack_bar = ft.SnackBar(ft.Text("✅ پیشنهاد ارسال شد."))
                page.snack_bar.open = True
                page.update()

        user_panel = ft.Column([
            ft.Row([
                ft.Text("📱 محیط کاربری سامانه رادار", size=15, weight=ft.FontWeight.BOLD, color=ft.colors.GREEN_400),
                ft.Row([
                    ft.IconButton(ft.icons.BRIGHTNESS_4, on_click=toggle_theme, tooltip="تم تاریک/روشن"),
                    ft.IconButton(ft.icons.LOGOUT, on_click=logout_user, tooltip="خروج")
                ])
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            clock_text,
            ft.Divider(),
            ft.Switch(label="🔐 تایید دو مرحله‌ای (2FA)", value=app_state["user_data"][active_user]["2fa_enabled"], on_change=toggle_2fa),
            ft.Divider(),
            ft.Text("📌 ثبت یادداشت و نقاط مشکوک روی نقشه:", size=13, weight=ft.FontWeight.BOLD),
            ft.Row([note_input, is_suspicious_check]),
            ft.ElevatedButton("ثبت یادداشت", on_click=add_note, icon=ft.icons.ADD_LOCATION),
            notes_list_view,
            ft.Divider(),
            ft.Text("📩 ارسال پیام / پیشنهاد به مدیریت:", size=13, weight=ft.FontWeight.BOLD),
            sug_input,
            ft.ElevatedButton("ارسال پیام", on_click=send_suggestion, icon=ft.icons.SEND)
        ], scroll=ft.ScrollMode.AUTO)

        page.add(user_panel)
        render_notes()

    page.add(splash_view)

ft.app(target=main)
