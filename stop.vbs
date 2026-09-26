' ============================================================
'  MokTradeDesk Stopper  -  stop.vbs
'  Terminates Backend (uvicorn), Frontend (vite/pnpm) and the
'  splash window (mshta). Silent by default when an argument is
'  given (e.g. "stop.vbs quiet").
' ============================================================
Option Explicit

Dim fso, sh, wmi, statusFile, logDir, stopLog, total, quiet

Set fso = CreateObject("Scripting.FileSystemObject")
Set sh  = CreateObject("WScript.Shell")

quiet = (WScript.Arguments.Count > 0)

On Error Resume Next
Set wmi = GetObject("winmgmts:\\.\root\cimv2")
If Err.Number <> 0 Then
    If Not quiet Then MsgBox "WMI is not available on this system.", 16, "MokTradeDesk"
    WScript.Quit 1
End If

statusFile = sh.ExpandEnvironmentStrings("%TEMP%") & "\moktrade_launch_status.txt"
logDir     = fso.BuildPath(fso.GetParentFolderName(WScript.ScriptFullName), "logs")
stopLog    = fso.BuildPath(logDir, "stop.log")

total = 0

' Backend: python -m uvicorn app.main:app
total = total + KillMatch("uvicorn", "moktradedesk")
total = total + KillMatch("uvicorn", "app.main")

' Frontend: pnpm dev / vite
total = total + KillMatch("pnpm", "moktradedesk")
total = total + KillMatch("vite", "moktradedesk")

' Splash window
total = total + KillMatch("mshta", "splash.hta")

' Clear the shared status file
On Error Resume Next
If fso.FileExists(statusFile) Then fso.DeleteFile statusFile, True
On Error Goto 0

' Write a small log
On Error Resume Next
Dim lf
Set lf = fso.CreateTextFile(stopLog, True)
lf.Write "stopped at " & Now & " - processes terminated: " & total
lf.Close
On Error Goto 0

If Not quiet Then
    MsgBox "MokTradeDesk stopped." & vbCrLf & _
           "Processes terminated: " & total, 64, "MokTradeDesk"
End If

WScript.Quit 0

' ============================ helpers ==============================
Function KillMatch(needle1, needle2)
    Dim procs, p, cl, n
    n = 0
    On Error Resume Next
    Set procs = wmi.ExecQuery("SELECT ProcessId, CommandLine FROM Win32_Process")
    For Each p In procs
        cl = LCase(CStr(p.CommandLine & ""))
        If Len(cl) > 0 Then
            If InStr(cl, LCase(needle1)) > 0 Then
                If Len(needle2) = 0 Or InStr(cl, LCase(needle2)) > 0 Then
                    n = n + 1
                    Call KillTree(p.ProcessId)
                End If
            End If
        End If
    Next
    Err.Clear
    On Error Goto 0
    KillMatch = n
End Function

Function KillTree(pid)
    Dim kids, k, objProc, ok
    ok = False
    On Error Resume Next
    Set kids = wmi.ExecQuery("SELECT ProcessId FROM Win32_Process WHERE ParentProcessId=" & pid)
    For Each k In kids
        Call KillTree(k.ProcessId)
    Next
    Set objProc = wmi.Get("Win32_Process.Handle='" & pid & "'")
    objProc.Terminate()
    If Err.Number = 0 Then ok = True
    Err.Clear
    On Error Goto 0
    KillTree = ok
End Function
