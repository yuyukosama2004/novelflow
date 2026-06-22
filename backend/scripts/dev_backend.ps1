Set-Location -LiteralPath (Resolve-Path "$PSScriptRoot\..")
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 *> .\uvicorn.log
