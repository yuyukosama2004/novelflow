Set-Location -LiteralPath (Resolve-Path "$PSScriptRoot\..")
npm run dev -- --host 127.0.0.1 --port 5173 *> .\vite.log
