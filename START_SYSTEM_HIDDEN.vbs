' បើកប្រព័ន្ធ SM Inventory ពេញលេញ (Web + Cloudflare Tunnel + Telegram Bot) ដោយមិនបង្ហាញផ្ទាំង CMD
' បិទប្រព័ន្ធ៖ ចុច STOP_SYSTEM.bat
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh  = CreateObject("WScript.Shell")
base = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = base
py = base & "\.venv\Scripts\pythonw.exe"
If Not fso.FileExists(py) Then py = "pythonw.exe"
sh.Environment("PROCESS")("SM_HIDDEN") = "1"
sh.Run """" & py & """ """ & base & "\run_system.py""", 0, False
