import flet as ft

def main(page: ft.Page):
    page.title = "سامانه پایش و رادار"
    page.theme_mode = ft.ThemeMode.DARK
    page.rtl = True
    page.padding = 12
    
    def show_login():
        page.controls.clear()
        page.add(
            ft.Column([
                ft.Text("🔐 ورود به سامانه", size=24, weight=ft.FontWeight.BOLD),
                ft.TextField(label="نام کاربری", width=300),
                ft.TextField(label="رمز عبور", password=True, width=300),
                ft.ElevatedButton("ورود", width=300),
                ft.Text("نسخه ساده و تست‌شده", size=10, color="grey500")
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )
        page.update()
    
    show_login()

ft.app(target=main)
