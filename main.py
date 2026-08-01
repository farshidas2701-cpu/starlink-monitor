import flet as ft
import requests
import time
import threading
from ping3 import ping

# تنظیمات اولیه و قابل تغییر توسط ادمین
DEFAULT_CONFIG = {
    "target_ips": ["8.8.8.8", "1.1.1.1", "4.2.2.4"],
    "starlink_keywords": ["SpaceX", "Starlink", "AS14593"],
    "ping_stellar": 60,
    "ping_medium": 120,
    "update_interval": 5,
    "admin_username": "admin",
    "admin_password": "f09931807880F"
}

class NetworkMonitorApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "مانیتورینگ شبکه و استارلینک"
        self.page.rtl = True
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.padding = 20
        self.page.scroll = ft.ScrollMode.AUTO

        self.config = DEFAULT_CONFIG.copy()
        self.is_admin_logged_in = False
        self.is_running = True

        self.public_ip = "در حال دریافت..."
        self.isp_info = "نامشخص"
        self.is_starlink = False
        self.avg_ping = 0

        self.build_ui()

        # اجرای پایش شبکه در نخ (Thread) پس‌زمینه
        self.monitor_thread = threading.Thread(target=self.bg_monitor, daemon=True)
        self.monitor_thread.start()

    def build_ui(self):
        # ساخت تب‌ها (نمای کاربر عادی + ورود/پنل ادمین)
        self.tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(text="📡 وضعیت شبکه", icon=ft.icons.CELLULAR_TOWER, content=self.build_user_view()),
                ft.Tab(text="🔐 پنل مدیریت", icon=ft.icons.ADMIN_PANEL_SETTINGS, content=self.build_admin_view())
            ],
            expand=True
        )
        self.page.add(self.tabs)

    # --- نمای کاربران عادی ---
    def build_user_view(self):
        self.ip_text = ft.Text(self.public_ip, weight=ft.FontWeight.BOLD)
        self.ping_text = ft.Text("-- ms", weight=ft.FontWeight.BOLD)
        self.isp_text = ft.Text(self.isp_info, weight=ft.FontWeight.BOLD)
        
        self.starlink_icon = ft.Icon(ft.icons.CANCEL, color=ft.colors.RED_400)
        self.starlink_status_text = ft.Text("استارلینک: خیر", size=16, weight=ft.FontWeight.BOLD)
        
        self.starlink_badge = ft.Container(
            content=ft.Row([self.starlink_icon, self.starlink_status_text], alignment=ft.MainAxisAlignment.CENTER),
            padding=12,
            border_radius=10,
            bgcolor=ft.colors.SURFACE_VARIANT
        )

        return ft.Column([
            ft.Text("📡 مانیتورینگ هوشمند شبکه", size=22, weight=ft.FontWeight.BOLD, color=ft.colors.CYAN_400),
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.ListTile(
                            leading=ft.Icon(ft.icons.SATELLITE_ALT, size=36, color=ft.colors.CYAN),
                            title=ft.Text("وضعیت اتصال", weight=ft.FontWeight.BOLD),
                            subtitle=ft.Text("پایش زنده کیفیت اینترنت")
                        ),
                        ft.Divider(),
                        ft.Row([ft.Icon(ft.icons.PUBLIC, size=18), ft.Text("آی‌پی عمومی:"), self.ip_text]),
                        ft.Row([ft.Icon(ft.icons.SPEED, size=18), ft.Text("میانگین پینگ:"), self.ping_text]),
                        ft.Row([ft.Icon(ft.icons.BUSINESS, size=18), ft.Text("ارائه‌دهنده (ISP):"), self.isp_text]),
                    ], spacing=10),
                    padding=15
                )
            ),
            self.starlink_badge,
            ft.Text("🔄 اطلاعات به‌طور خودکار بروزرسانی می‌شوند.", size=12, color=ft.colors.GREY_500)
        ], spacing=15)

    # --- نمای پنل ادمین ---
    def build_admin_view(self):
        self.admin_container = ft.Container(content=self.build_login_form())
        return self.admin_container

    def build_login_form(self):
        self.user_input = ft.TextField(label="نام کاربری", value="admin")
        self.pass_input = ft.TextField(label="رمز عبور", password=True, can_reveal_password=True)
        self.login_err = ft.Text("", color=ft.colors.RED_400)

        return ft.Column([
            ft.Text("🔑 ورود به پنل مدیریت", size=20, weight=ft.FontWeight.BOLD, color=ft.colors.CYAN_400),
            self.user_input,
            self.pass_input,
            self.login_err,
            ft.ElevatedButton("ورود", on_click=self.handle_login, icon=ft.icons.LOGIN)
        ], spacing=15)

    def handle_login(self, e):
        if (self.user_input.value == self.config["admin_username"] and 
            self.pass_input.value == self.config["admin_password"]):
            self.is_admin_logged_in = True
            self.admin_container.content = self.build_admin_dashboard()
            self.page.update()
        else:
            self.login_err.value = "نام کاربری یا رمز عبور اشتباه است!"
            self.page.update()

    def build_admin_dashboard(self):
        self.target_ips_input = ft.TextField(label="آی‌پی‌های هدف (با کاما جدا کنید)", value=",".join(self.config["target_ips"]))
        self.keywords_input = ft.TextField(label="کلمات کلیدی استارلینک", value=",".join(self.config["starlink_keywords"]))
        self.stellar_ping_input = ft.TextField(label="سقف پینگ عالی (ms)", value=str(self.config["ping_stellar"]))
        self.medium_ping_input = ft.TextField(label="سقف پینگ متوسط (ms)", value=str(self.config["ping_medium"]))
        self.interval_input = ft.TextField(label="بازه به‌روزرسانی (ثانیه)", value=str(self.config["update_interval"]))
        self.new_pass_input = ft.TextField(label="تغییر رمز عبور ادمین", value=self.config["admin_password"], password=True, can_reveal_password=True)

        return ft.Column([
            ft.Row([
                ft.Text("⚙️ مدیریت اختیارات و تنظیمات", size=18, weight=ft.FontWeight.BOLD, color=ft.colors.GREEN_400),
                ft.IconButton(ft.icons.LOGOUT, on_click=self.handle_logout, tooltip="خروج از حساب")
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            self.target_ips_input,
            self.keywords_input,
            ft.Row([self.stellar_ping_input, self.medium_ping_input]),
            self.interval_input,
            self.new_pass_input,
            ft.ElevatedButton("ذخیره و اعمال تنظیمات", on_click=self.save_settings, icon=ft.icons.SAVE, bgcolor=ft.colors.GREEN_700, color=ft.colors.WHITE)
        ], spacing=12)

    def save_settings(self, e):
        try:
            self.config["target_ips"] = [ip.strip() for ip in self.target_ips_input.value.split(",") if ip.strip()]
            self.config["starlink_keywords"] = [kw.strip() for kw in self.keywords_input.value.split(",") if kw.strip()]
            self.config["ping_stellar"] = int(self.stellar_ping_input.value)
            self.config["ping_medium"] = int(self.medium_ping_input.value)
            self.config["update_interval"] = int(self.interval_input.value)
            self.config["admin_password"] = self.new_pass_input.value
            
            self.page.show_snack_bar(ft.SnackBar(content=ft.Text("تنظیمات با موفقیت ذخیره و اعمال شدند!")))
        except Exception as ex:
            self.page.show_snack_bar(ft.SnackBar(content=ft.Text(f"خطا در ثبت اطلاعات: {ex}")))

    def handle_logout(self, e):
        self.is_admin_logged_in = False
        self.admin_container.content = self.build_login_form()
        self.page.update()

    # --- فرآیند پایش شبکه ---
    def fetch_network_info(self):
        try:
            res = requests.get("http://ip-api.com/json/", timeout=5).json()
            if res.get("status") == "success":
                self.public_ip = res.get("query", "نامشخص")
                org = res.get("org", "")
                isp = res.get("isp", "")
                as_name = res.get("as", "")
                self.isp_info = f"{isp} ({org})"

                full_str = f"{org} {isp} {as_name}"
                self.is_starlink = any(kw.lower() in full_str.lower() for kw in self.config["starlink_keywords"])
        except Exception:
            self.public_ip = "خطا در دریافت"
            self.isp_info = "نامشخص"

    def measure_ping(self):
        pings = []
        for ip in self.config["target_ips"]:
            p = ping(ip, timeout=1.5)
            if p is not None:
                pings.append(p * 1000)
        
        if pings:
            self.avg_ping = sum(pings) / len(pings)
        else:
            self.avg_ping = None

    def bg_monitor(self):
        while self.is_running:
            self.fetch_network_info()
            self.measure_ping()

            # update ui
            self.ip_text.value = self.public_ip
            self.isp_text.value = self.isp_info

            if self.avg_ping:
                self.ping_text.value = f"{self.avg_ping:.1f} ms"
                if self.avg_ping < self.config["ping_stellar"]:
                    self.ping_text.color = ft.colors.GREEN_400
                elif self.avg_ping < self.config["ping_medium"]:
                    self.ping_text.color = ft.colors.BLUE_400
                else:
                    self.ping_text.color = ft.colors.RED_400
            else:
                self.ping_text.value = "قطع اتصال"
                self.ping_text.color = ft.colors.RED_400

            if self.is_starlink:
                self.starlink_icon.name = ft.icons.CHECK_CIRCLE
                self.starlink_icon.color = ft.colors.GREEN_400
                self.starlink_status_text.value = "استارلینک: بله (شناسایی شد)"
                self.starlink_badge.bgcolor = ft.colors.GREEN_900
            else:
                self.starlink_icon.name = ft.icons.CANCEL
                self.starlink_icon.color = ft.colors.RED_400
                self.starlink_status_text.value = "استارلینک: خیر (اینترنت معمولی)"
                self.starlink_badge.bgcolor = ft.colors.SURFACE_VARIANT

            self.page.update()
            time.sleep(self.config["update_interval"])

def main(page: ft.Page):
    NetworkMonitorApp(page)

ft.app(target=main)
