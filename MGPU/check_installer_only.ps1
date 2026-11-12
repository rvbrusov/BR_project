$ErrorActionPreference = 'Stop'
$qaRoot = Join-Path $PSScriptRoot 'qa'
$qaSetup = Join-Path $PSScriptRoot 'dist\Aviatest-v4.21-MGPU-Setup.exe'
$qaDesktop = [Environment]::GetFolderPath('Desktop')
$qaDesktopLink = Join-Path $qaDesktop 'Авиатест МГПУ.lnk'
$qaBackup = Join-Path $qaRoot 'desktop-shortcut.before.lnk'
$qaHadShortcut = Test-Path -LiteralPath $qaDesktopLink
if ($qaHadShortcut) { Copy-Item -LiteralPath $qaDesktopLink -Destination $qaBackup -Force }
try {
    $qaExisting = Join-Path $qaRoot 'Установка в существующую папку'
    $qaNew = Join-Path $qaRoot 'Новая папка с пробелами\Авиатест'
    New-Item -ItemType Directory -Path $qaExisting -Force | Out-Null
    foreach ($qaDestination in @($qaExisting, $qaNew)) {
        $qaProcess = Start-Process -WindowStyle Hidden -FilePath $qaSetup -ArgumentList @('--silent', '--install-dir', ('"' + $qaDestination + '"')) -Wait -PassThru
        if ($qaProcess.ExitCode -ne 0) { throw "Installer failed: $($qaProcess.ExitCode)" }
        $qaInstalled = Join-Path $qaDestination 'aviatest_v4_21_mgpu_portable.exe'
        if (-not (Test-Path -LiteralPath $qaInstalled)) { throw 'EXE was not installed exactly in destination' }
        if (Test-Path -LiteralPath (Join-Path $qaDestination 'Aviatest')) { throw 'Unexpected nested folder' }
        $qaExpectedHash = (Get-FileHash -LiteralPath (Join-Path $PSScriptRoot 'dist\aviatest_v4_21_mgpu_portable.exe')).Hash
        if ((Get-FileHash -LiteralPath $qaInstalled).Hash -ne $qaExpectedHash) { throw 'Installed executable differs' }
        $qaShell = New-Object -ComObject WScript.Shell
        $qaShortcut = $qaShell.CreateShortcut($qaDesktopLink)
        if ($qaShortcut.TargetPath -ne $qaInstalled) { throw 'Wrong shortcut target' }
        if ($qaShortcut.WorkingDirectory -ne $qaDestination) { throw 'Wrong shortcut working directory' }
        if ($qaShortcut.IconLocation -ne ($qaInstalled + ',0')) { throw 'Wrong shortcut icon' }
        $qaOldData = Join-Path $qaDestination 'aviatest_v4_data'
        New-Item -ItemType Directory -Path $qaOldData -Force | Out-Null
        $qaSentinel = Join-Path $qaOldData 'preserve-on-reinstall.txt'
        Set-Content -LiteralPath $qaSentinel -Value 'Acceptance fixture, not participant data.' -Encoding utf8
        $qaBefore = (Get-FileHash -LiteralPath $qaSentinel).Hash
        $qaProcess = Start-Process -WindowStyle Hidden -FilePath $qaSetup -ArgumentList @('--silent', '--install-dir', ('"' + $qaDestination + '"')) -Wait -PassThru
        if ($qaProcess.ExitCode -ne 0 -or (Get-FileHash -LiteralPath $qaSentinel).Hash -ne $qaBefore) {
            throw 'Reinstallation did not preserve legacy data'
        }
    }
    # Keep a test copy of the real generated shortcut, then restore the user's desktop.
    $qaLaunchLink = Join-Path $qaRoot 'Авиатест МГПУ.lnk'
    Copy-Item -LiteralPath $qaDesktopLink -Destination $qaLaunchLink -Force
    Write-Output 'PASS: frozen installer; existing/new Cyrillic paths with spaces; exact destination; repeat installation; legacy sentinel unchanged; desktop shortcut target and embedded icon.'
}
finally {
    if ($qaHadShortcut) {
        Copy-Item -LiteralPath $qaBackup -Destination $qaDesktopLink -Force
    }
    elseif (Test-Path -LiteralPath $qaDesktopLink) {
        Remove-Item -LiteralPath $qaDesktopLink
    }
}

