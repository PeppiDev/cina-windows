' Generador de Accesos Directos de Windows para CINA AI Assistant
Set oWS = WScript.CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

strCurDir = fso.GetParentFolderName(WScript.ScriptFullName)
sDesktop = oWS.SpecialFolders("Desktop")

' 1. Acceso directo de la aplicacion principal (GUI)
sMainLink = sDesktop & "\CINA AI Assistant.lnk"
Set oLinkMain = oWS.CreateShortcut(sMainLink)
oLinkMain.TargetPath = strCurDir & "\run.bat"
oLinkMain.WorkingDirectory = strCurDir
oLinkMain.Description = "CINA - Asistente de Pantalla y Audio con Google Gemini"
oLinkMain.WindowStyle = 1
oLinkMain.Save

' 2. Acceso directo del disparador silencioso con atajo global nativo de Windows (Ctrl+Alt+S)
sTriggerLink = sDesktop & "\CINA Trigger.lnk"
Set oLinkTrigger = oWS.CreateShortcut(sTriggerLink)
oLinkTrigger.TargetPath = "wscript.exe"
oLinkTrigger.Arguments = """" & strCurDir & "\cina-trigger.vbs"""
oLinkTrigger.WorkingDirectory = strCurDir
oLinkTrigger.Hotkey = "Ctrl+Alt+S"
oLinkTrigger.Description = "Disparador silencioso invisible de CINA (Ctrl+Alt+S)"
oLinkTrigger.WindowStyle = 7 ' Minimizada / Inactiva
oLinkTrigger.Save

WScript.Echo "Accesos directos creados exitosamente en el Escritorio:"
WScript.Echo " - " & sMainLink
WScript.Echo " - " & sTriggerLink & " [Atajo: Ctrl+Alt+S]"

