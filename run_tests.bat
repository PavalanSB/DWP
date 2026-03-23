.venv\Scripts\python test_app.py > test_app_out.txt 2>&1
.venv\Scripts\python test_routes.py > test_routes_out.txt 2>&1
dir test_*_out.txt
