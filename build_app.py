import os
import sys
import platform
import subprocess
import shutil


def is_windows():
    return platform.system() == "Windows"


def is_macos():
    return platform.system() == "Darwin"


def is_linux():
    return platform.system() == "Linux"


def run_command(command):
    """Run a command and return its output"""
    print(f"Executing: {command}")
    try:
        # On Windows, we need to handle paths differently
        if is_windows():
            # Use subprocess with shell=False and args as list for better path handling
            if isinstance(command, list):
                args = command
            else:
                args = command.split()

            result = subprocess.run(args, shell=False, capture_output=True, text=True)
        else:
            # On Unix systems, shell=True works fine
            result = subprocess.run(command, shell=True, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"Command failed with exit code {result.returncode}")
            print(f"Error: {result.stderr}")
            return False
        return result.stdout.strip()
    except Exception as e:
        print(f"Error executing command: {e}")
        return False


def install_dependencies():
    """Install required dependencies for the build"""
    print("Installing required dependencies...")

    python_exe = sys.executable

    # Common dependencies
    if not run_command([python_exe, "-m", "pip", "install", "--upgrade", "pip"]):
        print("Warning: Failed to upgrade pip, continuing anyway...")

    run_command([python_exe, "-m", "pip", "install", "PyQt5", "pynput"])
    run_command([python_exe, "-m", "pip", "install", "pyinstaller"])

    if is_windows():
        # Windows-specific dependencies for shortcuts
        run_command([python_exe, "-m", "pip", "install", "pywin32", "winshell"])

    print("Dependencies installed successfully.")


def create_icon():
    """Create a simple icon if one doesn't exist"""
    icon_path = get_icon_path()

    if os.path.exists(icon_path):
        print(f"Using existing icon: {icon_path}")
        return

    print("Creating default icon...")
    try:
        run_command([sys.executable, "-m", "pip", "install", "pillow"])

        icon_script = """
from PIL import Image, ImageDraw

# Create a new image with a transparent background
img = Image.new('RGBA', (256, 256), color=(255, 255, 255, 0))

# Get a drawing context
draw = ImageDraw.Draw(img)

# Draw a yellow highlighter rectangle
draw.rectangle((64, 96, 192, 160), fill=(255, 255, 0, 180))

# Save files
if '{system}' == 'Darwin':
    # For macOS we need PNG
    img.save('{icon_path}')
else:
    # For Windows and Linux we use ICO
    img.save('{icon_path}', sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
"""

        icon_script = icon_script.format(
            system=platform.system(),
            icon_path=icon_path
        )

        # Save the icon creation script as a temporary file
        with open("temp_icon_script.py", "w") as f:
            f.write(icon_script)

        # Run the script
        run_command([sys.executable, "temp_icon_script.py"])

        # Clean up
        if os.path.exists("temp_icon_script.py"):
            os.remove("temp_icon_script.py")

        print(f"Icon created: {icon_path}")
    except Exception as e:
        print(f"Failed to create icon: {e}")
        print("Continuing without an icon...")


def get_icon_path():
    """Return the appropriate icon path based on the platform"""
    if is_macos():
        return "highlighter.png"
    else:  # Windows or Linux
        return "highlighter.ico"


def build_executable():
    """Build the executable for the current platform"""
    print(f"Building executable for {platform.system()}...")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_script = os.path.join(script_dir, "highlighter.py")
    icon_path = os.path.join(script_dir, get_icon_path())

    python_exe = sys.executable

    # Base PyInstaller command
    cmd = [
        python_exe,
        "-m",
        "PyInstaller",
        main_script,
        "--name=LineHighlighter",
        "--onefile",
        "--windowed",
        "--clean",
    ]

    # Add icon if it exists
    if os.path.exists(icon_path):
        cmd.append(f"--icon={icon_path}")

    # Platform-specific options
    if is_windows():
        cmd.append(f"--add-data={get_icon_path()};.")
    elif is_macos():
        cmd.append(f"--add-data=highlighter.png:.")
        cmd.append("--target-architecture=x86_64")  # Ensure compatibility
    elif is_linux():
        cmd.append(f"--add-data=highlighter.ico:.")

    # Add hidden imports
    cmd.append("--hidden-import=PyQt5")
    cmd.append("--hidden-import=pynput")

    # Run the PyInstaller command
    success = run_command(cmd)

    # Check if build was successful
    if is_windows():
        exe_path = os.path.join(script_dir, "dist", "LineHighlighter.exe")
    elif is_macos():
        exe_path = os.path.join(script_dir, "dist", "LineHighlighter.app", "Contents", "MacOS", "LineHighlighter")
    else:  # Linux
        exe_path = os.path.join(script_dir, "dist", "LineHighlighter")

    if os.path.exists(exe_path):
        print(f"Build successful! Executable created at: {exe_path}")
        return exe_path
    else:
        print("Build failed! Executable not found.")
        return None


def create_desktop_shortcut(exe_path):
    """Create a desktop shortcut based on the platform"""
    if not exe_path or not os.path.exists(exe_path):
        print("Cannot create shortcut: executable not found")
        return

    print("Creating desktop shortcut...")

    try:
        if is_windows():
            # Windows shortcut - create directly with Python
            shortcut_script = """
import os
import sys
import winshell
from win32com.client import Dispatch

desktop = winshell.desktop()
path = os.path.join(desktop, "Line Highlighter.lnk")

shell = Dispatch('WScript.Shell')
shortcut = shell.CreateShortCut(path)
shortcut.Targetpath = r'{exe_path}'
shortcut.WorkingDirectory = r'{work_dir}'
shortcut.IconLocation = r'{icon_loc}'
shortcut.save()

print(f"Shortcut created at: {{path}}")
"""
            shortcut_script = shortcut_script.format(
                exe_path=exe_path,
                work_dir=os.path.dirname(exe_path),
                icon_loc=exe_path
            )

            with open("create_shortcut.py", "w") as f:
                f.write(shortcut_script)

            run_command([sys.executable, "create_shortcut.py"])

            # Clean up
            if os.path.exists("create_shortcut.py"):
                os.remove("create_shortcut.py")

        elif is_macos():
            # macOS .app bundle should already be created by PyInstaller
            desktop_path = os.path.expanduser("~/Desktop")
            app_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(exe_path))), "LineHighlighter.app")

            if os.path.exists(app_path):
                shortcut_path = os.path.join(desktop_path, "LineHighlighter.app")
                if os.path.exists(shortcut_path):
                    shutil.rmtree(shortcut_path)
                shutil.copytree(app_path, shortcut_path)
                print(f"Application copied to desktop: {shortcut_path}")
            else:
                print("macOS app bundle not found")

        elif is_linux():
            # Linux .desktop file
            desktop_path = os.path.expanduser("~/Desktop")
            desktop_file = os.path.join(desktop_path, "LineHighlighter.desktop")

            desktop_content = """[Desktop Entry]
Type=Application
Name=Line Highlighter
Exec={exe_path}
Icon={icon_path}
Terminal=false
Categories=Utility;
""".format(exe_path=exe_path, icon_path=os.path.join(os.path.dirname(exe_path), "highlighter.ico"))

            with open(desktop_file, "w") as f:
                f.write(desktop_content)

            # Make it executable
            os.chmod(desktop_file, 0o755)
            print(f"Desktop shortcut created at: {desktop_file}")

    except Exception as e:
        print(f"Failed to create desktop shortcut: {e}")
        print("You can manually create a shortcut to the executable.")


def main():
    print("======================================")
    print("LineHighlighter Cross-Platform Builder")
    print("======================================")
    print(f"Platform: {platform.system()}")
    print(f"Python: {platform.python_version()}")
    print(f"Python executable: {sys.executable}")
    print("--------------------------------------")

    # Install required dependencies
    install_dependencies()

    # Create icon if needed
    create_icon()

    # Build the executable
    exe_path = build_executable()

    # Create desktop shortcut
    if exe_path:
        create_desktop_shortcut(exe_path)

    print("======================================")
    print("Build process completed!")
    print("======================================")


if __name__ == "__main__":
    main()