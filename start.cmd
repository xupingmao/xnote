@set PY_EXE=python

@if exist C:\Python34\Python.exe set PY_EXE=C:\Python34\Python.exe
@if exist C:\Python35\Python.exe set PY_EXE=C:\Python35\Python.exe

@echo Use Python Location: %PY_EXE%
call %PY_EXE% app.py

pause