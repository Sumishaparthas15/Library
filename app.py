from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import sqlite3, os, hashlib, datetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "library.db")

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = "my_super_secret_key_12345"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Important: allows accessing columns by name
    return conn

# Student dashboard
@app.route("/")
def home():
    return render_template("home.html")
@app.route("/index")
def index():
    conn = get_db()
    cur = conn.cursor()
    # Show newest 20 books
    cur.execute("""
        SELECT b.*, d.name AS department_name
        FROM books b
        LEFT JOIN departments d ON b.department_id = d.id
        ORDER BY b.id DESC
        
    """)
    new_books = cur.fetchall()

    # Get all departments
    cur.execute("SELECT name FROM departments ORDER BY name")
    departments = [r["name"] for r in cur.fetchall()]

    conn.close()
    return render_template("index.html", new_books=new_books, departments=departments)

# Search API

@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    dept_name = request.args.get("dept", "").strip()
    
    conn = get_db()
    cur = conn.cursor()
    
    params = []
    query = """
    SELECT books.*, departments.name AS department_name
    FROM books
    LEFT JOIN departments ON books.department_id = departments.id
    WHERE 1=1
    """
    
    if q:
        query += " AND (books.title LIKE ? OR books.author LIKE ? OR books.description LIKE ?)"
        likeq = f"%{q}%"
        params.extend([likeq, likeq, likeq])
    
    if dept_name:
        query += " AND departments.name = ?"
        params.append(dept_name)
    
    query += " LIMIT 200"
    
    cur.execute(query, params)
    search_results = cur.fetchall()
    
    # Get all departments again for the dropdown
    cur.execute("SELECT name FROM departments ORDER BY name")
    departments = [r["name"] for r in cur.fetchall()]
    
    # Get latest books again for display
    cur.execute("""
        SELECT b.*, d.name AS department_name
        FROM books b
        LEFT JOIN departments d ON b.department_id = d.id
        ORDER BY b.id DESC LIMIT 20
    """)
    new_books = cur.fetchall()
    
    conn.close()
    
    return render_template("index.html", 
                           new_books=new_books,
                           search_results=search_results,
                           departments=departments)



# Book detail + reviews
@app.route("/book/<int:book_id>")
def book_detail(book_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM books WHERE id=?", (book_id,))
    book = cur.fetchone()
    if not book:
        conn.close()
        return "Book not found", 404
    cur.execute("SELECT * FROM reviews WHERE book_id=? ORDER BY created_at DESC", (book_id,))
    reviews = cur.fetchall()
    conn.close()
    return render_template("book.html", book=book, reviews=reviews)

# Submit review (no login required)
@app.route("/review", methods=["POST"])
def submit_review():
    book_id = request.form.get("book_id")
    name = request.form.get("name","Anonymous").strip() or "Anonymous"
    rating = int(request.form.get("rating",5))
    comment = request.form.get("comment","").strip()
    created_at = datetime.datetime.utcnow().isoformat()
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO reviews (book_id, name, rating, comment, created_at) VALUES (?, ?, ?, ?, ?)",
                (book_id, name, rating, comment, created_at))
    conn.commit()
    conn.close()
    flash("Thank you for your feedback!", "success")
    return redirect(url_for("book_detail", book_id=book_id))

@app.route('/newlaunch')
def newlaunch_books():
    conn = get_db()
    # Select last 3 books by ID in reverse order
    books = conn.execute('SELECT b.*, d.name as department_name FROM books b '
                         'LEFT JOIN departments d ON b.department_id = d.id '
                         'ORDER BY b.id DESC LIMIT 3').fetchall()
    conn.close()
    return render_template('new_launch_book.html', books=books)

# Admin login
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password").strip()

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM admins WHERE username=?", (username,))
        admin = cur.fetchone()
        conn.close()

        if admin and check_password_hash(admin["password"], password):
            session.clear()
            session["admin_logged_in"] = True
            session["admin_username"] = username
            session["is_superuser"] = bool(admin["is_superuser"])
            flash("Login successful!", "success")
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid username or password", "danger")

    return render_template("admin_login.html")




def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged_in"):
            flash("Please login first.", "warning")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated

# Admin dashboard
@app.route("/admin")
@admin_required
def admin_dashboard():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as c FROM books")
    total_books = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) as c FROM departments  ")
    total_departments = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) as c FROM reviews")
    total_reviews = cur.fetchone()["c"]
    conn.close()
    return render_template("admin_dashboard.html", total_books=total_books,total_departments=total_departments, total_reviews=total_reviews)

@app.route("/admin/logout")
@admin_required
def admin_logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("admin_login"))


# List and manage books
@app.route("/admin/books")
@admin_required
def admin_books():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        SELECT books.id, books.title, books.author, books.year,
               departments.name AS department,
               books.type, books.description, books.image
        FROM books
        LEFT JOIN departments ON books.department_id = departments.id
        ORDER BY books.id DESC
    ''')
    books = cur.fetchall()
    conn.close()
    return render_template('admin_books.html', books=books)

# Add book
@app.route("/admin/books/add", methods=["GET", "POST"])
@admin_required
def admin_add_book():
    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        title = request.form.get("title")
        author = request.form.get("author")
        year = request.form.get("year")
        department_id = request.form.get("department_id")
        book_type = request.form.get("type")
        description = request.form.get("description")

        # Handle file upload
        image_file = request.files.get("image")
        if image_file and image_file.filename != "":
            filename = secure_filename(image_file.filename)
            upload_path = os.path.join(app.static_folder, "uploads")
            os.makedirs(upload_path, exist_ok=True)
            save_path = os.path.join(upload_path, filename)
            image_file.save(save_path)
            image = "/static/uploads/" + filename
        else:
            image = None

        # Insert into DB
        cur.execute("""
            INSERT INTO books (title, author, year, department_id, type, description, image)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (title, author, year, department_id, book_type, description, image))

        conn.commit()
        conn.close()
        flash("Book added successfully!", "success")
        return redirect(url_for("admin_books"))

    # GET → load departments
    cur.execute("SELECT id, name FROM departments ORDER BY name")
    departments = cur.fetchall()
    conn.close()
    return render_template("admin_add_book.html", departments=departments)

# Edit book

@app.route("/admin/books/edit/<int:book_id>", methods=["GET","POST"])
@admin_required
def admin_edit_book(book_id):
    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        title = request.form.get("title")
        author = request.form.get("author")
        year = request.form.get("year")
        department_id = request.form.get("department_id")
        book_type = request.form.get("type")
        description = request.form.get("description")

        # Handle uploaded image
        image_file = request.files.get("image")
        if image_file and image_file.filename != "":
            filename = secure_filename(image_file.filename)
            upload_path = os.path.join(app.static_folder, "uploads")
            os.makedirs(upload_path, exist_ok=True)
            image_file.save(os.path.join(upload_path, filename))
            image = "/static/uploads/" + filename

            cur.execute("""
                UPDATE books SET title=?, author=?, year=?, department_id=?, type=?, description=?, image=?
                WHERE id=?
            """, (title, author, year, department_id, book_type, description, image, book_id))
        else:
            cur.execute("""
                UPDATE books SET title=?, author=?, year=?, department_id=?, type=?, description=?
                WHERE id=?
            """, (title, author, year, department_id, book_type, description, book_id))

        conn.commit()
        conn.close()
        flash("Book updated successfully!", "success")
        return redirect(url_for("admin_books"))

    # GET → load book and departments
    cur.execute("SELECT * FROM books WHERE id=?", (book_id,))
    book = cur.fetchone()
    cur.execute("SELECT id, name FROM departments ORDER BY name")
    departments = cur.fetchall()
    conn.close()
    return render_template("admin_edit_book.html", book=book, departments=departments)

# Delete book
@app.route("/admin/books/delete/<int:book_id>", methods=["POST"])
@admin_required
def admin_delete_book(book_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM books WHERE id=?", (book_id,))
    conn.commit()
    conn.close()
    flash("Book deleted", "success")
    return redirect(url_for("admin_books"))

# List Departments
@app.route("/admin/departments")
@admin_required
def admin_departments():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM departments ORDER BY name")
    departments = cur.fetchall()
    conn.close()
    return render_template("admin_departments.html", departments=departments)

# Add Department
@app.route("/admin/departments/add", methods=["GET","POST"])
@admin_required
def admin_add_department():
    if request.method == "POST":
        name = request.form.get("name").strip()
        if name:
            try:
                conn = get_db()
                cur = conn.cursor()
                cur.execute("INSERT INTO departments (name) VALUES (?)", (name,))
                conn.commit()
                conn.close()
                flash(f"Department '{name}' added successfully!", "success")
            except sqlite3.IntegrityError:
                flash(f"Department '{name}' already exists!", "danger")
        return redirect(url_for("admin_departments"))
    return render_template("admin_add_department.html")

# Edit Department
@app.route("/admin/departments/edit/<int:dept_id>", methods=["GET","POST"])
@admin_required
def admin_edit_department(dept_id):
    conn = get_db()
    cur = conn.cursor()
    if request.method == "POST":
        name = request.form.get("name").strip()
        if name:
            try:
                cur.execute("UPDATE departments SET name=? WHERE id=?", (name, dept_id))
                conn.commit()
                flash("Department updated successfully!", "success")
            except sqlite3.IntegrityError:
                flash(f"Department '{name}' already exists!", "danger")
        conn.close()
        return redirect(url_for("admin_departments"))
    cur.execute("SELECT * FROM departments WHERE id=?", (dept_id,))
    department = cur.fetchone()
    conn.close()
    return render_template("admin_edit_department.html", department=department)

# Delete Department
@app.route("/admin/departments/delete/<int:dept_id>", methods=["POST"])
@admin_required
def admin_delete_department(dept_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM departments WHERE id=?", (dept_id,))
    conn.commit()
    conn.close()
    flash("Department deleted successfully!", "success")
    return redirect(url_for("admin_departments"))



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=8000, debug=True)
