import flet as ft
import re
import math
import time
import random
from datetime import datetime

CURRENT_VERSION = "8.0.0-OFFLINE-FULL"

# وضعیت عمومی برنامه
user_store = {
    "notes": [],
    "ram_only_mode": False,
    "stealth_pin": "1234",          # پین ورود عادی
    "panic_pin": "9999",            # پین تخریب اضطراری
    "sound_alert": True
}

def sanitize_input(text: str) -> str:
    return re.sub(r'[\';\"\\<>]', '', text)

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

    def show_toast(msg: str):
        page.snack_bar = ft.SnackBar(ft.Text(msg))
        page.snack_bar.open = True
        page.update()

    def show_section_guide(title: str, description: str):
        dialog = ft.AlertDialog(
            title=ft.Text(f"❓ راهنمای {title}", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400),
            content=ft.Container(
                content=ft.Text(description, size=13, color=ft.Colors.WHITE70),
                width=300, padding=10
            ),
            actions=[ft.TextButton("متوجه شدم", on_click=lambda e: page.close(dialog))]
        )
        page.open(dialog)

    def create_help_button(section_title: str, guide_text: str):
        return ft.Column([
            ft.Container(
                content=ft.IconButton(
                    icon=ft.Icons.QUESTION_MARK,
                    icon_color=ft.Colors.WHITE,
                    bgcolor=ft.Colors.GREEN_600,
                    icon_size=16,
                    on_click=lambda e: show_section_guide(section_title, guide_text),
                    tooltip=f"راهنمای {section_title}"
                ),
                shape=ft.BoxShape.CIRCLE,
                width=32, height=32, alignment=ft.Alignment(0, 0)
            ),
            ft.Text("راهنما", size=10, color=ft.Colors.GREEN_300)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2)

    # ----- ۱. نقشه راداری آفلاین پیشرفته (مستقل از اینترنت) -----
    def open_offline_radar_map(e):
        center_lat, center_lng = 35.6892, 51.3890
        scale = 8000  # مقیاس تبدیل درجه جغرافیایی به پیکسل‌های صفحه

        radar_elements = [
            # لایه‌های گرافیکی شبکه رادار
            ft.Container(width=240, height=240, border=ft.border.all(1, ft.Colors.GREEN_900), border_radius=120, alignment=ft.Alignment(0, 0)),
            ft.Container(width=160, height=160, border=ft.border.all(1, ft.Colors.GREEN_800), border_radius=80, alignment=ft.Alignment(0, 0)),
            ft.Container(width=80, height=80, border=ft.border.all(1, ft.Colors.GREEN_700), border_radius=40, alignment=ft.Alignment(0, 0)),
            # نقطه مرکز (موقعیت کاربر)
            ft.Container(
                content=ft.Icon(ft.Icons.MY_LOCATION, color=ft.Colors.GREEN_400, size=24),
                alignment=ft.Alignment(0, 0)
            )
        ]

        # نگاشت موقعیت مکانی نقاط ثبت‌شده روی گرید
        for n in user_store["notes"]:
            color = ft.Colors.RED_500 if n["suspicious"] else ft.Colors.BLUE_400
            
            # محاسبه انحراف از مرکز (مجموعاً بین -1 تا +1)
            dx = (n["lng"] - center_lng) * scale
            dy = (center_lat - n["lat"]) * scale
            
            # محدود کردن نقاط درون کادر ۲۸۰x۲۸۰
            dx = max(-120, min(120, dx))
            dy = max(-120, min(120, dy))

            # تبدیل فاصله به Alignment نسبی در Flet
            align_x = dx / 140
            align_y = dy / 140

            radar_elements.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.LOCATION_ON, color=color, size=18),
                        ft.Text(n['text'][:8], size=8, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD)
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
                    alignment=ft.Alignment(align_x, align_y),
                    tooltip=f"{n['text']} ({n['gps']})"
                )
            )

        map_dialog = ft.AlertDialog(
            title=ft.Text("🗺️ رادار و نقشه آفلاین (مخصوص نت ملی)", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400),
            content=ft.Container(
                content=ft.Column([
                    ft.Text("موقعیت نسبی نقاط مشکوک و ثبت‌شده نسبت به مرکز:", size=11, color=ft.Colors.WHITE70),
                    ft.Container(
                        content=ft.Stack(
                            controls=radar_elements,
                            alignment=ft.Alignment(0, 0)
                        ),
                        width=280, height=280, bgcolor=ft.Colors.BLACK, border_radius=14, border=ft.border.all(1.5, ft.Colors.GREEN_600)
                    ),
                    ft.Row([
                        ft.Text("🟢 مرکز: شما", size=10, color=ft.Colors.GREEN_400),
                        ft.Text("🔴 مشکوک", size=10, color=ft.Colors.RED_400),
                        ft.Text("🔵 عادی", size=10, color=ft.Colors.BLUE_400)
                    ], alignment=ft.MainAxisAlignment.SPACE_AROUND)
                ], spacing=10),
                width=300, height=360, padding=5
            ),
            actions=[ft.TextButton("بستن", on_click=lambda e: page.close(map_dialog))]
        )
        page.open(map_dialog)

    # ----- ۲. ماشین حساب مخفی -----
    calc_display = ft.Text("0", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400)

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
            elif calc_expression == user_store["panic_pin"]:
                calc_expression = ""
                user_store["notes"].clear()
                is_stealth_mode = False
                page.controls.clear()
                show_user_dashboard()
                show_toast("🚨 امحای اضطراری انجام شد.")
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

    def build_calc_button(text, color=ft.Colors.WHITE10):
        return ft.ElevatedButton(text, on_click=on_calc_btn_click, bgcolor=color, expand=True, height=55)

    fake_calc_view = ft.Column([
        ft.Row([
            ft.Text("ماشین حساب", size=16, weight=ft.FontWeight.BOLD),
            create_help_button("ماشین حساب مخفی", "پین 1234= ورود عادی\n🚨 پین 9999= امحای کامل اطلاعات")
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Container(content=calc_display, padding=15, bgcolor=ft.Colors.BLACK46, border_radius=10, alignment=ft.Alignment(1, 0)),
        ft.Column([
            ft.Row([build_calc_button("7"), build_calc_button("8"), build_calc_button("9"), build_calc_button("/", ft.Colors.ORANGE_800)]),
            ft.Row([build_calc_button("4"), build_calc_button("5"), build_calc_button("6"), build_calc_button("*", ft.Colors.ORANGE_800)]),
            ft.Row([build_calc_button("1"), build_calc_button("2"), build_calc_button("3"), build_calc_button("-", ft.Colors.ORANGE_800)]),
            ft.Row([build_calc_button("C", ft.Colors.RED_800), build_calc_button("0"), build_calc_button("=", ft.Colors.GREEN_800), build_calc_button("+", ft.Colors.ORANGE_800)]),
        ], spacing=8)
    ], spacing=15)

    # ----- ۳. داشبورد اصلی -----
    def show_user_dashboard():
        page.controls.clear()
        
        date_shamsi, time_tehran = get_tehran_shamsi_datetime()
        clock_text = ft.Text(f"📅 {date_shamsi} | ⏰ {time_tehran}", size=12, color=ft.Colors.CYAN_200, weight=ft.FontWeight.BOLD)

        rssi_val_text = ft.Text("-65 dBm", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400)
        distance_text = ft.Text("تخمین فاصله: ~8.5 متر", size=12, color=ft.Colors.AMBER_200)
        rssi_progress = ft.ProgressBar(value=0.65, color=ft.Colors.GREEN_400, bgcolor=ft.Colors.WHITE10)

        def simulate_signal_scan(e):
            val = random.randint(35, 90)
            dist = calculate_fspl_distance(-val)
            rssi_val_text.value = f"-{val} dBm ({'عالی/نزدیک' if val < 50 else 'متوسط' if val < 75 else 'ضعیف'})"
            distance_text.value = f"تخمین فاصله (FSPL): ~{dist} متر"
            rssi_progress.value = (100 - val) / 100
            rssi_progress.color = ft.Colors.RED_400 if val < 50 else ft.Colors.GREEN_400 if val < 75 else ft.Colors.AMBER_400
            
            if val < 50 and user_store["sound_alert"]:
                show_toast("🔊 [هشدار صوتی گایگر] سیگنال بسیار نزدیک است!")
            page.update()

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

        def render_notes():
            notes_list_view.controls.clear()
            for n in user_store["notes"]:
                color = ft.Colors.RED_400 if n["suspicious"] else ft.Colors.BLUE_200
                prefix = "⚠️ [مشکوک] " if n["suspicious"] else "📌 "
                card = ft.Container(
                    content=ft.Row([
                        ft.Column([
                            ft.Text(f"{prefix}{n['text']}", size=13, weight=ft.FontWeight.BOLD, color=color),
                            ft.Text(f"{n['date']} | 📍 {n['gps']}", size=10, color=ft.Colors.GREY_400)
                        ], expand=True),
                        ft.IconButton(ft.Icons.DELETE, icon_color=ft.Colors.RED_500, on_click=lambda e, nid=n["id"]: delete_note(nid))
                    ]),
                    padding=8, bgcolor=ft.Colors.WHITE10, border_radius=8
                )
                notes_list_view.controls.append(card)
            page.update()

        user_panel = ft.Column([
            ft.Row([
                ft.Text("📱 سامانه پیشرفته پایش و رادار", size=15, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400),
                ft.IconButton(ft.Icons.CALCULATOR, on_click=toggle_stealth, tooltip="ماشین حساب مخفی")
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            clock_text,
            ft.Divider(),
            
            # اسکن سیگنال
            ft.Row([
                ft.Text("📈 اسکن شدت سیگنال و تخمین فاصله:", size=13, weight=ft.FontWeight.BOLD),
                create_help_button("اسکن سیگنال", "شدت سیگنال و فاصله بر حسب متر.")
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(
                content=ft.Column([
                    ft.Row([rssi_val_text, distance_text], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    rssi_progress,
                    ft.ElevatedButton("بروزرسانی اسکن 🔄", on_click=simulate_signal_scan, icon=ft.Icons.RADAR)
                ]),
                padding=10, bgcolor=ft.Colors.BLACK26, border_radius=8
            ),
            
            ft.Divider(),
            # ثبت نقاط و مشاهده روی نقشه آفلاین
            ft.Row([
                ft.Text("📍 ثبت نقاط و نقشه آفلاین:", size=13, weight=ft.FontWeight.BOLD),
                create_help_button("نقشه آفلاین", "نقشه داخلی بدون نیاز به اینترنت کار می‌کند.")
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([note_input]),
            ft.Row([is_suspicious_check, gps_check]),
            ft.ElevatedButton("ثبت نقطه روی نقشه", on_click=add_note, icon=ft.Icons.ADD_LOCATION),
            ft.Row([
                ft.Text("📋 موارد ذخیره‌شده:", size=13, weight=ft.FontWeight.BOLD),
                ft.ElevatedButton("مشاهده نقشه راداری آفلاین 🗺️", on_click=open_offline_radar_map, bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            notes_list_view
        ], scroll=ft.ScrollMode.AUTO)

        page.add(user_panel)
        render_notes()

    show_user_dashboard()

ft.app(target=main)
