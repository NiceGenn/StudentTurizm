@echo off
chcp 65001 >nul
title Туристический портал Благовещенского округа
cd /d "%~dp0"

echo.
echo  ==============================================================
echo   Туристический портал Благовещенского муниципального округа
echo  ==============================================================
echo.

rem ---------------------------------------------------------------
rem  1. Ищем Python
rem ---------------------------------------------------------------
set "PYCMD="
py -3 -c "" >nul 2>&1
if %errorlevel%==0 set "PYCMD=py -3"
if defined PYCMD goto HAVE_PYTHON

python -c "" >nul 2>&1
if %errorlevel%==0 set "PYCMD=python"
if defined PYCMD goto HAVE_PYTHON

goto NO_PYTHON

:HAVE_PYTHON

rem ---------------------------------------------------------------
rem  2. Виртуальное окружение (создаётся один раз)
rem ---------------------------------------------------------------
if exist ".venv\Scripts\python.exe" goto HAVE_VENV
echo  [1/4] Создаю рабочее окружение. Это нужно только при первом запуске.
%PYCMD% -m venv .venv
if errorlevel 1 goto VENV_FAILED

:HAVE_VENV
set "VPY=%~dp0.venv\Scripts\python.exe"

rem ---------------------------------------------------------------
rem  3. Зависимости
rem ---------------------------------------------------------------
if exist ".venv\.installed" goto HAVE_DEPS
echo  [2/4] Устанавливаю Django и Pillow. Нужен интернет, займёт минуту.
"%VPY%" -m pip install --upgrade pip --quiet
if exist "wheels\*.whl" goto INSTALL_OFFLINE

"%VPY%" -m pip install --quiet -r sources\requirements.txt
if errorlevel 1 goto PIP_FAILED
goto INSTALL_DONE

:INSTALL_OFFLINE
echo         Найдена папка wheels — ставлю без интернета.
"%VPY%" -m pip install --quiet --no-index --find-links wheels Django Pillow
if errorlevel 1 goto PIP_FAILED

:INSTALL_DONE
echo done > ".venv\.installed"

:HAVE_DEPS

rem ---------------------------------------------------------------
rem  4. База данных и содержимое портала
rem ---------------------------------------------------------------
"%VPY%" sources\manage.py migrate --noinput >nul
if errorlevel 1 goto DB_FAILED

if exist ".venv\.seeded" goto HAVE_DB
echo  [3/4] Наполняю портал: объекты, события, маршруты, пользователи.
"%VPY%" sources\manage.py seed_demo
if errorlevel 1 goto DB_FAILED
echo done > ".venv\.seeded"

:HAVE_DB

rem ---------------------------------------------------------------
rem  5. Запуск
rem ---------------------------------------------------------------
echo.
echo  [4/4] Запускаю сайт. Браузер откроется сам через несколько секунд.
echo.
echo   Сайт:              http://127.0.0.1:8000/
echo   Панель управления: http://127.0.0.1:8000/admin/
echo.
echo   Администратор:     admin    / admin12345
echo   Контент-менеджер:  manager  / manager12345
echo   Пользователь:      ivanova  / demo12345
echo.
echo   Чтобы остановить сайт, закройте это окно или нажмите Ctrl+C.
echo  --------------------------------------------------------------
echo.

start "" /min "%~dp0tools\open-site.bat"
"%VPY%" sources\manage.py runserver 127.0.0.1:8000 --noreload

echo.
echo  Сайт остановлен. Чтобы открыть снова, запустите START.bat.
pause
exit /b 0

rem ---------------------------------------------------------------
rem  Сообщения об ошибках
rem ---------------------------------------------------------------
:NO_PYTHON
echo.
echo  На компьютере не найден Python — без него сайт не запустится.
echo.
echo  Что сделать:
echo    1. Скачайте Python с https://www.python.org/downloads/
echo    2. При установке ОБЯЗАТЕЛЬНО поставьте галочку
echo       "Add python.exe to PATH" на первом экране.
echo    3. Перезапустите START.bat.
echo.
echo  Сейчас откроется страница загрузки.
timeout /t 5 >nul
start "" https://www.python.org/downloads/
pause
exit /b 1

:VENV_FAILED
echo.
echo  Не удалось создать рабочее окружение (.venv).
echo  Проверьте, что папка проекта не в "Program Files" и доступна для записи.
pause
exit /b 1

:PIP_FAILED
echo.
echo  Не удалось установить Django и Pillow.
echo  Чаще всего причина — нет доступа в интернет или его блокирует
echo  корпоративный прокси. Проверьте подключение и запустите START.bat снова.
pause
exit /b 1

:DB_FAILED
echo.
echo  Не удалось подготовить базу данных.
echo  Попробуйте удалить файл sources\db.sqlite3 и запустить START.bat снова.
pause
exit /b 1
