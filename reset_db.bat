IF EXIST instance\dwp_new.db del instance\dwp_new.db
IF EXIST dwp_new.db del dwp_new.db
.venv\Scripts\python scripts\setup_test_users.py > setup.log 2>&1
.venv\Scripts\python test_routes.py > test_out.txt 2>&1
