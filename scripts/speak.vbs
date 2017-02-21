'Dim userinput
'userinput = InputBox("Hi")
'只支持UTF-8
Set api = Wscript.CreateObject("SAPI.SpVoice")

set objArgs = Wscript.Arguments
for x = 0 to objArgs.Count - 1 
  api.speak objArgs(x)
next