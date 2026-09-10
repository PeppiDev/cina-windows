' CINA Screen Trigger Invisible para Windows
' Ejecuta el disparador en segundo plano sin mostrar ninguna ventana de consola negra.
Set oShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

strCurDir = fso.GetParentFolderName(WScript.ScriptFullName)

strPythonw = strCurDir & "\venv\Scripts\pythonw.exe"
strMain = strCurDir & "\main.py"

If fso.FileExists(strPythonw) Then
    strCmd = """" & strPythonw & """ """ & strMain & """ --trigger"
Else
    strCmd = "pythonw """ & strMain & """ --trigger"
End If

' 0 = Ventana oculta, False = no esperar a que termine
oShell.Run strCmd, 0, False

