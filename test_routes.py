import os
print("Starting script...")

try:
    print("Importing create_app...")
    from app import create_app
    print("Imported outcreate_app.")
    
    app = create_app()
    print("Created app.")
    
    client = app.test_client()
    with app.app_context():
        # Setup context
        print("Starting test...")
        
        # 1. Login with wrong password 3 times
        print("\n--- Test 1: 3 Failed Logins ---")
        for i in range(1, 4):
            resp = client.post('/auth/login', data={'email': 'user@example.com', 'password': 'wrongpass', 'remember': '0'})
            # Flash messages can be checked via session, but we will just print the response or redirect
            print(f"Attempt {i} completed. Redirected to: {resp.headers.get('Location', 'No redirect')}")
            
        # 4th attempt to verify lockout message
        resp = client.post('/auth/login', data={'email': 'user@example.com', 'password': 'wrongpass'})
        print(f"Attempt 4 (Locked) HTML Contains 'contact an admin': {'contact an admin' in resp.get_data(as_text=True).lower()}")

        # 2. Login as admin
        print("\n--- Test 2: Admin Login ---")
        resp = client.post('/auth/login', data={'email': 'admin@example.com', 'password': 'admin123'})
        print(f"Admin login redirected to: {resp.headers.get('Location', 'No redirect')}")

        # 3. View Admin Dashboard
        print("\n--- Test 3: Admin Dashboard ---")
        resp = client.get('/admin/', follow_redirects=True)
        html = resp.get_data(as_text=True)
        print(f"Admin Dashboard loaded: {'Admin Dashboard' in html}")
        print(f"Shows locked user: {'user@example.com' in html}")

        # Get user ID to unlock
        from models import User
        u = User.get_by_email('user@example.com')
        
        # 4. Unlock user
        print("\n--- Test 4: Unlock User ---")
        if u:
            resp = client.post(f'/admin/unlock/{u.id}')
            print(f"Unlock redirected to: {resp.headers.get('Location', 'No redirect')}")

            # 5. Login as unlocked user
            print("\n--- Test 5: Login Unlocked User ---")
            client.get('/auth/logout') # Ensure admin is logged out
            resp = client.post('/auth/login', data={'email': 'user@example.com', 'password': 'user123'})
            print(f"User login redirected to: {resp.headers.get('Location', 'No redirect')}")
        else:
            print("User not found!")

except Exception as e:
    import traceback
    traceback.print_exc()

print("Script finished.")
