@echo off
REM ============================================================
REM Agente AR Isberoal - Ejecucion programada (Task Scheduler)
REM ============================================================
REM Programar diariamente a las 08:00 hora de Madrid en
REM Programador de Tareas de Windows. Argumentos: ninguno.

cd /d "G:\Unidades compartidas\01_ISBEROAL Energy\14_Agentes\Accounts-Receivable\files"

python agente_cobros.py --sync >> logs\task_scheduler.log 2>&1

exit /b %ERRORLEVEL%
