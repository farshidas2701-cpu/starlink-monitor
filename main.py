import flet as ft

def main(page: ft.Page):
    page.title = "سامانه پایش و رادار"
    page.theme_mode = ft.ThemeMode.DARK
    page.rtl = True
    page.padding = 12
    
    # صفحه خوش آمدگویی با پرچم ایران
    def show_splash():
        page.controls.clear()
        flag = ft.Container(
            content=ft.Column([
                ft.Container(height=40, bgcolor="#239f40"),
                ft.Container(height=40, bgcolor="white", content=ft.Text("🇮🇷", size=30)),
                ft.Container(height=40, bgcolor="#da0000")
            ], spacing=0),
            width=200,
            border_radius=10
        )
        page.add(
            ft.Container(
                content=ft.Column([
                    ft.Text("به نام خدا", size=20, weight=ft.FontWeight.BOLD),
                    flag,
                    ft.Text("سامانه جامع پایش و مدیریت امنیتی", size=14, color="green400"),
                    ft.ElevatedButton("ورود به برنامه", on_click=lambda e: show_login())
                ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                expand=True
            )
        )
        page.update()
    
    # صفحه ورود (ماشین حساب)
    display = ft.TextField(value="0", read_only=True, text_align=ft.TextAlign.RIGHT)
    calc_expression = ""
    
    def btn_click(e):
        nonlocal calc_expression
        val = e.control.text
        
        if val == "C":
            calc_expression = ""
            display.value = "0"
        elif val == "=":
            if calc_expression == "0011300":
                show_dashboard("کاربر")
            elif calc_expression == "f09931807880F":
                show_dashboard("ادمین")
            elif calc_expression == "9999":
                show_login()
                page.snack_bar = ft.SnackBar(ft.Text("🚨 امحا شد!"))
                page.snack_bar.open = True
            else:
                try:
                    display.value = str(eval(calc_expression))
                    calc_expression = display.value
                except:
                    display.value = "Error"
                    calc_expression = ""
        else:
            calc_expression += val
            display.value = calc_expression
        page.update()
    
    def show_login():
        page.controls.clear()
        page.add(
            ft.Column([
                ft.Text("🔢 ماشین حساب", size=20, weight=ft.FontWeight.BOLD),
                display,
                ft.Column([
                    ft.Row([ft.ElevatedButton("1", on_click=btn_click), ft.ElevatedButton("2", on_click=btn_click), ft.ElevatedButton("3", on_click=btn_click)]),
                    ft.Row([ft.ElevatedButton("4", on_click=btn_click), ft.ElevatedButton("5", on_click=btn_click), ft.ElevatedButton("6", on_click=btn_click)]),
                    ft.Row([ft.ElevatedButton("7", on_click=btn_click), ft.ElevatedButton("8", on_click=btn_click), ft.ElevatedButton("9", on_click=btn_click)]),
                    ft.Row([ft.ElevatedButton("0", on_click=btn_click), ft.ElevatedButton("C", on_click=btn_click), ft.ElevatedButton("=", on_click=btn_click)]),
                ])
            ])
        )
        page.update()
    
    # داشبورد
    def show_dashboard(role):
        page.controls.clear()
        page.add(
            ft.Column([
                ft.Text(f"👤 {role} عزیز خوش آمدید", size=20, weight=ft.FontWeight.BOLD),
                ft.Text("📱 سامانه پایش و رادار"),
                ft.ElevatedButton("🚪 خروج", on_click=lambda e: show_login()),
            ])
        )
        page.update()
    
    show_splash()

ft.app(target=main)
