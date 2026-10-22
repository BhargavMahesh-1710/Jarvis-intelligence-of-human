import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def get_startup_folder() -> Path:
    """Returns the current user's Windows Startup directory."""
    appdata = os.getenv("APPDATA")
    if not appdata:
        raise RuntimeError("Could not find APPDATA environment variable.")
    startup = Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    return startup

def install_startup():
    """Installs the silent launcher into Windows Startup with absolute project paths."""
    startup_dir = get_startup_folder()
    if not startup_dir.exists():
        startup_dir.mkdir(parents=True, exist_ok=True)

    dest_vbs = startup_dir / "StartJarvisBackground.vbs"
    proj_dir = str(PROJECT_ROOT)
    daemon_script = str(PROJECT_ROOT / "backend" / "services" / "background_voice_daemon.py")

    lines = [
        "' MAHI JARVIS — Silent Background Startup Launcher",
        "' Generated automatically by install_startup.py",
        "Dim WshShell",
        'Set WshShell = CreateObject("WScript.Shell")',
        "",
        'Dim currentDir, daemonScript',
        f'currentDir = "{proj_dir}"',
        f'daemonScript = "{daemon_script}"',
        "",
        'WshShell.CurrentDirectory = currentDir',
        'WshShell.Run "powershell -WindowStyle Hidden -NoProfile -ExecutionPolicy Bypass -Command ""Start-Process pythonw -ArgumentList \'" & daemonScript & "\' -WindowStyle Hidden""", 0, False',
        "",
        "Set WshShell = Nothing"
    ]
    vbs_content = "\r\n".join(lines) + "\r\n"

    with open(dest_vbs, "w", encoding="utf-8") as f:
        f.write(vbs_content)

    print("=" * 65)
    print("  [MAHI JARVIS] STARTUP SERVICE INSTALLED SUCCESSFULLY!")
    print(f"  Location: {dest_vbs}")
    print(f"  Project Root: {PROJECT_ROOT}")
    print("  Status: JARVIS will now silently run in the background whenever")
    print("          you boot or log in to your laptop.")
    print("  Usage: Simply say 'Hello Jarvis' or 'Jarvis <command>' on your desktop.")
    print("=" * 65)
    return True

def uninstall_startup():
    """Removes the launcher from Windows Startup."""
    startup_dir = get_startup_folder()
    dest_vbs = startup_dir / "StartJarvisBackground.vbs"
    if dest_vbs.exists():
        dest_vbs.unlink()
        print(f"[MAHI JARVIS] Removed startup launcher from: {dest_vbs}")
        return True
    else:
        print("[MAHI JARVIS] Startup launcher was not found in Startup folder.")
        return False

def check_status():
    """Checks if JARVIS is registered in Windows Startup."""
    startup_dir = get_startup_folder()
    dest_vbs = startup_dir / "StartJarvisBackground.vbs"
    installed = dest_vbs.exists()
    print(f"[MAHI JARVIS] Startup status: {'INSTALLED' if installed else 'NOT INSTALLED'}")
    if installed:
        print(f"  Path: {dest_vbs}")
    return installed

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--uninstall":
        uninstall_startup()
    elif len(sys.argv) > 1 and sys.argv[1] == "--status":
        check_status()
    else:
        install_startup()
