College Library Management System (Flask + SQLite)

What's included
- Flask backend (app.py)
- Templates and static assets (CSS, JS, placeholder image)
- Database schema and generator script to populate a large dataset (generate_db.py)
- Admin panel (username: admin, password: admin123)
- Student dashboard: search, new books, department filter, view book details, add reviews (no registration required)

Setup (Linux / macOS / WSL / Windows with Python 3.8+)
1. unzip the project or navigate into the folder.
2. Create a virtual env (recommended):
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
3. Install dependencies:
   pip install flask
4. Generate the database (creates library.db with sample data):
   python generate_db.py
5. Run the app:
   python app.py
6. Open http://127.0.0.1:5000 in your browser.

Notes
- To increase the number of books, edit n_books in generate_db.py (e.g., 20000) then re-run it. It may take longer for very large numbers.
- The admin password is stored in DB as SHA-256 hash. Change the password after first login for production.
