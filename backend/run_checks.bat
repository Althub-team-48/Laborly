@echo off

echo Running Ruff lint check...
ruff check . --fix --unsafe-fixes
if %errorlevel% neq 0 (
    echo Ruff fix failed!
    exit /b %errorlevel%
)

echo Formatting with Black...
black .
if %errorlevel% neq 0 (
    echo Black formatting failed!
    exit /b %errorlevel%
)

echo Running Mypy type checks...
mypy .
if %errorlevel% neq 0 (
    echo Mypy failed!
    exit /b %errorlevel%
)

echo All checks passed successfully!
