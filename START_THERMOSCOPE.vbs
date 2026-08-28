Set WshShell = CreateObject("WScript.Shell")

projectPath = "C:\Users\Victus\OneDrive\Desktop\Thermoscope"

pythonPath = projectPath & "\.venv\Scripts\python.exe"
uvicornPath = projectPath & "\.venv\Scripts\uvicorn.exe"
streamlitPath = projectPath & "\.venv\Scripts\streamlit.exe"

' Start FastAPI
WshShell.Run "cmd /c cd /d """ & projectPath & """ && """ & uvicornPath & """ src.api:app --port 8000", 0, False

' Start Streamlit directly
WshShell.Run "cmd /c cd /d """ & projectPath & """ && """ & streamlitPath & """ run src\dashboard.py --server.headless true", 0, False

' Check Streamlit every 100 ms
Set http = CreateObject("MSXML2.XMLHTTP")

For i = 1 To 100

    WScript.Sleep 100

    On Error Resume Next

    http.Open "GET", "http://localhost:8501/_stcore/health", False
    http.Send

    If Err.Number = 0 Then
        If http.Status = 200 Then
            Exit For
        End If
    End If

    Err.Clear
    On Error GoTo 0

Next

' Open dashboard
WshShell.Run "http://localhost:8501", 1, False

Set http = Nothing
Set WshShell = Nothing