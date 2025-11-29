$StopFlagPath = "C:\Temp\stop_daemon.flag"

# Функция проверки флага остановки
function Test-StopFlag {
    return (Test-Path $StopFlagPath)
}

# В основном цикле добавьте проверку
function Start-Daemon {
    Write-Log "Демон запущен. Ожидание 1:00 для запуска main.exe..."
    
    while ($true) {
        # Проверяем флаг остановки
        if (Test-StopFlag) {
            Write-Log "Обнаружен флаг остановки. Завершение работы..." "INFO"
            Remove-Item $StopFlagPath -Force -ErrorAction SilentlyContinue
            break
        }
        
        $Now = Get-Date
        $CurrentTime = $Now.ToString("HH:mm")

# demoized_main_runner.ps1

param(
    [string]$LogPath = "C:\Logs\main_runner.log",
    [switch]$RunAsService = $false
)

# Функция логирования
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogEntry = "[$Timestamp] [$Level] $Message"
    Write-Host $LogEntry
    if ($RunAsService) {
        Add-Content -Path $LogPath -Value $LogEntry
    }
}

# Функция создания папки для логов
function Initialize-Logging {
    $LogDir = Split-Path $LogPath -Parent
    if (!(Test-Path $LogDir)) {
        New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
    }
}

# Функция запуска main.exe
function Start-MainProgram {
    try {
        Write-Log "Запуск main.exe..."
        
        # Укажите полный путь к вашей программе
        $MainExePath = "main.exe"
        
        if (Test-Path $MainExePath) {
            $Process = Start-Process -FilePath $MainExePath `
                -WindowStyle Hidden `
                -PassThru `
                -Wait
            
            if ($Process.ExitCode -eq 0) {
                Write-Log "main.exe завершен успешно (код: $($Process.ExitCode))"
            } else {
                Write-Log "main.exe завершен с кодом ошибки: $($Process.ExitCode)" "WARNING"
            }
        } else {
            Write-Log "Файл $MainExePath не найден!" "ERROR"
        }
    }
    catch {
        Write-Log "Ошибка при запуске main.exe: $($_.Exception.Message)" "ERROR"
    }
}

# Основной цикл демона
function Start-Daemon {
    Write-Log "Демон запущен. Ожидание 1:00 для запуска main.exe..."
    
    while ($true) {
        $Now = Get-Date
        $CurrentTime = $Now.ToString("HH:mm")
        
        # Проверяем, сейчас ли 1:00
        if ($CurrentTime -eq "01:00") {
            Write-Log "Обнаружено время 1:00, запуск программы..."
            Start-MainProgram
            
            # Ждем 61 секунду чтобы избежать повторного запуска в ту же минуту
            Write-Log "Ожидание 61 секунду перед следующей проверкой..."
            Start-Sleep -Seconds 61
        }
        else {
            # Вычисляем время до следующей 1:00
            $NextRun = $Now.Date.AddDays(1).AddHours(1)
            if ($Now.Hour -lt 1) {
                $NextRun = $Now.Date.AddHours(1)
            }
            
            $SecondsUntilNextRun = [math]::Round(($NextRun - $Now).TotalSeconds)
            
            # Ждем разумное время (1 минута) или до 1:00
            $SleepTime = [math]::Min(60, $SecondsUntilNextRun)
            
            if ($SleepTime -gt 0) {
                Start-Sleep -Seconds $SleepTime
            }
        }
        
        # Периодическое сообщение о работе (раз в час)
        if ($Now.Minute -eq 0) {
            Write-Log "Демон работает. Следующий запуск в 1:00"
        }
    }
}

# Обработка прерывания
function Handle-Interrupt {
    Write-Log "Получен сигнал прерывания. Завершение демона..." "INFO"
    exit 0
}

# Основной код
try {
    # Устанавливаем обработчик прерывания
    $null = Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action {
        Handle-Interrupt
    }

    # Инициализируем логирование
    Initialize-Logging
    
    Write-Log "=== Запуск демона для выполнения main.exe ==="
    Write-Log "Текущая директория: $(Get-Location)"
    Write-Log "Логи будут сохраняться в: $LogPath"
    
    # Запускаем демон
    Start-Daemon
}
catch {
    Write-Log "Критическая ошибка: $($_.Exception.Message)" "ERROR"
    exit 1
}