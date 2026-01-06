Set s=CreateObject("WScript.Shell")
s.Environment("Process")("USERPROFILE")="C:\Users\jdavis"
s.Environment("Process")("HOME")="C:\Users\jdavis"
s.CurrentDirectory="C:/Users/jdavis/Documents/kpk-app"
s.Run """C:/Users/jdavis/Documents/kpk-app/../AppData/Local/Programs/Python/Python311/pythonw.exe"" ""C:/Users/jdavis/Documents/kpk-app/host-services/workers/data_sync.py""",0,False
