# ArxivCat build script
# Tkinter only.

$ErrorActionPreference = 'Stop'
$ProjectRoot = $PSScriptRoot
$EntryPoint  = "$ProjectRoot\main.py"
$ExeName     = "ArxivCat"
$Version     = "v0.3.0"
$ReleaseName = "$ExeName-$Version-win64"
$PythonExe   = "D:\anaconda3\envs\arxivcat\python.exe"

Write-Host "==> building $ExeName.exe" -ForegroundColor Cyan
Write-Host "    python: $PythonExe" -ForegroundColor DarkGray

if (-not (Test-Path $PythonExe)) {
    Write-Host "`n==> build failed" -ForegroundColor Red
    Write-Host "    missing python executable: $PythonExe" -ForegroundColor Red
    exit 1
}

try {
    & $PythonExe -m PyInstaller --version | Out-Null
} catch {
    Write-Host "    installing pyinstaller..." -ForegroundColor Yellow
    & $PythonExe -m pip install pyinstaller
}

& $PythonExe -m PyInstaller `
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
    --collect-all google `
    --hidden-import tkinter `
    --hidden-import tkinter.ttk `
    $EntryPoint

if ($LASTEXITCODE -eq 0) {
    $exe = "$ProjectRoot\dist\$ExeName.exe"
    $zip = "$ProjectRoot\dist\$ReleaseName.zip"
    if (Test-Path $zip) {
        Remove-Item $zip -Force
    }
    Compress-Archive -Path $exe -DestinationPath $zip
    $sizeMB = [math]::Round((Get-Item $exe).Length / 1MB, 1)
    Write-Host "`n==> done" -ForegroundColor Green
    Write-Host "    output: $exe" -ForegroundColor Green
    Write-Host "    zip:    $zip" -ForegroundColor Green
    Write-Host "    size:   $sizeMB MB" -ForegroundColor Green
} else {
    Write-Host "`n==> build failed" -ForegroundColor Red
    exit 1
}
