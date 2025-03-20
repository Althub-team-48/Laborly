@REM copy and run this in terminal make sure you update the message to suit the change: migrate.bat "create initial tables"

@echo off
if "%~1"=="" (
    echo Usage: migrate.bat "migration message"
    exit /b 1
)
rmdir /S /Q migrations\versions
mkdir migrations\versions
alembic -c alembic.ini revision --autogenerate -m "%~1"
alembic -c alembic.ini upgrade head
echo Migration applied successfully.