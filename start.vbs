' ============================================================
'  MokTradeDesk Launcher  -  start.vbs
'  Silent launcher (no CMD window) with HTA splash + progress.
'  ASCII-only on purpose: all user text lives in splash.hta (UTF-8).
' ============================================================
Option Explicit

Dim fso, sh, baseDir, backendDir, frontendDir
Dim pythonExe, alembicExe, logDir, statusFile, splashFile
Dim backendLog, frontendLog, migrationLog

Set fso = CreateObject("Scripting.FileSystemObject")
Set sh  = CreateObject("WScript.Shell")

baseDir     = fso.GetParentFolderName(WScript.ScriptFullName)
backendDir  = fso.BuildPath(baseDir, "backend")
frontendDir = fso.BuildPath(baseDir, "frontend")
pythonExe   = fso.BuildPath(backendDir, "venv\Scripts\python.exe")
alembicExe  = fso.BuildPath(backendDir, "venv\Scripts\alembic.exe")
logDir      = fso.BuildPath(baseDir, "logs")
statusFile  = sh.ExpandEnvironmentStrings("%TEMP%") & "\moktrade_launch_status.txt"
splashFile  = fso.BuildPath(baseDir, "splash.hta")
backendLog  = fso.BuildPath(logDir, "backend.log")
frontendLog = fso.BuildPath(logDir, "frontend.log")
migrationLog = fso.BuildPath(logDir, "migration.log")

Dim BACKEND_URLS, FRONTEND_URLS
BACKEND_URLS  = "http://127.0.0.1:8000/docs,http://localhost:8000/docs"
FRONTEND_URLS = "http://localhost:5173,http://127.0.0.1:5173,http://[::1]:5173"

If Not fso.FolderExists(logDir) Then
    On Error Resume Next
    fso.CreateFolder logDir
    On Error Goto 0
End If

' --- sanity check -------------------------------------------------
If Not fso.FileExists(pythonExe) Then
    Call SetStatus(0, "error_backend")
    MsgBox "Backend virtualenv not found:" & vbCrLf & pythonExe, _
           16, "MokTradeDesk"
    WScript.Quit 1
End If

' --- already running? just open the browser ------------------------
If IsAnyUp(BACKEND_URLS) And IsAnyUp(FRONTEND_URLS) Then
    Call SetStatus(100, "done")
    Call OpenBrowser("http://localhost:5173")
    WScript.Quit 0
End If

' --- 1. splash -----------------------------------------------------
Call SetStatus(2, "init")
On Error Resume Next
sh.Run "mshta.exe """ & splashFile & """", 1, False
On Error Goto 0
WScript.Sleep 400

' --- 2. migrations -------------------------------------------------
Call SetStatus(8, "migrate")
If fso.FileExists(alembicExe) Then
    Call RunHidden("cmd /c cd /d """ & backendDir & """ && """ & alembicExe & """ upgrade head >> """ & migrationLog & """ 2>&1", True)
End If
Call SetStatus(20, "migrate_done")

' --- 3. backend ----------------------------------------------------
Call SetStatus(30, "backend")
Call RunHidden("cmd /c cd /d """ & backendDir & """ && """ & pythonExe & """ -m uvicorn app.main:app --reload >> """ & backendLog & """ 2>&1", False)

Call SetStatus(45, "backend_wait")
If WaitForAny(BACKEND_URLS, 60) Then
    Call SetStatus(58, "backend_ready")
Else
    Call SetStatus(58, "error_backend")
End If

' --- 4. frontend ---------------------------------------------------
Call SetStatus(68, "frontend")
Call RunHidden("cmd /c cd /d """ & frontendDir & """ && pnpm dev >> """ & frontendLog & """ 2>&1", False)

Call SetStatus(80, "frontend_wait")
If WaitForAny(FRONTEND_URLS, 60) Then
    Call SetStatus(92, "frontend_ready")
Else
    Call SetStatus(92, "error_frontend")
End If

' --- 5. browser ----------------------------------------------------
Call SetStatus(97, "browser")
Call OpenBrowser("http://localhost:5173")
Call SetStatus(100, "done")

WScript.Sleep 1500

' ============================ helpers ==============================
Sub SetStatus(pct, code)
    Dim f
    On Error Resume Next
    Set f = fso.CreateTextFile(statusFile, True)
    If Not f Is Nothing Then
        f.Write pct & "|" & code
        f.Close
    End If
    On Error Goto 0
End Sub

Sub RunHidden(cmd, waitFor)
    On Error Resume Next
    sh.Run cmd, 0, waitFor
    On Error Goto 0
End Sub

Sub OpenBrowser(url)
    On Error Resume Next
    sh.Run "cmd /c start """" """ & url & """", 0, False
    On Error Goto 0
End Sub

Function IsUp(url)
    Dim http, ok
    ok = False
    On Error Resume Next
    Set http = CreateObject("MSXML2.ServerXMLHTTP.6.0")
    If Err.Number <> 0 Then
        Err.Clear
        Set http = CreateObject("MSXML2.XMLHTTP")
    End If
    http.setTimeouts 800, 800, 1200, 1200
    http.open "GET", url, False
    http.send
    If Err.Number = 0 Then
        If http.status >= 200 And http.status < 500 Then ok = True
    End If
    Err.Clear
    On Error Goto 0
    IsUp = ok
End Function

Function IsAnyUp(urlList)
    Dim arr, i
    IsAnyUp = False
    arr = Split(urlList, ",")
    For i = 0 To UBound(arr)
        If IsUp(Trim(arr(i))) Then
            IsAnyUp = True
            Exit Function
        End If
    Next
End Function

Function WaitForAny(urlList, seconds)
    Dim i
    WaitForAny = False
    For i = 1 To seconds * 2
        If IsAnyUp(urlList) Then
            WaitForAny = True
            Exit Function
        End If
        WScript.Sleep 500
    Next
End Function
