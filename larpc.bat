@echo off
rem Atalho para rodar o larpc de qualquer pasta.
rem Uso:  larpc programa.larp   |   larpc ver programa.larp
setlocal
set "PYTHONPATH=%~dp0;%PYTHONPATH%"
python -m larpc %*
