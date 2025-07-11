@ECHO OFF
@SET PYTHONIOENCODING=utf-8
@SET PYTHONUTF8=1
@FOR /F "tokens=2 delims=:." %%A in ('chcp') do for %%B in (%%A) do set "_CONDA_OLD_CHCP=%%B"
@chcp 65001 > NUL
@CALL "C:\Users\rawal\miniconda3\condabin\conda.bat" activate "c:\Users\rawal\OneDrive\डेस्कटॉप\Crime_satety_appV2\.conda"
@IF %ERRORLEVEL% NEQ 0 EXIT /b %ERRORLEVEL%
@c:\Users\rawal\OneDrive\डेस्कटॉप\Crime_satety_appV2\.conda\python.exe -Wi -m compileall -q -l -i C:\Users\rawal\AppData\Local\Temp\tmpf0m7pih6 -j 0
@IF %ERRORLEVEL% NEQ 0 EXIT /b %ERRORLEVEL%
@chcp %_CONDA_OLD_CHCP%>NUL
