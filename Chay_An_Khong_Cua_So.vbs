Set WshShell = CreateObject("WScript.Shell")
currentPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = currentPath
WshShell.Run "python """ & currentPath & "\TrimzAutoJob.py""", 0, False
