call .venv\Scripts\activate.bat
python scripts\setup_test_users.py > users.log 2>&1
python app.py > server.log 2>&1
