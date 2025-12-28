from flask import Flask, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
from bson.objectid import ObjectId
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

# MongoDB Connection
client = MongoClient(os.getenv("MONGO_URI"))  # Local database
db = client["studentsdb"]
collection = db["students"]
admins = db["admins"]

# Create default admin if not exists
if admins.count_documents({}) == 0:
    admins.insert_one({
        "username": "admin",
        "password": generate_password_hash("admin123")
    })


# --- LOGIN REQUIRED DECORATOR ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "admin" not in session:
            flash("Please login first!", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# --- ROUTES ---
@app.route("/")
def home():
    return render_template("home.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        admin = admins.find_one({"username": username})

        if admin and check_password_hash(admin["password"], password):
            session["admin"] = username
            flash("Login Successful!", "success")
            return redirect(url_for("show_students"))
        else:
            flash("Invalid Username or Password!", "error")
            return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("admin", None)
    flash("Logged Out Successfully!", "info")
    return redirect(url_for("login"))


# --- CRUD OPERATIONS ---

# CREATE
@app.route("/add", methods=["GET", "POST"])
@login_required
def add_student():
    if request.method == "POST":
        name = request.form["name"]
        course = request.form["course"]
        collection.insert_one({"name": name, "course": course})
        flash("Student Added Successfully ✔️", "success")
        return redirect(url_for("show_students"))
    return render_template("add.html")


# READ + SEARCH + PAGINATIONs
@app.route("/students")
@login_required
def show_students():
    page = int(request.args.get("page", 1))
    limit = 5
    skip = (page - 1) * limit

    search = request.args.get("search", "")
    query = {"$or": [
        {"name": {"$regex": search, "$options": "i"}},
        {"course": {"$regex": search, "$options": "i"}}
    ]} if search else {}

    students = list(collection.find(query).skip(skip).limit(limit))
    total = collection.count_documents(query)
    total_pages = (total + limit - 1) // limit

    return render_template("students.html", students=students,
                           page=page, total_pages=total_pages, search=search)


# DELETE
@app.route("/delete/<id>")
@login_required
def delete_student(id):
    collection.delete_one({"_id": ObjectId(id)})
    flash("Student Deleted 🗑️", "warning")
    return redirect(url_for("show_students"))


# UPDATE
@app.route("/edit/<id>", methods=["GET", "POST"])
@login_required
def edit_student(id):
    student = collection.find_one({"_id": ObjectId(id)})

    if request.method == "POST":
        name = request.form["name"]
        course = request.form["course"]
        collection.update_one({"_id": ObjectId(id)}, {"$set": {"name": name, "course": course}})
        flash("Student Updated Successfully ✏️", "success")
        return redirect(url_for("show_students"))

    return render_template("edit.html", student=student)

@app.route("/dashboard")
@login_required
def dashboard():
    from collections import Counter
    
    # Fetch all students
    students = list(collection.find())
    
    # Count students by course
    courses = [s["course"] for s in students]
    data = Counter(courses)  # {'Python': 3, 'Java': 4, ...}
    
    labels = list(data.keys())
    values = list(data.values())

    total_students = len(students)

    return render_template(
        "dashboard.html",
        labels=labels,
        values=values,
        total_students=total_students
    )


if __name__ == "__main__":
    app.run()