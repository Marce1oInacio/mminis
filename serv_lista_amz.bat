@echo off
:: Define os caminhos conforme sua estrutura
set "PYTHON_EXE=D:\vscode\.vscode\mminis\venv\Scripts\python.exe"
set "SCRIPT_PY=D:\vscode\.vscode\mminis\monitor_wishlist.py"

:: Muda para o diretório do script para evitar erros de caminhos relativos
cd /d "D:\vscode\.vscode\mminis\"

:: Executa o script
"%PYTHON_EXE%" "%SCRIPT_PY%"

:: Se quiser que a janela feche sozinha, remova a linha abaixo
pause
