@echo off
:: Tu dong xin quyen Administrator neu chua co
>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
if '%errorlevel%' NEQ '0' (
    echo Dang yeu cau quyen Administrator...
    powershell -Command "Start-Process cmd.exe -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /B
)

:: Da co quyen Administrator
title Cap quyen Full Control cho Workspace D:\workplace_make_firm
echo ========================================================
echo DANG CAP FULL QUYEN CHO HERMES / SANDBOX / EVERYONE
echo ========================================================
echo.
echo [1/3] Lay quyen so huu thu muc D:\workplace_make_firm...
takeown /F "D:\workplace_make_firm" /R /D Y

echo.
echo [2/3] Cap quyen Full Control cho Everyone, Users, CodexSandbox...
icacls "D:\workplace_make_firm" /grant Everyone:(OI)(CI)F /grant "BUILTIN\Users":(OI)(CI)F /grant "ANH-KHOA\CodexSandboxUsers":(OI)(CI)F /grant "ANH-KHOA\CodexSandboxOffline":(OI)(CI)F /grant "ANH-KHOA\CodexSandboxOnline":(OI)(CI)F /T /C /Q

echo.
echo [3/3] Kiem tra ket qua...
echo ========================================================
echo HOAN TAT!
echo Da cap Full Control vao:
echo   - D:\workplace_make_firm
echo   - D:\workplace_make_firm\review_firm_china
echo   - D:\workplace_make_firm\review_firm_china\ai-video-review
echo   va tat ca cac thu muc con!
echo ========================================================
echo.
pause
