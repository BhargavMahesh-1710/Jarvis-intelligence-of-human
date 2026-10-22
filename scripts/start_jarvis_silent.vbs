' MAHI JARVIS — Silent Background Startup Launcher
' Launches JARVIS Background Voice Daemon silently on Windows login with no console windows.

Dim WshShell, fso, currentDir, pythonwPath, daemonScript

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Get project directory
currentDir = fso.GetParentFolderName(fso.GetParentFolderName(WScript.ScriptFullName))

' Locate pythonw or python
pythonwPath = "pythonw.exe"
daemonScript = currentDir & "\backend\services\background_voice_daemon.py"

' Set working directory to project root
WshShell.CurrentDirectory = currentDir

' Launch completely hidden (0 = vbHide, False = don't wait)
WshShell.Run "powershell -WindowStyle Hidden -NoProfile -ExecutionPolicy Bypass -Command ""Start-Process pythonw -ArgumentList '\""" & daemonScript & "\"""' -WindowStyle Hidden""", 0, False

Set WshShell = Nothing
Set fso = Nothing
