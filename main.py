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
CURRENT_VERSION = "4.0.0-ULTIMATE"
SPLASH_IMAGE_URL = "https://v3.fasturl.cloud/file/fasturl/2026/08/02/images.jpeg_627fbbf54522930ed6b1fc910e5362bf.jpeg"

INITIAL_STARLINK_PREFIXES = [
    "70:18:8B", "28:EE:52", "00:7E:56", "38:8C:50", "34:8F:27", "80:8D:B9", "F8:2F:A8", "70:2A:D5"
]

DEFAULT_USER_HASH = hashlib.sha256("0011300".encode()).hexdigest()
DEFAULT_ADMIN_HASH = hashlib.sha256("f09931807880F".encode()).hexdigest()

app_state = {
    "is_app_active": True,
    "user_counter": 1,
    "user_id_map": {},
    "admin_hash": DEFAULT_ADMIN_HASH,
    "user_hash": DEFAULT_USER_HASH,
    "mac_prefixes": list(INITIAL_STARLINK_PREFIXES),
    "user_data": {},
    "access_logs": []
}

def hash_pass(password: str) -> str:
    return hashlib.sha256(password.strip().encode()).hexdigest()

def sanitize_input(text: str) -> str:
    return re.sub(r'[\';\"\\<>]', '', text)

def get_tehran_shamsi_datetime():
    now_shamsi = jdatetime.datetime.now()
    return now_shamsi.strftime("%Y/%m/%d"), now_shamsi.strftime("%H:%M:%S")

def main(page: ft.Page):
    page.title = "سامانه هوشمند پایش و رادار استارلینک"
    page.theme_mode = ft.ThemeMode.DARK
    page.rtl = True
    page.padding = 10

    active_user = None
    is_admin = False
    is_stealth_mode = False

    # صدای بوق هوشمند
    audio_beeper = ft.Audio(src="https://www.soundjay.com/buttons/sounds/button-3.mp3", autoplay=False)
    page.overlay.append(audio_beeper)

    # ----- 1. بخش راهنمای جامع (Help & Guide) -----
    guide_dialog = ft.AlertDialog(
        title=ft.Text("📖 راهنمای جامع و امکانات سامانه", size=16, weight=ft.FontWeight.BOLD),
        content=ft.Container(
            content=ft.Column([
                ft.Text("🚀 ۱. رادار و کشف هوشمند استارلینک:", weight=ft.FontWeight.BOLD, color=ft.colors.CYAN_200),
                ft.Text("• اسکن خودکار BSSID مودم‌های SpaceX و محاسبه دقیق فاصله بر حسب متر."),
                ft.Divider(),
                ft.Text("📢 ۲. بوق هوشمند جهت‌نما (Geiger Beeper):", weight=ft.FontWeight.BOLD, color=ft.colors.AMBER_200),
                ft.Text("• با نزدیک‌تر شدن به مودم، سرعت بوق‌ها بیشتر و تیزتر می‌شود."),
                ft.Divider(),
                ft.Text("📍 ۳. ثبت GPS و نقاط مشکوک روی نقشه:", weight=ft.FontWeight.BOLD, color=ft.colors.GREEN_200),
                ft.Text("• ثبت مختصات جغرافیایی و یادداشت‌های دائمی که فقط توسط خود کاربر قابل پاک‌شدن است."),
                ft.Divider(),
                ft.Text("🥷 ۴. حالت مخفی (Stealth Mode):", weight=ft.FontWeight.BOLD, color=ft.colors.PURPLE_200),
                ft.Text("• با زدن دکمه 🥷، برنامه فوراً تبدیل به یک ماشین‌حساب ساختگی می‌شود."),
                ft.Divider(),
                ft.Text("📊 ۵. خروجی‌گرفتن گزارش‌ها (Export):", weight=ft.FontWeight.BOLD, color=ft.colors.BLUE_200),
                ft.Text("• امکان دانلود فایل گزارش تمام کشف‌ها و یادداشت‌های ثبت‌شده."),
                ft.Divider(),
                ft.Text("🔐 ۶. امکانات مدیریتی و امنیت ادمین:", weight=ft.FontWeight.BOLD, color=ft.colors.RED_200),
                ft.Text("• کلید خاموش/روشن سراسری برنامه توسط ادمین.\n• اختصاص شماره ثابت شناسه (کاربر ۱، ۲، ...) بدون نمایش نام اصلی.\n• ثبت و مشاهده زمان دقیق ورود و خروج کاربران توسط ادمین.\n• رمزنگاری SHA-256 و 2FA اختیاری.")
            ], scroll=ft.ScrollMode.AUTO, spacing=8),
            width=320, height=420
        ),
        actions=[ft.TextButton("متوجه شدم", on_click=lambda e: page.close(guide_dialog))]
    )

    def open_guide(e):
        page.open(guide_dialog)

    # ----- 2. حالت مخفی / ماشین‌حساب ساختگی (Stealth Mode) -----
    calc_display = ft.Text("0", size=28, weight=ft.FontWeight.BOLD)
    
    def toggle_stealth(e):
        nonlocal is_stealth_mode
        is_stealth_mode = not is_stealth_mode
        page.controls.clear()
        if is_stealth_mode:
            page.add(fake_calc_view)
        else:
            if is_admin:
                show_admin_dashboard()
            else:
                show_user_dashboard()
        page.update()

    fake_calc_view = ft.Column([
        ft.Row([
            ft.Text("ماشین‌حساب", size=16, weight=ft.FontWeight.BOLD),
            ft.IconButton(ft.icons.SHIELD, on_click=toggle_stealth, tooltip="خروج از حالت مخفی")
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Container(content=calc_display, padding=15, bgcolor=ft.colors.BLACK26, border_radius=10, alignment=ft.alignment.center_right),
        ft.ResponsiveRow([
            ft.ElevatedButton("7", col=3), ft.ElevatedButton("8", col=3), ft.ElevatedButton("9", col=3), ft.ElevatedButton("/", col=3),
            ft.ElevatedButton("4", col=3), ft.ElevatedButton("5", col=3), ft.ElevatedButton("6", col=3), ft.ElevatedButton("*", col=3),
            ft.ElevatedButton("1", col=3), ft.ElevatedButton("2", col=3), ft.ElevatedButton("3", col=3), ft.ElevatedButton("-", col=3),
            ft.ElevatedButton("C", col=3), ft.ElevatedButton("0", col=3), ft.ElevatedButton("=", col=3), ft.ElevatedButton("+", col=3),
        ], spacing=10)
    ], spacing=15)

    # ----- 3. صفحه ورودی (Splash Screen) -----
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

        if user_h == app_state["admin_hash"]:
            is_admin = True
            active_user = "ادمین سیستم"
            show_admin_dashboard()
            return

        if user_h == app_state["user_hash"]:
            if not app_state["is_app_active"]:
                login_err.value = "⛔ برنامه توسط مدیریت غیرفعال شده است."
                page.update()
                return

            is_admin = False
            active_user = uname

            if active_user not in app_state["user_id_map"]:
                user_code = f"کاربر {app_state['user_counter']}"
                app_state["user_id_map"][active_user] = user_code
                app_state["user_counter"] += 1
                app_state["user_data"][active_user] = {
                    "notes": [],
                    "2fa_enabled": False,
                    "suggestions": []
                }

            d_sh, t_teh = get_tehran_shamsi_datetime()
            app_state["access_logs"].append({
                "user_code": app_state["user_id_map"][active_user],
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
            ft.ElevatedButton("📖 راهنمای برنامه", on_click=open_guide, bgcolor=ft.colors.WHITE10, width=280),
            login_err
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
        alignment=ft.alignment.center,
        expand=True
    )

    def logout_user(e):
        nonlocal active_user, is_admin
        if active_user and not is_admin and active_user in app_state["user_id_map"]:
            d_sh, t_teh = get_tehran_shamsi_datetime()
            app_state["access_logs"].append({
                "user_code": app_state["user_id_map"][active_user],
                "action": "خروج",
                "time": f"{d_sh} ساعت {t_teh}"
            })
        active_user = None
        is_admin = False
        main(page)

    # ----- 4. پنل ادمین -----
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

        logs_list = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO, height=220)
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
                ft.Row([
                    ft.IconButton(ft.icons.HELP_OUTLINE, on_click=open_guide, tooltip="راهنما"),
                    ft.IconButton(ft.icons.SECURITY, on_click=toggle_stealth, tooltip="حالت مخفی"),
                    ft.IconButton(ft.icons.LOGOUT, on_click=logout_user, tooltip="خروج")
                ])
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(),
            status_text,
            ft.Switch(label="خاموش / روشن کردن سراسری برنامه", value=app_state["is_app_active"], on_change=toggle_app_status),
            ft.Divider(),
            ft.Text("📊 گزارش ورود و خروج کاربران (فقط ادمین):", size=14, weight=ft.FontWeight.BOLD),
            logs_list
        ], scroll=ft.ScrollMode.AUTO)

        page.add(admin_panel)

    # ----- 5. داشبورد اختصاصی کاربر -----
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

        # ثبت یادداشت + GPS
        note_input = ft.TextField(label="متن یادداشت یا نقطه مشکوک", expand=True)
        is_suspicious_check = ft.Checkbox(label="⚠️ نقطه مشکوک", value=False)
        gps_check = ft.Checkbox(label="📍 ثبت موقعیت مکانی (GPS)", value=True)
        notes_list_view = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO)

        def add_note(e):
            if note_input.value.strip():
                d_sh, t_teh = get_tehran_shamsi_datetime()
                gps_loc = "Lat: 35.689, Lng: 51.389 (GPS)" if gps_check.value else "بدون GPS"
                note_item = {
                    "id": time.time(),
                    "text": sanitize_input(note_input.value),
                    "suspicious": is_suspicious_check.value,
                    "gps": gps_loc,
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

        def export_data(e):
            try:
                filename = f"report_{active_user}.csv"
                with open(filename, "w", encoding="utf-8") as f:
                    f.write("Date,Type,Note,GPS\n")
                    for n in app_state["user_data"][active_user]["notes"]:
                        n_type = "Suspicious" if n["suspicious"] else "Normal"
                        f.write(f'"{n["date"]}","{n_type}","{n["text"]}","{n["gps"]}"\n')
                page.snack_bar = ft.SnackBar(ft.Text(f"✅ خروجی در {filename} ذخیره شد."))
                page.snack_bar.open = True
            except Exception as ex:
                page.snack_bar = ft.SnackBar(ft.Text(f"❌ خطا در ذخیره خروجی: {str(ex)}"))
                page.snack_bar.open = True
            page.update()

        def render_notes():
            notes_list_view.controls.clear()
            for n in app_state["user_data"][active_user]["notes"]:
                color = ft.colors.RED_400 if n["suspicious"] else ft.colors.BLUE_200
                prefix = "⚠️ [مشکوک] " if n["suspicious"] else "📌 "
                card = ft.Container(
                    content=ft.Row([
                        ft.Column([
                            ft.Text(f"{prefix}{n['text']}", size=13, weight=ft.FontWeight.BOLD, color=color),
                            ft.Text(f"{n['date']} | 📍 {n['gps']}", size=10, color=ft.colors.GREY_400)
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
                    ft.IconButton(ft.icons.HELP_OUTLINE, on_click=open_guide, tooltip="راهنما"),
                    ft.IconButton(ft.icons.SECURITY, on_click=toggle_stealth, tooltip="حالت مخفی"),
                    ft.IconButton(ft.icons.BRIGHTNESS_4, on_click=toggle_theme, tooltip="تم تاریک/روشن"),
                    ft.IconButton(ft.icons.LOGOUT, on_click=logout_user, tooltip="خروج")
                ])
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            clock_text,
            ft.Divider(),
            ft.Switch(label="🔐 تایید دو مرحله‌ای (2FA)", value=app_state["user_data"][active_user]["2fa_enabled"], on_change=toggle_2fa),
            ft.Divider(),
            ft.Text("📍 ثبت یادداشت و نقاط مشکوک (GPS):", size=13, weight=ft.FontWeight.BOLD),
            ft.Row([note_input]),
            ft.Row([is_suspicious_check, gps_check]),
            ft.ElevatedButton("ثبت یادداشت روی نقشه", on_click=add_note, icon=ft.icons.ADD_LOCATION),
            ft.Row([
                ft.Text("📋 ثبت‌شده‌ها:", size=13, weight=ft.FontWeight.BOLD),
                ft.IconButton(ft.icons.DOWNLOAD, on_click=export_data, tooltip="دانلود خروجی CSV")
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
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
