@echo off

cd /d "C:\dev\WeightApp"

powershell -NoProfile -ExecutionPolicy Bypass -Command "py weight_tracker.py"

pause