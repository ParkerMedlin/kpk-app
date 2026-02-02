Set s=CreateObject("WScript.Shell")
s.Environment("Process")("USERPROFILE")="C:\Users\pmedlin"
s.Environment("Process")("HOME")="C:\Users\pmedlin"
s.CurrentDirectory="C:\Users\pmedlin\Documents\kpk-app"
s.Run """C:\Users\pmedlin\AppData\Local\Programs\Python\Python311\pythonw.exe"" ""C:\Users\pmedlin\Documents\kpk-app\host-services\watchdogs\looper_health.py""",0,False
