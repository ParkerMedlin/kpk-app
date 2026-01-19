Set s=CreateObject("WScript.Shell")
s.Environment("Process")("USERPROFILE")="C:\Users\pmedlin"
s.Environment("Process")("HOME")="C:\Users\pmedlin"
s.CurrentDirectory="C:\Users\pmedlin\Documents\kpk-app"
<<<<<<< HEAD
s.Run """C:\Users\pmedlin\AppData\Local\Programs\Python\Python311\pythonw.exe"" ""C:\Users\pmedlin\Documents\kpk-app\host-services\watchdogs\tank_leak_detector.py""",0,False
=======
s.Run """C:\Users\pmedlin\AppData\Local\Programs\Python\Python311\pythonw.exe"" ""C:\Users\pmedlin\Documents\kpk-app\host-services\workers\data_sync.py""",0,False
>>>>>>> 2899fe1e7267576c6d2c735869637197f30de608
