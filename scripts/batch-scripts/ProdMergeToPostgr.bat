@echo off
set LOGFILE=batch.log
call :LOG > %LOGFILE%
exit /B
:LOG
"C:\Users\Blendverse\AppData\Local\Programs\Python\Python310\python.exe" "C:\users\Blendverse\Documents\kpk-app\scripts\direct-db-table-scripts\ProdMergetoPostgres.py"