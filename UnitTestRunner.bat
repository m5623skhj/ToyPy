@echo off
python -m unittest discover -s tests
exit /b %ERRORLEVEL%
