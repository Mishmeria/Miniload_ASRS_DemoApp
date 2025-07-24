import flet as ft
from src.state import state

def create_login_view(page):
    # Define username and password for simple authentication
    username_value = "admin"
    password_value = "1234"
    
    # Store these credentials in state for access in main.py
    state['valid_username'] = username_value
    state['valid_password'] = password_value
    
    def login_clicked(e):
        if username.value == state['valid_username'] and password.value == state['valid_password']:
            # Set login state to True and navigate to main content
            state['logged_in'] = True
            page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Welcome, {username.value}!"),
                bgcolor=ft.Colors.GREEN_500
            )
            page.snack_bar.open = True
            # Clear the login form
            username.value = ""
            password.value = ""
            # Update the page to show main content
            page.go("/main")
        else:
            page.snack_bar = ft.SnackBar(
                content=ft.Text("Invalid username or password!"),
                bgcolor=ft.Colors.RED_500
            )
            page.snack_bar.open = True
        page.update()
    
    # Create login form controls
    username = ft.TextField(
        label="Username",
        autofocus=True,
        prefix_icon=ft.Icons.PERSON,
        width=250
    )
    
    password = ft.TextField(
        label="Password",
        password=True,
        can_reveal_password=True,
        prefix_icon=ft.Icons.LOCK_OUTLINE,
        width=250
    )
    
    login_button = ft.ElevatedButton(
        "Login",
        icon=ft.Icons.LOGIN,
        width=250,
        on_click=login_clicked
    )
    
    # Create a simple login box
    login_box = ft.Container(
        content=ft.Column(
            [
                ft.Text("ASRS Database Login", size=20, weight=ft.FontWeight.BOLD),
                username,
                password,
                login_button,
                ft.Text(
                    f"Demo: {username_value}/{password_value}",
                    size=12,
                    color=ft.Colors.GREY_600
                )
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20,
            tight=True
        ),
        padding=30,
        bgcolor=ft.Colors.WHITE,
        border_radius=10,
        width=300,
        shadow=ft.BoxShadow(
            spread_radius=1,
            blur_radius=15,
            color=ft.Colors.BLACK12,
            offset=ft.Offset(0, 0)
        )
    )
    
    # Center the login box on the screen
    return ft.Container(
        content=login_box,
        alignment=ft.alignment.center,
        expand=True,
        bgcolor=ft.Colors.BLUE_GREY_50
    )