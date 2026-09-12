# ==============================================================================
# SLUGA_agent: Онлайн-деинсталлятор для Windows PowerShell
# Запуск одной командой:
# irm https://raw.githubusercontent.com/johnngoan66101996-cmyk/SLUGA_agent/main/uninstall.ps1 | iex
# ==============================================================================

$ErrorActionPreference = "SilentlyContinue"

Write-Host "========================================================================" -ForegroundColor Red
Write-Host "  🗑️ ДЕИНСТАЛЛЯЦИЯ АВТОНОМНОГО АГЕНТА SLUGA" -ForegroundColor Red
Write-Host "========================================================================" -ForegroundColor Red

# 1. Поиск установленного агента
$candidates = @(
    "C:\SLUGA_agent",
    "$HOME\Desktop\SLUGA_agent",
    "$HOME\SLUGA_agent",
    "$PSScriptRoot"
)

$detectedPath = ""
foreach ($p in $candidates) {
    if ((Test-Path "$p\main.py") -or (Test-Path "$p\wizard.py")) {
        $detectedPath = $p
        break
    }
}

Write-Host "`n📁 Выберите директорию установленного агента для удаления:" -ForegroundColor Yellow
if ($detectedPath) {
    Write-Host "  [1] $detectedPath (Обнаружена установленная версия)" -ForegroundColor Green
} else {
    Write-Host "  [1] C:\SLUGA_agent (Стандартный путь)" -ForegroundColor Green
}
Write-Host "  [2] $HOME\Desktop\SLUGA_agent (Рабочий стол)"
Write-Host "  [3] $HOME\SLUGA_agent (Домашняя папка)"
Write-Host "  [4] Ввести путь вручную"

$choice = Read-Host "`n> Ваш выбор [1-4] (Enter = 1)"

$targetDir = "C:\SLUGA_agent"
if ($detectedPath -and ($choice -eq "" -or $choice -eq "1")) {
    $targetDir = $detectedPath
} elseif ($choice -eq "2") {
    $targetDir = "$HOME\Desktop\SLUGA_agent"
} elseif ($choice -eq "3") {
    $targetDir = "$HOME\SLUGA_agent"
} elseif ($choice -eq "4") {
    $custom = Read-Host "> Введите полный путь к папке агента"
    if ($custom.Trim()) { $targetDir = $custom.Trim() }
}

# Очистка от окружающих кавычек
$targetDir = $targetDir.Trim().Trim('"').Trim("'")

if (-not (Test-Path -LiteralPath $targetDir)) {
    Write-Host "`n⚠️ Папка $targetDir не существует. Возможно, агент уже удален." -ForegroundColor Yellow
    exit 0
}

Write-Host "`n⚠️ ВНИМАНИЕ: Будет полностью удалена папка:" -ForegroundColor Red
Write-Host "   $targetDir" -ForegroundColor White
Write-Host "   (Включая виртуальное окружение .venv, базу данных SQLite и конфигурацию .env)" -ForegroundColor Gray

$confirm = Read-Host "`nПодтвердите полное удаление [y/N]"
if ($confirm -notmatch "^[yYдД]") {
    Write-Host "❌ Деинсталляция отменена пользователем." -ForegroundColor Green
    exit 0
}

# 2. Остановка активных процессов агента
Write-Host "`n🛑 Завершение работающих процессов агента..." -ForegroundColor Yellow
Get-Process python -ErrorAction SilentlyContinue | Where-Object { 
    $_.Path -like "*$targetDir*" -or $_.CommandLine -like "*main.py*" 
} | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

# 3. Удаление папки
Write-Host "🧹 Удаление файлов и зависимостей..." -ForegroundColor Yellow
try {
    Remove-Item -Path $targetDir -Recurse -Force -ErrorAction Stop
    Write-Host "`n✅ Агент SLUGA успешно и полностью удален из $targetDir!" -ForegroundColor Green
} catch {
    # Повторная попытка при блокировке открытых файлов
    Start-Sleep -Seconds 2
    Remove-Item -Path $targetDir -Recurse -Force -ErrorAction SilentlyContinue
    if (-not (Test-Path $targetDir)) {
        Write-Host "`n✅ Агент SLUGA успешно и полностью удален!" -ForegroundColor Green
    } else {
        Write-Host "`n⚠️ Некоторые файлы были заблокированы. Закройте все консоли PowerShell и выполните:" -ForegroundColor Yellow
        Write-Host "   Remove-Item -Path '$targetDir' -Recurse -Force" -ForegroundColor White
    }
}
