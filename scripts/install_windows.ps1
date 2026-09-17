# Install vnpy extras and vnpy_ctp on Windows (prefer PyPI wheel with .dll).
# Never use Mac .framework or Linux .so. Does not start the app.
# Usage (repo root, PowerShell):
#   python -m venv .venv
#   .\scripts\install_windows.ps1
# Optional: set STABX_SIMNOW_CTP to a folder with thost*_se.dll, or place them under vendor\simnow-ctp\windows\
# Optional: $env:STABX_CTP_FROM_SOURCE = "1"  # clone tag 6.7.7.2 and pip install . (needs Git + MSVC)

$ErrorActionPreference = "Stop"

if ($env:OS -ne "Windows_NT") {
    Write-Error "scripts/install_windows.ps1 仅用于 Windows。macOS: ./scripts/install_macos.sh ；Linux: ./scripts/install_linux.sh"
}

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$Py = Join-Path $Root ".venv\Scripts\python.exe"
$Deps = Join-Path $Root ".deps"
$CtpTag = "6.7.7.2"
$VendorWin = Join-Path $Root "vendor\simnow-ctp\windows"

function Test-WindowsDlls {
    param([string]$Dir)
    if (-not $Dir -or -not (Test-Path -LiteralPath $Dir -PathType Container)) {
        return $false
    }
    $md = @(
        (Join-Path $Dir "thostmduserapi_se.dll"),
        (Join-Path $Dir "libthostmduserapi_se.dll")
    ) | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf }
    $td = @(
        (Join-Path $Dir "thosttraderapi_se.dll"),
        (Join-Path $Dir "libthosttraderapi_se.dll")
    ) | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf }
    return ($md.Count -gt 0 -and $td.Count -gt 0)
}

function Resolve-DllSource {
    $candidates = @()
    if ($env:STABX_SIMNOW_CTP) {
        $candidates += $env:STABX_SIMNOW_CTP
    }
    $candidates += $VendorWin
    foreach ($cand in $candidates) {
        if (Test-WindowsDlls $cand) {
            return $cand
        }
    }
    return $null
}

function Copy-WindowsDlls {
    param(
        [Parameter(Mandatory = $true)][string]$Src,
        [Parameter(Mandatory = $true)][string]$ApiDst
    )
    if (-not (Test-Path -LiteralPath $ApiDst -PathType Container)) {
        Write-Error "缺少 vnpy_ctp api 目录：$ApiDst"
    }
    New-Item -ItemType Directory -Force -Path $VendorWin | Out-Null

    $mdSrc = if (Test-Path (Join-Path $Src "thostmduserapi_se.dll")) {
        Join-Path $Src "thostmduserapi_se.dll"
    } else {
        Join-Path $Src "libthostmduserapi_se.dll"
    }
    $tdSrc = if (Test-Path (Join-Path $Src "thosttraderapi_se.dll")) {
        Join-Path $Src "thosttraderapi_se.dll"
    } else {
        Join-Path $Src "libthosttraderapi_se.dll"
    }

    if ($Src -ne $VendorWin) {
        Write-Host "同步 Windows CTP .dll → vendor\simnow-ctp\windows\"
        Copy-Item -Force $mdSrc (Join-Path $VendorWin "thostmduserapi_se.dll")
        Copy-Item -Force $tdSrc (Join-Path $VendorWin "thosttraderapi_se.dll")
        $Src = $VendorWin
        $mdSrc = Join-Path $Src "thostmduserapi_se.dll"
        $tdSrc = Join-Path $Src "thosttraderapi_se.dll"
    }

    Write-Host "覆盖 vnpy_ctp Windows .dll → $ApiDst"
    Copy-Item -Force $mdSrc (Join-Path $ApiDst "thostmduserapi_se.dll")
    Copy-Item -Force $tdSrc (Join-Path $ApiDst "thosttraderapi_se.dll")
}

if (-not (Test-Path -LiteralPath $Py -PathType Leaf)) {
    Write-Host "未找到 $Py ，正在创建虚拟环境 ..."
    python -m venv (Join-Path $Root ".venv")
}
if (-not (Test-Path -LiteralPath $Py -PathType Leaf)) {
    Write-Error "无法创建虚拟环境：$Py。请先安装 Python ≥ 3.10 并勾选 Add to PATH。"
}

$verOk = & $Py -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
if ($LASTEXITCODE -ne 0) {
    Write-Error "需要 Python ≥ 3.10（pyproject.toml）。"
}

& $Py -m pip install -U pip
# Web-only: install leaf deps, then vnpy/project --no-deps (vnpy still declares PySide6).
Write-Host "安装 Web 依赖（不含桌面 Qt / PySide6）..."
& $Py -m pip install `
  "fastapi>=0.115" "uvicorn[standard]>=0.32" "sqlalchemy>=2.0" `
  "pyjwt>=2.9" "bcrypt>=4.2" "cryptography>=43" `
  "python-multipart>=0.0.12" "httpx>=0.27" "orjson>=3.10" "vnpy_sqlite"
& $Py -m pip install `
  "deap>=1.4.2" "loguru>=0.7.3" "nbformat>=5.10.4" `
  "numpy>=2.2.3" "pandas>=2.2.3" "plotly>=6.0.0" `
  "pyzmq>=26.3.0" "tqdm>=4.67.1" "tzlocal>=5.3.1"
& $Py -m pip install "ta-lib>=0.6.3"
if ($LASTEXITCODE -ne 0) {
    Write-Warning "ta-lib 安装失败时可稍后重试（优先 wheel）。"
}
& $Py -m pip install --no-deps "vnpy>=4.0.0,<5"
& $Py -m pip install --no-deps -e $Root
if ($LASTEXITCODE -ne 0) {
    Write-Error "pip install --no-deps -e . 失败"
}
& $Py -m pip uninstall -y pyside6 pyside6-essentials pyside6-addons qdarkstyle shiboken6 pyqtgraph 2>$null

$FromSource = $env:STABX_CTP_FROM_SOURCE -eq "1"
if ($FromSource) {
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        Write-Error "STABX_CTP_FROM_SOURCE=1 需要 Git。或改用默认：直接 pip install vnpy_ctp（PyPI wheel）。"
    }
    New-Item -ItemType Directory -Force -Path $Deps | Out-Null
    $DepsCtp = Join-Path $Deps "vnpy_ctp"
    if (-not (Test-Path (Join-Path $DepsCtp ".git"))) {
        git clone --depth 1 --branch $CtpTag https://github.com/vnpy/vnpy_ctp.git $DepsCtp
    }
    Write-Host "源码安装 vnpy_ctp $CtpTag（需要 Visual Studio C++ 生成工具）..."
    & $Py -m pip install $DepsCtp
    if ($LASTEXITCODE -ne 0) {
        Write-Error "源码安装 vnpy_ctp 失败。可改用默认 PyPI：去掉 STABX_CTP_FROM_SOURCE 后重跑。"
    }
} else {
    Write-Host "安装 vnpy_ctp==$CtpTag（优先 PyPI Windows wheel，自带穿透式 .dll）..."
    & $Py -m pip install "vnpy_ctp==$CtpTag"
    if ($LASTEXITCODE -ne 0) {
        Write-Error @"
pip install vnpy_ctp==$CtpTag 失败。
可尝试：pip install vnpy_ctp
或设置 `$env:STABX_CTP_FROM_SOURCE='1'` 后本机编译（需 MSVC）。
不要拷贝 Mac .framework 或 Linux .so。
"@
    }
}

$ApiDir = & $Py -c "import pathlib, vnpy_ctp; print(pathlib.Path(vnpy_ctp.__file__).resolve().parent / 'api')"
if ($LASTEXITCODE -ne 0 -or -not $ApiDir) {
    Write-Error "无法定位已安装的 vnpy_ctp.api"
}
$ApiDir = $ApiDir.Trim()

$DllSrc = Resolve-DllSource
if ($DllSrc) {
    Copy-WindowsDlls -Src $DllSrc -ApiDst $ApiDir
} else {
    Write-Host "未提供外部 Windows CTP .dll，使用 vnpy_ctp 自带 dll。"
    Write-Host "可选：将 thostmduserapi_se.dll / thosttraderapi_se.dll 放到 $VendorWin 或设置 STABX_SIMNOW_CTP。"
}

Write-Host "依赖已就绪（Windows CTP .dll + vnpy_ctp）。"
Write-Host "原生 Windows 启动见 docs/CTP分平台搭建.md（uvicorn）；或用 WSL2 走 Linux 脚本。"
Write-Host "不要把 Mac .framework / Linux .so 拷到本机。"
