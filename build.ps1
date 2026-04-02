# ArxivCat build script
# Tkinter only.

$ErrorActionPreference = 'Stop'
$ProjectRoot = $PSScriptRoot
$EntryPoint  = "$ProjectRoot\main.py"
$ExeName     = "ArxivCat"

Write-Host "==> building $ExeName.exe" -ForegroundColor Cyan

if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Host "    installing pyinstaller..." -ForegroundColor Yellow
    pip install pyinstaller
}

& pyinstaller `
    --noconfirm `
    --onefile `
    --windowed `
    --name $ExeName `
    '--add-data' "arxivcat;arxivcat" `
    --hidden-import arxivcat `
    --hidden-import arxivcat.core `
    --hidden-import arxivcat.presenter `
    --hidden-import arxivcat.ui `
    --hidden-import arxivcat.ui.base `
    --hidden-import arxivcat.ui.tkinter_ui `
    --collect-all requests `
    --hidden-import tkinter `
    --hidden-import tkinter.ttk `
    $EntryPoint

if ($LASTEXITCODE -eq 0) {
    $exe = "$ProjectRoot\dist\$ExeName.exe"
    $sizeMB = [math]::Round((Get-Item $exe).Length / 1MB, 1)
    Write-Host "`n==> done" -ForegroundColor Green
    Write-Host "    output: $exe" -ForegroundColor Green
    Write-Host "    size:   $sizeMB MB" -ForegroundColor Green
} else {
    Write-Host "`n==> build failed" -ForegroundColor Red
    exit 1
}
