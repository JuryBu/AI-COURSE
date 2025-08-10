@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: 强化网络配置
set "PS_CMD=powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; [System.Net.ServicePointManager]::ServerCertificateValidationCallback = { $true }; ""

:: 基础路径设置
set "BASE_DIR=%USERPROFILE%\Desktop\大创 - 副本\课程资源系统v3\课程资源系统v1"

:: 文件校验模块
set MISSING_FILE=
call :CheckFileExist "%BASE_DIR%\app.py"
call :CheckFileExist "%BASE_DIR%\templates\additional_resources.html"
call :CheckFileExist "%BASE_DIR%\templates\base.html"
call :CheckFileExist "%BASE_DIR%\templates\course_content.html"
call :CheckFileExist "%BASE_DIR%\templates\course_description.html"
call :CheckFileExist "%BASE_DIR%\templates\index.html"
call :CheckFileExist "%BASE_DIR%\templates\rename.html"
call :CheckFileExist "%BASE_DIR%\templates\teaching_staff.html"
call :CheckFileExist "%BASE_DIR%\templates\upload.html"
call :CheckFileExist "%BASE_DIR%\READ ME.txt"

if defined MISSING_FILE (
    echo [WARNING] 缺失关键文件：
    echo !MISSING_FILE!
    goto ExternalAccess
) else (
    goto LocalStart
)

:CheckFileExist
if not exist "%~1" (
    set "MISSING_FILE=!MISSING_FILE!    %~1
)
exit /b

:LocalStart
echo [STATUS] 启动本地服务...
start "" /B python "%BASE_DIR%\app.py" >nul 2>&1
timeout /t 10 /nobreak >nul

:: 服务状态检测（带重试机制）
set retry=0
:LocalRetry
%PS_CMD% "$result = try { (Invoke-WebRequest -Uri 'http://127.0.0.1:8000' -UseBasicParsing -DisableKeepAlive -TimeoutSec 8).StatusCode } catch { 503 }; exit $result"
if %errorlevel% equ 200 (
    start "" "http://127.0.0.1:8000"
    exit /b
) else (
    set /a retry+=1
    if !retry! lss 3 (
        echo [RETRY] 本地服务检测重试 (!retry!/3)...
        timeout /t 3 /nobreak >nul
        goto LocalRetry
    )
)

echo [ERROR] 本地服务不可用 (代码: %errorlevel%)
echo 可能原因:
echo 1. Python服务未响应（检查app.py是否正常启动）
echo 2. 端口8000被占用（运行 netstat -ano ^| findstr :8000）
echo 3. 应用程序运行时错误
goto Termination

:ExternalAccess
echo [STATUS] 尝试外部安全连接...
set retry=0
:ExternalRetry
%PS_CMD% "$result = try { (Invoke-WebRequest -Uri 'https://frp-end.com:13010/' -UseBasicParsing -DisableKeepAlive -TimeoutSec 15).StatusCode } catch { if ($_.Exception.Response) { $_.Exception.Response.StatusCode.Value__ } else { 408 } }; exit $result"

if %errorlevel% equ 200 (
    start "" "https://frp-end.com:13010/"
    exit /b
) else (
    set /a retry+=1
    if !retry! lss 2 (
        echo [RETRY] 外部连接重试 (!retry!/2)...
        timeout /t 5 /nobreak >nul
        goto ExternalRetry
    )
)

echo [CRITICAL] 外部访问失败 (代码: %errorlevel%)
call :NetworkDiagnosis

:Termination
echo [NOTICE] 进程将在5秒后终止...
timeout /t 5 /nobreak >nul
exit /b 1

:NetworkDiagnosis
echo 网络诊断报告:
echo ==== 基础连通性测试 ====
powershell -Command "Test-NetConnection frp-end.com -Port 13010 -InformationLevel Detailed | Select-Object ComputerName, RemotePort, TcpTestSucceeded"
echo ------------------------
echo ==== DNS解析验证 ====
nslookup frp-end.com
echo ------------------------
echo ==== 路由追踪 ====
tracert frp-end.com
exit /b