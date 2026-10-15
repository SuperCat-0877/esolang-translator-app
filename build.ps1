# build.ps1
# Build EsolangTranslator.exe - auto-detect existing folders.

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== EsolangTranslator - build ===" -ForegroundColor Cyan

if (-not (Test-Path "Main.py")) {
    Write-Host "[ERR] Main.py not found" -ForegroundColor Red
    exit 1
}

$addDataCandidates = @(
    @{ src = "core";                 dst = "core" },
    @{ src = "langs";                dst = "langs" },
    @{ src = "ui";                   dst = "ui" },
    @{ src = "tools";                dst = "tools" },
    @{ src = "services";             dst = "services" },
    @{ src = "rivulet";              dst = "rivulet" },
    @{ src = "plugins";              dst = "plugins" },
    @{ src = "langs_disabled";       dst = "langs_disabled" },
    @{ src = "Rivulet_examples";     dst = "Rivulet_examples" },
    @{ src = "config.json";          dst = "." },
    @{ src = "rivulet_library.json"; dst = "." }
)

$collectData = @()
foreach ($pkg in @("sv_ttk", "customtkinter")) {
    $ok = $false
    try { python -c "import $pkg" 2>$null | Out-Null; $ok = $true } catch { }
    if ($ok) {
        $collectData += "--collect-data"
        $collectData += $pkg
        Write-Host ("  [OK] package found: " + $pkg) -ForegroundColor Green
    } else {
        Write-Host ("  [--] skip (not installed): " + $pkg) -ForegroundColor DarkGray
    }
}

$pyArgs = @(
    "-m", "PyInstaller",
    "--onefile",
    "--windowed",
    "--name", "EsolangTranslator",
    "--noconfirm",
    "--clean"
)
foreach ($cd in $collectData) { $pyArgs += $cd }

$hidden = @(
    "PIL._tkinter_finder", "cairosvg",
    "rivulet", "rivulet.riv_interpreter", "rivulet.riv_parser",
    "rivulet.riv_python_transpiler", "rivulet.riv_svg_generator",
    "rivulet.riv_themes", "rivulet.riv_exceptions"
)
foreach ($h in $hidden) { $pyArgs += @("--hidden-import", $h) }

if (Test-Path "rivulet") {
    $pyArgs += @("--collect-submodules", "rivulet")
}

Write-Host ""
Write-Host "=== Resources ===" -ForegroundColor Cyan
foreach ($item in $addDataCandidates) {
    if (Test-Path $item.src) {
        $pyArgs += @("--add-data", "$($item.src);$($item.dst)")
        Write-Host ("  [OK] " + $item.src + " -> " + $item.dst) -ForegroundColor Green
    } else {
        Write-Host ("  [--] missing: " + $item.src) -ForegroundColor DarkGray
    }
}

$pyArgs += "Main.py"

Write-Host ""
Write-Host "=== Command ===" -ForegroundColor Cyan
Write-Host ("python " + ($pyArgs -join " ")) -ForegroundColor DarkGray
Write-Host ""

& python @pyArgs

if ($LASTEXITCODE -ne 0) {
    Write-Host ("[ERR] build failed with code " + $LASTEXITCODE) -ForegroundColor Red
    exit $LASTEXITCODE
}
Write-Host "[OK] done: dist\EsolangTranslator.exe" -ForegroundColor Green