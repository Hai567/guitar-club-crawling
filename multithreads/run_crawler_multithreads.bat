@echo off
echo Starting Chrome with remote debugging...
start chrome --remote-debugging-port=9222
echo.
echo Please log in to your Guitar Club account in the Chrome browser.
echo.
echo When you're logged in, press any key to start the crawler...
pause > nul
echo.
echo Starting multithreaded crawler...
python crawler_multithreads.py
echo.
pause
