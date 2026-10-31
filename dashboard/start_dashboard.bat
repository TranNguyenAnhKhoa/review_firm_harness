@echo off
title Workplace Make Firm - AI Video Pipeline Monitor
cd /d "d:\workplace_make_firm"
echo Starting Workplace Make Firm Workflow Monitor on http://localhost:3000 ...
"d:\workplace_make_firm\review_firm_china\ai-video-review\.venv\Scripts\python.exe" "d:\workplace_make_firm\dashboard\server.py"
pause
