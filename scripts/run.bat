@rem xnote start program
@rem CMD do not support unicode

@title Xnote Server

@rem set color
@rem color [background] foreground
@rem color table
@rem 0 Black 
@rem 1 Blue
@rem 2 Green
@rem 3 Lake Blue
@rem 4 Red
@rem 5 Purple
@rem 6 Yellow
@rem 7 White
@rem 8 Gray
@rem 9 Light blue
@rem A Light green
@rem B Shallow green
@rem C Light red
@rem D Light purple
@rem E Light yellow
@rem F Light white

@rem @color B

@date /T
@time /T

@set PY_EXE=python

@if exist C:\Python34\Python.exe set PY_EXE=C:\Python34\Python.exe
@if exist C:\Python35\Python.exe set PY_EXE=C:\Python35\Python.exe
@if exist C:\Users\%username%\AppData\Local\Programs\Python\Python37\python.exe set PY_EXE=C:\Users\%username%\AppData\Local\Programs\Python\Python37\python.exe

@echo Use Python Location: %PY_EXE%
call %PY_EXE% app.py --webbrowser yes %*

@rem wait to report errors
pause