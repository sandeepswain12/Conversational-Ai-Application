from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_pymongo import PyMongo
import bcrypt
import google.generativeai as genai
import os
from dotenv import load_dotenv


# Load .env file
load_dotenv()

# Configure Google Gemini API
GENAI_API_KEY = os.getenv("GENAI_API_KEY")
genai.configure(api_key=GENAI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")  # Read secret key from .env
app.config["MONGO_URI"] = os.getenv("MONGO_URI")
mongo = PyMongo(app)

# Home Route (Login Required)
@app.route("/")
def home():
    if "user" not in session:
        return redirect(url_for("login"))

    chats = mongo.db.chats.find({})
    myChats = [chat for chat in chats]
    return render_template("index.html", myChats=myChats)

# User Registration
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        existing_user = mongo.db.users.find_one({"username": username})
        if existing_user:
            return "Username already exists. Try another."

        hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        mongo.db.users.insert_one({"username": username, "password": hashed_pw})

        return redirect(url_for("login"))

    return render_template("register.html")

# User Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = mongo.db.users.find_one({"username": username})
        if user and bcrypt.checkpw(password.encode("utf-8"), user["password"]):
            session["user"] = username
            return redirect(url_for("home"))
        return "Invalid credentials. Try again."

    return render_template("login.html")

# User Logout
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

# Chat API (Login Required)
@app.route("/api", methods=["POST"])
def qa():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    question = request.json.get("question")
    chat = mongo.db.chats.find_one({"question": question})

    if chat:
        return jsonify({"question": question, "answer": chat["answer"]})

    response = model.generate_content(question)
    answer = response.text.strip() if response.text else "Sorry, I couldn't generate a response."

    mongo.db.chats.insert_one({"question": question, "answer": answer})
    return jsonify({"question": question, "answer": answer})

if __name__ == "__main__":
    app.run(debug=True, port=5001)
