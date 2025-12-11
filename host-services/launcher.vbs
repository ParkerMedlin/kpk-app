Set objShell = CreateObject("WScript.Shell")
objShell.Environment("Process")("USERPROFILE") = "C:\Users\pmedlin"
objShell.Environment("Process")("HOME") = "C:\Users\pmedlin"
objShell.CurrentDirectory = "C:\Users\pmedlin\Documents\kpk-app"
objShell.Run """C:/Users/pmedlin/AppData/Local/Programs/Python/Python311/pythonw.exe"" ""C:/Users/pmedlin/Documents/kpk-app/host-services/workers/excel_worker.py""", 0, False