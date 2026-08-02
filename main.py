import flet as ft

def main(page: ft.Page):
    page.title = "Starlink"
    page.theme_mode = ft.ThemeMode.DARK
    
    page.add(
        ft.Text("✅ Starlink App", size=30, weight=ft.FontWeight.BOLD),
        ft.Text("اپلیکیشن با موفقیت ساخته شد!", size=16, color="green400"),
        ft.ElevatedButton("ورود", on_click=lambda e: page.add(ft.Text("دکمه کلیک شد!")))
    )

ft.app(target=main)
