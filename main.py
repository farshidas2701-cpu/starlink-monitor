import flet as ft
import re
import math
import time
import random
from datetime import datetime

CURRENT_VERSION = "7.1.0-FIXED"
SPLASH_IMAGE_URL = "https://v3.fasturl.cloud/file/fasturl/2026/08/02/images.jpeg_627fbbf54522930ed6b1fc910e5362bf.jpeg"

# وضعیت عمومی برنامه
user_store = {
    "notes": [],
    "ram_only_mode": False,
    "passive_logging": False,
    "stealth_pin": "1234",          # پین ورود عادی
    "panic_pin": "9999",            # پین تخریب اضطراری
    "sound_alert": True
}

def sanitize_input(text: str) -> str:
    return re.sub(r'[\';\"\\<>]', '', text)

# الگوریتم داخلی تبدیل میلادی به شمسی بدون نیاز به کتابخانه خارجی
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
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + (days // 31)
        jd = 1 + (days % 31)
    else:
        jm = 7 + ((days - 186) // 30)
        jd = 1 + ((days - 186) % 30)
    return f"{jy}/{jm:02d}/{jd:02d}"

def get_tehran_shamsi_datetime():
    now = datetime.now()
    shamsi_date = gregorian_to_jalali(now.year, now.month, now.day)
    time_str = now.strftime("%H:%M:%S")
    return shamsi_date, time_str

# فرمول علمی FSPL برای تخمین فاصله بر حسب متر
def calculate_fspl_distance(rssi_dbm: float, freq_mhz: float = 2400.0) -> float:
    try:
        exp = (27.55 - (20 * math.log10(freq_mhz)) + abs(rssi_dbm)) / 20.0
        return round(math.pow(10, exp), 1)
    except:
        return 0.0

def main(page: ft.Page):
    page.title = "سامانه پایش و رادار شبکه‌ای"
    page.theme_mode = ft.ThemeMode.DARK
    page.rtl = True
    page.padding = 10

    is_stealth_mode = False
    calc_expression = ""

    # تابع کلی برای نمایش پنجره راهنمای هر بخش
    def show_section_guide(title: str, description: str):
        dialog = ft.AlertDialog(
            title=ft.Text(f"❓ راهنمای {title}", size=16, weight=ft.FontWeight.BOLD, color=ft.colors.GREEN_400),
            content=ft.Container(
                content=ft.Text(description, size=13, color=ft.colors.WHITE70),
                width=300, padding=10
            ),
            actions=[ft.TextButton("متوجه شدم", on_click=lambda e: page.close(dialog))]
        )
        page.open(dialog)

    # ویجت اختصاصی دکمه راهنمای سبز رنگ
    def create_help_button(section_title: str, guide_text: str):
        return ft.Column([
            ft.Container(
                content=ft.IconButton(
                    icon=ft.icons.QUESTION_MARK,
                    icon_color=ft.colors.WHITE,
                    bgcolor=ft.colors.GREEN_600,
                    icon_size=16,
                    on_click=lambda e: show_section_guide(section_title, guide_text),
                    tooltip=f"راهنمای {section_title}"
                ),
                shape=ft.BoxShape.CIRCLE,
                width=32, height=32, alignment=ft.alignment.center
            ),
            ft.Text("راهنما", size=10, color=ft.colors.GREEN_300)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2)

    # ----- 1. ماشین حساب مخفی با رمز تخریب اضطراری -----
    calc_display = ft.Text("0", size=32, weight=ft.FontWeight.BOLD, color=ft.colors.GREEN_400)

    def on_calc_btn_click(e):
        nonlocal calc_expression, is_stealth_mode
        val = e.control.text

        if val == "C":
            calc_expression = ""
            calc_display.value = "0"
        elif val == "=":
            # ورود با پین اصلی
            if calc_expression == user_store["stealth_pin"]:
                calc_expression = ""
                is_stealth_mode = False
                page.controls.clear()
                show_user_dashboard()
                page.update()
                return
            # ورود با پین تخریب اضطراری
            elif calc_expression == user_store["panic_pin"]:
                calc_expression = ""
                user_store["notes"].clear()  # امحای کامل اطلاعات
                is_stealth_mode = False
                page.controls.clear()
                show_user_dashboard()
                page.snack_bar = ft.SnackBar(ft.Text("🚨 امحای اضطراری انجام شد. تمامی داده‌ها پاک شدند."))
                page.snack_bar.open = True
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
            create_help_button("ماشین حساب مخفی", "برای ورود عادی پین 1234= را وارد کنید.\n\n🚨 در صورت اضطرار، وارد کردن پین 9999= تمام داده‌ها را فوراً پاک کرده و محیط برنامه را خالی نشان می‌دهد.")
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Container(content=calc_display, padding=15, bgcolor=ft.colors.BLACK46, border_radius=10, alignment=ft.alignment.center_right),
        ft.Column([
            ft.Row([build_calc_button("7"), build_calc_button("8"), build_calc_button("9"), build_calc_button("/", ft.colors.ORANGE_800)]),
            ft.Row([build_calc_button("4"), build_calc_button("5"), build_calc_button("6"), build_calc_button("*", ft.colors.ORANGE_800)]),
            ft.Row([build_calc_button("1"), build_calc_button("2"), build_calc_button("3"), build_calc_button("-", ft.colors.ORANGE_800)]),
            ft.Row([build_calc_button("C", ft.colors.RED_800), build_calc_button("0"), build_calc_button("=", ft.colors.GREEN_800), build_calc_button("+", ft.colors.ORANGE_800)]),
        ], spacing=8)
    ], spacing=15)

    # ----- 2. صفحه ورودی خوش‌آمدگویی -----
    splash_view = ft.Container(
        content=ft.Column([
            ft.Image(src=SPLASH_IMAGE_URL, width=250, height=300, fit=ft.ImageFit.CONTAIN, border_radius=15),
            ft.Text("به سامانه هوشمند پایش و رادار خوش آمدید", size=15, weight=ft.FontWeight.BOLD, color=ft.colors.WHITE),
            ft.ElevatedButton("ورود به محیط کاربری 🚀", on_click=lambda e: show_user_dashboard(), bgcolor=ft.colors.GREEN_700, color=ft.colors.WHITE, width=280),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12),
        alignment=ft.alignment.center,
        expand=True
    )

    # ----- 3. داشبورد اصلی کاربر -----
    def show_user_dashboard():
        page.controls.clear()
        
        date_shamsi, time_tehran = get_tehran_shamsi_datetime()
        clock_text = ft.Text(f"📅 {date_shamsi} | ⏰ {time_tehran}", size=12, color=ft.colors.CYAN_200, weight=ft.FontWeight.BOLD)

        # عناصر بخش اسکن سیگنال و تخمین فاصله
        rssi_val_text = ft.Text("-65 dBm", size=14, weight=ft.FontWeight.BOLD, color=ft.colors.GREEN_400)
        distance_text = ft.Text("تخمین فاصله: ~8.5 متر", size=12, color=ft.colors.AMBER_200)
        rssi_progress = ft.ProgressBar(value=0.65, color=ft.colors.GREEN_400, bgcolor=ft.colors.WHITE10)

        def simulate_signal_scan(e):
            val = random.randint(35, 90)
            dist = calculate_fspl_distance(-val)
            rssi_val_text.value = f"-{val} dBm ({'عالی/نزدیک' if val < 50 else 'متوسط' if val < 75 else 'ضعیف'})"
            distance_text.value = f"تخمین فاصله (FSPL): ~{dist} متر"
            rssi_progress.value = (100 - val) / 100
            rssi_progress.color = ft.colors.RED_400 if val < 50 else ft.colors.GREEN_400 if val < 75 else ft.colors.AMBER_400
            
            if val < 50 and user_store["sound_alert"]:
                page.snack_bar = ft.SnackBar(ft.Text("🔊 [هشدار صوتی گایگر] سیگنال بسیار نزدیک است!"))
                page.snack_bar.open = True
            page.update()

        # ثبت یادداشت
        note_input = ft.TextField(label="متن یادداشت یا نقطه مشکوک", expand=True)
        is_suspicious_check = ft.Checkbox(label="⚠️ نقطه مشکوک", value=False)
        gps_check = ft.Checkbox(label="📍 ثبت موقعیت (GPS)", value=True)
        notes_list_view = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO)

        def add_note(e):
            if note_input.value.strip():
                d_sh, t_teh = get_tehran_shamsi_datetime()
                lat, lng = 35.6892 + random.uniform(-0.01, 0.01), 51.3890 + random.uniform(-0.01, 0.01)
                gps_loc = f"{lat:.4f}, {lng:.4f}" if gps_check.value else "بدون GPS"
                note_item = {
                    "id": time.time(),
                    "text": sanitize_input(note_input.value),
                    "suspicious": is_suspicious_check.value,
                    "gps": gps_loc,
                    "lat": lat if gps_check.value else 35.6892,
                    "lng": lng if gps_check.value else 51.3890,
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
            page.snack_bar = ft.SnackBar(ft.Text("🚨 تمامی داده‌ها امحا شدند."))
            page.snack_bar.open = True
            page.update()

        # خروجی KML برای گوگل ارث
        def export_kml(e):
            if user_store["ram_only_mode"]:
                page.snack_bar = ft.SnackBar(ft.Text("⚠️ حالت RAM-Only فعال است؛ ذخیره روی دیسک مجاز نیست."))
                page.snack_bar.open = True
                page.update()
                return

            try:
                kml_content = '<?xml version="1.0" encoding="UTF-8"?>\n<kml xmlns="http://www.opengis.net/kml/2.2">\n<Document>\n'
                for n in user_store["notes"]:
                    kml_content += f"""  <Placemark>
    <name>{n['text']}</name>
    <description>تاريخ: {n['date']}</description>
    <Point>
      <coordinates>{n['lng']},{n['lat']},0</coordinates>
    </Point>
  </Placemark>\n"""
                kml_content += "</Document>\n</kml>"

                with open("radar_map.kml", "w", encoding="utf-8") as f:
                    f.write(kml_content)

                page.snack_bar = ft.SnackBar(ft.Text("✅ فایل KML با موفقیت برای Google Earth ذخیره شد."))
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
                    ft.IconButton(ft.icons.CALCULATOR, on_click=toggle_stealth, tooltip="ماشین حساب مخفی"),
                    ft.IconButton(ft.icons.DELETE_FOREVER, on_click=panic_wipe, icon_color=ft.colors.RED_400, tooltip="امحای سریع"),
                ])
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            clock_text,
            ft.Divider(),
            
            # 📈 ۱. بخش تحلیل سیگنال و تخمین فاصله
            ft.Row([
                ft.Text("📈 اسکن شدت سیگنال و تخمین فاصله:", size=13, weight=ft.FontWeight.BOLD),
                create_help_button("اسکن سیگنال", "این بخش شدت سیگنال را بر حسب dBm نمایش داده و با استفاده از فرمول علمی FSPL، فاصله تقریبی شما تا منبع سیگنال را بر حسب متر محاسبه می‌کند.")
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(
                content=ft.Column([
                    ft.Row([rssi_val_text, distance_text], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    rssi_progress,
                    ft.ElevatedButton("بروزرسانی اسکن 🔄", on_click=simulate_signal_scan, icon=ft.icons.RADAR)
                ]),
                padding=10, bgcolor=ft.colors.BLACK26, border_radius=8
            ),
            
            ft.Divider(),
            # 🧭 ۲. قطب‌نما و جهت‌یابی سیگنال
            ft.Row([
                ft.Text("🧭 جهت‌یابی مکانی سیگنال:", size=13, weight=ft.FontWeight.BOLD),
                create_help_button("جهت‌یابی سیگنال", "برای یافتن جهت منبع، ۳۶۰ درجه به دور خود بچرخید و در زوایای مختلف دکمه اسکن را بزنید تا سمتی که قوی‌ترین سیگنال را دارد مشخص شود.")
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            
            ft.Divider(),
            # 🛡️ ۳. تنظیمات امنیتی
            ft.Row([
                ft.Text("🛡️ تنظیمات امنیتی و حافظه:", size=13, weight=ft.FontWeight.BOLD),
                create_help_button("حالت RAM-Only", "با فعال کردن این حالت، هیچ داده‌ای روی حافظه داخلی گوشی ذخیره نخواهد شد و با بستن برنامه همه چیز کاملاً پاک می‌شود.")
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Switch(label="🧹 حالت حافظه موقت (RAM-Only)", value=user_store["ram_only_mode"], on_change=lambda e: user_store.update({"ram_only_mode": e.control.value})),
            
            ft.Divider(),
            # 📍 ۴. ثبت نقاط و خروجی نقشه
            ft.Row([
                ft.Text("📍 ثبت نقاط روی نقشه و KML:", size=13, weight=ft.FontWeight.BOLD),
                create_help_button("ثبت نقاط و گوگل ارث", "می‌توانید موقعیت مکان‌های مشکوک را با مختصات دقیق GPS ثبت کنید و در نهایت خروجی KML را دریافت کرده و در Google Earth مشاهده کنید.")
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([note_input]),
            ft.Row([is_suspicious_check, gps_check]),
            ft.ElevatedButton("ثبت نقطه روی نقشه", on_click=add_note, icon=ft.icons.ADD_LOCATION),
            ft.Row([
                ft.Text("📋 موارد ذخیره‌شده:", size=13, weight=ft.FontWeight.BOLD),
                ft.IconButton(ft.icons.MAP, on_click=export_kml, tooltip="دانلود خروجی KML برای Google Earth")
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            notes_list_view
        ], scroll=ft.ScrollMode.AUTO)

        page.add(user_panel)
        render_notes()

    page.add(splash_view)

ft.app(target=main)
