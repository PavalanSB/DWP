import sys
import traceback

print("Testing app import...")
try:
    from app import create_app
    app = create_app()
    print("create_app() succeeded!")
except Exception as e:
    print("ERROR:")
    traceback.print_exc()
