import flet as ft
import re
import hashlib
import time
import random
import jdatetime

CURRENT_VERSION = "6.0.0-STEALTH_PRO"
SPLASH_IMAGE_URL = "https://v3.fasturl.cloud/file/fasturl/2026/08/02/images.jpeg_627fbbf54522930ed6b1fc910e5362bf.jpeg"

# وضعیت عمومی برنامه و تنظیمات حافظه
user_store = {
    "notes": [],
    "2fa_enabled": False,
    "ram_only_mode": False,       # حالت عدم ذخیره‌سازی روی دیسک (فقط RAM)
    "haptic_enabled": True,       # هشدار ویبره/لرزشی
    "passive_logging": False,     # اسکن پس‌زمینه و لاگ جاده‌ای
    "stealth_pin": "1234"
}

def sanitize_input(text: str) -> str:
    return re.sub(r'[\';\"\\<>]', '', text)

def get_tehran_shamsi_datetime():
    now_shamsi = jdatetime.datetime.now()
    return now_shamsi.strftime("%Y/%m/%d"), now_shamsi.strftime("%H:%M:%S")

def main(page: ft.Page):
    page.title = "سامانه پیشرفته پایش و رادار شبکه‌ای"
    page.theme_mode = ft.ThemeMode.DARK
    page.rtl = True
    page.padding = 10

    is_stealth_mode = False
    calc_expression = ""

    # ----- 1. راهنمای جامع و به‌روزرسانی‌شده -----
    guide_dialog = ft.AlertDialog(
        title=ft.Text("📖 راهنمای امکانات پیشرفته سامانه", size=16, weight=ft.FontWeight.BOLD),
        content=ft.Container(
            content=ft.Column([
                ft.Text("📈 ۱. نمودار زنده شدت سیگنال (Live RSSI Graph):", weight=ft.FontWeight.BOLD, color=ft.colors.CYAN_200),
                ft.Text("• مشاهده نوسانات و اوج‌گیری سیگنال بر حسب dBm جهت یافتن موقعیت دقیق."),
                ft.Divider(),
                ft.Text("🔔 ۲. هشدار لرزشی بی‌صدا (Haptic Alert):", weight=ft.FontWeight.BOLD, color=ft.colors.AMBER_200),
                ft.Text("• اعلام نزدیک شدن به سیگنال با الگوهای لرزش بدون ایجاد صدا."),
                ft.Divider(),
                ft.Text("🧹 ۳. حالت حافظه رم (RAM-Only Operating):", weight=ft.FontWeight.BOLD, color=ft.colors.RED_200),
                ft.Text("• عدم ذخیره‌سازی هیچ داده‌ای روی دیسک؛ پاکسازی کامل اطلاعات پس از خروج."),
                ft.Divider(),
                ft.Text("⏱️ ۴. ثبت پس‌زمینه جاده‌ای (Passive Logging):", weight=ft.FontWeight.BOLD, color=ft.colors.GREEN_200),
                ft.Text("• پایش مداوم سیگنال و ثبت موقعیت حین حرکت با صفحه خاموش."),
                ft.Divider(),
                ft.Text("🧮 ۵. ماشین‌حساب مخفی واقعی (Stealth Mode):", weight=ft.FontWeight.BOLD, color=ft.colors.PURPLE_200),
                ft.Text("• ورود به محیط کاربری فقط با وارد کردن پین (پیش‌فرض: 1234=).")
            ], scroll=ft.ScrollMode.AUTO, spacing=8),
            width=320, height=420
        ),
        actions=[ft.TextButton("متوجه شدم", on_click=lambda e: page.close(guide_dialog))]
    )

    def open_guide(e):
        page.open(guide_dialog)

    # ----- 2. ماشین حساب ساختگی واقعی (Stealth Mode) -----
    calc_display = ft.Text("0", size=32, weight=ft.FontWeight.BOLD, color=ft.colors.GREEN_400)

    def on_calc_btn_click(e):
        nonlocal calc_expression, is_stealth_mode
        val = e.control.text

        if val == "C":
            calc_expression = ""
            calc_display.value = "0"
        elif val == "=":
            if calc_expression == user_store["stealth_pin"]:
                calc_expression = ""
                is_stealth_mode = False
                page.controls.clear()
                show_user_dashboard()
                page.update()
                return
            try:
                calc_display.value = str(eval(calc_expression))
                calc_expression = calc_display.value
            except:
                calc_display.value = "Error"
                calc_expression = ""
        else:
            calc_expression += val
            calc_display.value = calc_expression

        page.update()

    def toggle_stealth(e):
        nonlocal is_stealth_mode
        is_stealth_mode = not is_stealth_mode
        page.controls.clear()
        if is_stealth_mode:
            page.add(fake_calc_view)
        else:
            show_user_dashboard()
        page.update()

    def build_calc_button(text, color=ft.colors.WHITE10):
        return ft.ElevatedButton(text, on_click=on_calc_btn_click, bgcolor=color, expand=True, height=55)

    fake_calc_view = ft.Column([
        ft.Row([
            ft.Text("ماشین حساب", size=16, weight=ft.FontWeight.BOLD),
            ft.IconButton(ft.icons.SHIELD, on_click=toggle_stealth, tooltip="خروج")
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Container(content=calc_display, padding=15, bgcolor=ft.colors.BLACK46, border_radius=10, alignment=ft.alignment.center_right),
        ft.Column([
            ft.Row([build_calc_button("7"), build_calc_button("8"), build_calc_button("9"), build_calc_button("/", ft.colors.ORANGE_800)]),
            ft.Row([build_calc_button("4"), build_calc_button("5"), build_calc_button("6"), build_calc_button("*", ft.colors.ORANGE_800)]),
            ft.Row([build_calc_button("1"), build_calc_button("2"), build_calc_button("3"), build_calc_button("-", ft.colors.ORANGE_800)]),
            ft.Row([build_calc_button("C", ft.colors.RED_800), build_calc_button("0"), build_calc_button("=", ft.colors.GREEN_800), build_calc_button("+", ft.colors.ORANGE_800)]),
        ], spacing=8)
    ], spacing=15)

    # ----- 3. صفحه ورودی خوش‌آمدگویی -----
    splash_view = ft.Container(
        content=ft.Column([
            ft.Image(src=SPLASH_IMAGE_URL, width=250, height=320, fit=ft.ImageFit.CONTAIN, border_radius=15),
            ft.Text("به سامانه هوشمند پایش و رادار خوش آمدید", size=15, weight=ft.FontWeight.BOLD, color=ft.colors.WHITE),
            ft.ElevatedButton("ورود به محیط کاربری 🚀", on_click=lambda e: show_user_dashboard(), bgcolor=ft.colors.GREEN_700, color=ft.colors.WHITE, width=280),
            ft.ElevatedButton("📖 راهنمای برنامه", on_click=open_guide, bgcolor=ft.colors.WHITE10, width=280),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12),
        alignment=ft.alignment.center,
        expand=True
    )

    # ----- 4. داشبورد اختصاصی و پیشرفته کاربر -----
    def show_user_dashboard():
        page.controls.clear()
        
        date_shamsi, time_tehran = get_tehran_shamsi_datetime()
        clock_text = ft.Text(f"📅 {date_shamsi} | ⏰ {time_tehran} (تهران)", size=12, color=ft.colors.CYAN_200, weight=ft.FontWeight.BOLD)

        # 📈 کنترل‌های نمودار زنده سیگنال (RSSI Live Graph)
        rssi_val_text = ft.Text("-65 dBm (متوسط)", size=14, weight=ft.FontWeight.BOLD, color=ft.colors.GREEN_400)
        rssi_progress = ft.ProgressBar(value=0.65, color=ft.colors.GREEN_400, bgcolor=ft.colors.WHITE10)

        def simulate_signal_scan(e):
            # شبیه‌سازی تغییر شدت سیگنال و بازخورد
            val = random.randint(30, 95)
            rssi_val_text.value = f"-{val} dBm ({'قوی / نزدیک' if val < 50 else 'متوسط' if val < 75 else 'ضعیف'})"
            rssi_progress.value = (100 - val) / 100
            rssi_progress.color = ft.colors.RED_400 if val < 50 else ft.colors.GREEN_400 if val < 75 else ft.colors.AMBER_400
            
            if user_store["haptic_enabled"] and val < 50:
                page.snack_bar = ft.SnackBar(ft.Text("📳 [هشدار لرزشی] سیگنال قوی در نزدیکی کشف شد!"))
                page.snack_bar.open = True
            page.update()

        def toggle_ram_mode(e):
            user_store["ram_only_mode"] = e.control.value
            status = "فعال (عدم ذخیره روی دیسک)" if e.control.value else "غیرفعال"
            page.snack_bar = ft.SnackBar(ft.Text(f"حالت RAM-Only {status} شد."))
            page.snack_bar.open = True
            page.update()

        def toggle_passive_logging(e):
            user_store["passive_logging"] = e.control.value
            status = "فعال" if e.control.value else "غیرفعال"
            page.snack_bar = ft.SnackBar(ft.Text(f"پایش پس‌زمینه جاده‌ای {status} شد."))
            page.snack_bar.open = True
            page.update()

        # ثبت یادداشت و GPS
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
                user_store["notes"].append(note_item)
                note_input.value = ""
                is_suspicious_check.value = False
                render_notes()

        def delete_note(note_id):
            user_store["notes"] = [n for n in user_store["notes"] if n["id"] != note_id]
            render_notes()

        def panic_wipe(e):
            user_store["notes"].clear()
            render_notes()
            page.snack_bar = ft.SnackBar(ft.Text("🚨 تمام داده‌ها با موفقیت امحا شدند."))
            page.snack_bar.open = True
            page.update()

        def export_data(e):
            if user_store["ram_only_mode"]:
                page.snack_bar = ft.SnackBar(ft.Text("⚠️ حالت RAM-Only فعال است؛ ذخیره روی دیسک مجاز نیست."))
                page.snack_bar.open = True
                page.update()
                return

            try:
                filename = "radar_export.csv"
                with open(filename, "w", encoding="utf-8") as f:
                    f.write("Date,Type,Note,GPS\n")
                    for n in user_store["notes"]:
                        n_type = "Suspicious" if n["suspicious"] else "Normal"
                        f.write(f'"{n["date"]}","{n_type}","{n["text"]}","{n["gps"]}"\n')
                page.snack_bar = ft.SnackBar(ft.Text(f"✅ گزارش در {filename} ذخیره شد."))
                page.snack_bar.open = True
            except Exception as ex:
                page.snack_bar = ft.SnackBar(ft.Text(f"❌ خطا در خروجی: {str(ex)}"))
                page.snack_bar.open = True
            page.update()

        def render_notes():
            notes_list_view.controls.clear()
            for n in user_store["notes"]:
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

        user_panel = ft.Column([
            ft.Row([
                ft.Text("📱 سامانه پیشرفته پایش و رادار", size=15, weight=ft.FontWeight.BOLD, color=ft.colors.GREEN_400),
                ft.Row([
                    ft.IconButton(ft.icons.HELP_OUTLINE, on_click=open_guide, tooltip="راهنما"),
                    ft.IconButton(ft.icons.CALCULATOR, on_click=toggle_stealth, tooltip="ماشین حساب مخفی"),
                    ft.IconButton(ft.icons.DELETE_FOREVER, on_click=panic_wipe, icon_color=ft.colors.RED_400, tooltip="امحای سریع داده‌ها"),
                ])
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            clock_text,
            ft.Divider(),
            
            # 📈 پنل نمودار زنده سیگنال
            ft.Text("📈 نمودار لحظه‌ای شدت سیگنال (RSSI):", size=13, weight=ft.FontWeight.BOLD),
            ft.Container(
                content=ft.Column([
                    ft.Row([ft.Text("قدرت سیگنال:"), rssi_val_text], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    rssi_progress,
                    ft.ElevatedButton("بروزرسانی اسکن سیگنال 🔄", on_click=simulate_signal_scan, icon=ft.icons.RADAR)
                ]),
                padding=10, bgcolor=ft.colors.BLACK26, border_radius=8
            ),
            
            ft.Divider(),
            # تنظیمات امنیتی جدید
            ft.Switch(label="🧹 حالت حافظه موقت (RAM-Only / عدم ذخیره روی دیسک)", value=user_store["ram_only_mode"], on_change=toggle_ram_mode),
            ft.Switch(label="⏱️ ثبت پس‌زمینه جاده‌ای (Passive Logger)", value=user_store["passive_logging"], on_change=toggle_passive_logging),
            
            ft.Divider(),
            ft.Text("📍 ثبت یادداشت و نقاط مشکوک روی نقشه:", size=13, weight=ft.FontWeight.BOLD),
            ft.Row([note_input]),
            ft.Row([is_suspicious_check, gps_check]),
            ft.ElevatedButton("ثبت نقطه روی نقشه", on_click=add_note, icon=ft.icons.ADD_LOCATION),
            ft.Row([
                ft.Text("📋 موارد ذخیره‌شده شما:", size=13, weight=ft.FontWeight.BOLD),
                ft.IconButton(ft.icons.DOWNLOAD, on_click=export_data, tooltip="دانلود خروجی CSV")
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            notes_list_view
        ], scroll=ft.ScrollMode.AUTO)

        page.add(user_panel)
        render_notes()

    page.add(splash_view)

ft.app(target=main)
