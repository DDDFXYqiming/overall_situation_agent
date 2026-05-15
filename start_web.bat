@echo off
setlocal

cd /d "%~dp0"

if not exist "vue_app\node_modules" (
  echo Installing Vue web dependencies...
  pushd "vue_app"
  call npm install
  if errorlevel 1 (
    popd
    exit /b 1
  )
  popd
)

python -m overall_situation_agent.cli web %*
