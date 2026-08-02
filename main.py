import flet as ft
import time
from datetime import datetime

# تاریخ شمسی ساده
def get_now_shamsi():
    now = datetime.now()
    return f"{now.year}/{now.month:02d}/{now.day:02d} - {now.strftime('%H:%M:%S')}"

user_store = {
    "notes": [],
    "user_logs": [],
    "user_counter": 1,
    "user_pin": "0011300",
    "admin_pin": "f09931807880F",
    "panic_pin": "9999",
    "current_role": None,
    "current_user_name": "",
    "failed_attempts": 0,
    "lockout_until": 0
}

def main(page: ft.Page):
    page.title = "سامانه جامع پایش"
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
                ft.Container(height=40, bgcolor="#239f40"),
                ft.Container(height=40, bgcolor="white", content=ft.Text("🇮🇷", size=24)),
                ft.Container(height=40, bgcolor="#da0000")
            ], spacing=0),
            width=180,
            border_radius=10
        )
        page.add(
            ft.Container(
                content=ft.Column([
                    ft.Text("به نام خدا", size=18, weight=ft.FontWeight.BOLD),
                    flag,
                    ft.Text("سامانه جامع پایش و مدیریت", size=14, color="green400"),
                    ft.ElevatedButton("ورود به برنامه 🚀", on_click=lambda e: show_login(), bgcolor="green800", color="white")
                ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12),
                expand=True
            )
        )
        page.update()

    def open_change_pin_dialog(e):
        is_admin = (user_store["current_role"] == "admin")
        pin_input = ft.TextField(label="رمز جدید کاربران", password=True, can_reveal_password=True)

        def save_pin(e):
            if pin_input.value and pin_input.value.strip():
                user_store["user_pin"] = pin_input.value.strip()
                page.close(change_pin_dialog)
                show_toast("🔑 رمز تغییر یافت.")
            else:
                show_toast("⚠️ رمز معتبر وارد کنید.")

        change_pin_dialog = ft.AlertDialog(
            title=ft.Text("تغییر رمز", size=14, weight=ft.FontWeight.BOLD),
            content=ft.Container(content=ft.Column([pin_input], spacing=10), width=250, padding=5),
            actions=[
                ft.TextButton("انصراف", on_click=lambda e: page.close(change_pin_dialog)),
                ft.ElevatedButton("ذخیره", on_click=save_pin, bgcolor="green800", color="white")
            ]
        )
        page.open(change_pin_dialog)

    def open_logs_dialog(e):
        log_items = []
        for log in reversed(user_store["user_logs"][-10:]):
            log_items.append(
                ft.Container(
                    content=ft.Column([
                        ft.Text(f"👤 {log['user']}", size=12, weight=ft.FontWeight.BOLD),
                        ft.Text(f"🕐 {log['login_time']}", size=10),
                    ], spacing=2),
                    padding=5, bgcolor="white10", border_radius=5
                )
            )
        logs_dialog = ft.AlertDialog(
            title=ft.Text("📋 لاگ‌های اخیر", size=14, weight=ft.FontWeight.BOLD),
            content=ft.Container(content=ft.Column(log_items, scroll=ft.ScrollMode.AUTO, spacing=5), width=280, height=250),
            actions=[ft.TextButton("بستن", on_click=lambda e: page.close(logs_dialog))]
        )
        page.open(logs_dialog)

    calc_display = ft.TextField(value="0", read_only=True, text_align=ft.TextAlign.RIGHT, text_size=20, bgcolor="black46", border_radius=8)

    def on_calc_btn_click(e):
        nonlocal calc_expression
        val = e.control.text

        if time.time() < user_store["lockout_until"]:
            remaining = int(user_store["lockout_until"] - time.time())
            show_toast(f"⏳ {remaining} ثانیه صبر کنید")
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
                user_store["user_logs"].append({"user": user_name, "login_time": get_now_shamsi()})
                show_dashboard()
                show_toast(f"👤 خوش آمدید {user_name}")
                return
            elif calc_expression == user_store["admin_pin"]:
                calc_expression = ""
                user_store["failed_attempts"] = 0
                user_store["current_role"] = "admin"
                user_store["current_user_name"] = "ادمین"
                user_store["user_logs"].append({"user": "ادمین", "login_time": get_now_shamsi()})
                show_dashboard()
                show_toast("👑 ورود ادمین")
                return
            elif calc_expression == user_store["panic_pin"]:
                calc_expression = ""
                user_store["notes"].clear()
                user_store["user_logs"].clear()
                show_login()
                show_toast("🚨 داده‌ها پاک شدند")
                return
            try:
                calc_display.value = str(eval(calc_expression))
                calc_expression = calc_display.value
            except:
                user_store["failed_attempts"] += 1
                if user_store["failed_attempts"] >= 3:
                    user_store["lockout_until"] = time.time() + 15
                    show_toast("🚫 ۳ تلاش اشتباه، قفل ۱۵ ثانیه")
                calc_display.value = "Error"
                calc_expression = ""
        else:
            calc_expression += val
            calc_display.value = calc_expression
        page.update()

    def build_calc_button(text, color="white10"):
        return ft.ElevatedButton(text, on_click=on_calc_btn_click, bgcolor=color, expand=True, height=45)

    def logout(e=None):
        if user_store["user_logs"]:
            user_store["user_logs"][-1]["logout_time"] = get_now_shamsi()
        show_login()

    def show_login():
        user_store["current_role"] = None
        user_store["current_user_name"] = ""
        page.controls.clear()
        page.add(
            ft.Column([
                ft.Row([ft.Text("🔢 ماشین حساب", size=18, weight=ft.FontWeight.BOLD)]),
                calc_display,
                ft.Column([
                    ft.Row([build_calc_button("C", "red800"), build_calc_button("/", "orange800")]),
                    ft.Row([build_calc_button("7"), build_calc_button("8"), build_calc_button("9"), build_calc_button("*", "orange800")]),
                    ft.Row([build_calc_button("4"), build_calc_button("5"), build_calc_button("6"), build_calc_button("-", "orange800")]),
                    ft.Row([build_calc_button("1"), build_calc_button("2"), build_calc_button("3"), build_calc_button("+", "orange800")]),
                    ft.Row([build_calc_button("0"), build_calc_button("=", "green800")], spacing=8)
                ], spacing=5)
            ], spacing=10)
        )
        page.update()

    def show_dashboard():
        page.controls.clear()
        is_admin = (user_store["current_role"] == "admin")
        
        notes_input = ft.TextField(label="متن یادداشت", expand=True)
        notes_list = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO)

        def add_note(e):
            if notes_input.value.strip():
                user_store["notes"].append({
                    "id": time.time(),
                    "text": notes_input.value.strip(),
                    "by": user_store["current_user_name"]
                })
                notes_input.value = ""
                render_notes()

        def delete_note(nid):
            user_store["notes"] = [n for n in user_store["notes"] if n["id"] != nid]
            render_notes()

        def render_notes():
            notes_list.controls.clear()
            user_notes = user_store["notes"] if is_admin else [n for n in user_store["notes"] if n.get("by") == user_store["current_user_name"]]
            for n in user_notes:
                notes_list.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Text(f"📌 {n['text']}", size=13, expand=True),
                            ft.ElevatedButton("❌", on_click=lambda e, nid=n["id"]: delete_note(nid), bgcolor="red900", height=28)
                        ]),
                        padding=6, bgcolor="white10", border_radius=6
                    )
                )
            page.update()

        dashboard = [
            ft.Row([
                ft.Text("📱 پایش", size=16, weight=ft.FontWeight.BOLD, color="green400"),
                ft.Row([
                    ft.ElevatedButton("🚨 قفل", on_click=logout, bgcolor="red900", height=30),
                    ft.ElevatedButton("🔑 رمز", on_click=open_change_pin_dialog, bgcolor="blue800", height=30)
                ], spacing=5)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Text(f"👤 {user_store['current_user_name']}", size=12, color="cyan300"),
            ft.Divider(),
            ft.Text("📝 یادداشت‌ها", size=13, weight=ft.FontWeight.BOLD),
            ft.Row([notes_input, ft.ElevatedButton("➕", on_click=add_note)]),
            notes_list,
            ft.Row([
                ft.ElevatedButton("📋 لاگ‌ها", on_click=open_logs_dialog, bgcolor="amber900", height=30),
                ft.ElevatedButton("🗑️ پاک کردن همه", on_click=lambda e: clear_all(), bgcolor="red800", height=30) if is_admin else ft.Container()
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        ]

        def clear_all():
            user_store["notes"].clear()
            render_notes()
            show_toast("🗑️ همه یادداشت‌ها پاک شدند")

        page.add(ft.Column(dashboard, scroll=ft.ScrollMode.AUTO))
        render_notes()

    show_splash()

ft.app(target=main)
