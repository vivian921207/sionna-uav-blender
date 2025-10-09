@echo off
cd /d E:\NYCU\topic2

echo [1] Adding all files...
git add .

echo [2] Committing with timestamp...
git commit -m "Auto commit on %DATE% %TIME%"

echo [3] Pushing to GitHub...
git push origin main

echo [✓] Push complete.
pause
