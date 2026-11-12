$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    New-Item -ItemType Directory -Path qa -Force | Out-Null
    python -m pytest -q | Tee-Object -FilePath qa\pytest-final.log
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
    python check_modes.py | Tee-Object -FilePath qa\modes-acceptance.log
    if ($LASTEXITCODE -ne 0) { throw 'Mode acceptance failed' }
    python -m pytest test_surface_reference.py -q | Tee-Object -FilePath qa\surface-reference.log
    if ($LASTEXITCODE -ne 0) { throw 'Reference surface tests failed' }
    python check_surface_flow.py | Tee-Object -FilePath qa\surface-flow.log
    if ($LASTEXITCODE -ne 0) { throw 'Surface acceptance failed' }
    python check_button_layout.py | Tee-Object -FilePath qa\button-layout.log
    if ($LASTEXITCODE -ne 0) { throw 'Button layout acceptance failed' }
    python check_login_layout.py | Tee-Object -FilePath qa\login-layout.log
    if ($LASTEXITCODE -ne 0) { throw 'Centered login acceptance failed' }
    python check_registration_menu.py | Tee-Object -FilePath qa\registration-menu.log
    if ($LASTEXITCODE -ne 0) { throw 'Registration/menu acceptance failed' }
    python check_method_windows.py | Tee-Object -FilePath qa\methods-smoke.log
    if ($LASTEXITCODE -ne 0) { throw 'Method window acceptance failed' }
    python -m PyInstaller --noconfirm --clean aviatest_v4_portable.spec
    if ($LASTEXITCODE -ne 0) { throw 'Application build failed' }
    python -m PyInstaller --noconfirm --clean Aviatest-v4.21-MGPU-Setup.spec
    if ($LASTEXITCODE -ne 0) { throw 'Installer build failed' }
    python package_release.py
    if ($LASTEXITCODE -ne 0) { throw 'Source packaging failed' }
    Get-FileHash -Algorithm SHA256 dist\aviatest_v4_21_mgpu_portable.exe,dist\Aviatest-v4.21-MGPU-Setup.exe
}
finally {
    Pop-Location
}
