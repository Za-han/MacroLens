# ============================================================
# app.py — The brain of MacroLens
# This is the Flask server that runs everything
# ============================================================

from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
from dotenv import load_dotenv
from supabase import create_client, Client
import google.generativeai as genai
import os
import base64

# ---- LOAD ENVIRONMENT VARIABLES ----
# This reads your .env file and makes all your keys available
# Without this line, the app has no idea where your API keys are
load_dotenv()

# ---- INITIALIZE FLASK ----
# This creates your web app
# __name__ tells Flask where to find your templates and static files
app = Flask(__name__)

# This is needed for login sessions - It encrypts the session cookie
# Change this to any random string you want
app.secret_key = "macrolens_zahan_2025_xk92"

# ---- ENABLE CORS ----
# Allows your frontend HTML pages to talk to this Flask backend
# Without this the browser blocks all requests as a security measure
CORS(app)


# ---- CONNECT TO SUPABASE ----
# Reads your URL and key from .env and creates a connection
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_ANON_KEY")
)

# ---- CONNECT TO GEMINI AI ----
# Reads your Gemini key from .env and sets it up
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
# We use gemini-1.5-flash becuase it supports image scanning and is fee tier
model = genai.GenerativeModel("gemini-1.5-flash")

# ============================================================
# ROUTES — These are the pages and endpoints of your app
# Think of routes like doors into your app
# Each @app.route defines what happens when someone visits that URL
# ============================================================

# ---- HOME PAGE ----
# When someone visits http://localhost:5000 they see the login page
@app.route("/")
def home():
   return render_template("login.html")

# ---- DASHBOARD ----
# Only accessible after logging in
@app.route("/dashboard")
def dashboard():
    # Check if user is logged in — if not send them back to login
    if "user_id" not in session:
        return render_template("login.html")
    return render_template("dashboard.html")

# ---- SIGNUP ----
# Handles new user registration
@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    name = data.get("name")

    try:
        # Create user in Supabase Auth
        response = supabase.auth.sign_up({
            "email": email,
            "password": password
        })

        user_id = response.user.id

        # Save extra profile info in our profiles table
        supabase.table("profiles").insert({
            "id": user_id,
            "name": name,
            "email": email
        }).execute()

        return jsonify({"success": True, "message": "Account created!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

# ---- LOGIN ----
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    try:
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        # Store user info in session so we know they're logged in
        session["user_id"] = response.user.id
        session["email"] = response.user.email

        return jsonify({"success": True, "message": "Logged in!"})
    except Exception as e:
        return jsonify({"success": False, "message": "Invalid email or password"})

# ---- LOGOUT ----
@app.route("/logout")
def logout():
    session.clear()
    return render_template("login.html")

# ---- SAVE PROFILE ----
# Saves user's height, weight, age, goal after they set up their profile
@app.route("/save_profile", methods=["POST"])
def save_profile():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Not logged in"})

    data = request.get_json()

    try:
        supabase.table("profiles").update({
            "height_cm": data.get("height"),
            "weight_kg": data.get("weight"),
            "age": data.get("age"),
            "goal": data.get("goal"),  # 'cut', 'maintain', or 'bulk'
            "gender": data.get("gender")
        }).eq("id", session["user_id"]).execute()

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

# ---- GET PROFILE ----
# Returns user's profile data to display on dashboard
@app.route("/get_profile")
def get_profile():
    if "user_id" not in session:
        return jsonify({"success": False})

    try:
        response = supabase.table("profiles").select("*").eq(
            "id", session["user_id"]
        ).execute()

        profile = response.data[0] if response.data else {}

        # Calculate daily calorie target based on profile
        calories = calculate_calories(profile)
        profile["daily_calories"] = calories

        return jsonify({"success": True, "profile": profile})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

# ---- CALORIE CALCULATOR ----
# Uses the Mifflin-St Jeor formula — the most accurate calorie formula
# This is what dietitians and fitness apps actually use
def calculate_calories(profile):
    try:
        weight = float(profile.get("weight_kg", 70))
        height = float(profile.get("height_cm", 170))
        age = float(profile.get("age", 20))
        gender = profile.get("gender", "male")
        goal = profile.get("goal", "maintain")

        # Mifflin-St Jeor Formula
        if gender == "male":
            bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5
        else:
            bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161

        # Multiply by activity factor (we assume moderate activity)
        tdee = bmr * 1.55

        # Adjust based on goal
        if goal == "cut":
            return round(tdee - 500)   # 500 calorie deficit to lose fat
        elif goal == "bulk":
            return round(tdee + 300)   # 300 calorie surplus to gain muscle
        else:
            return round(tdee)         # Maintenance

    except:
        return 2000  # Default fallback

# ---- SCAN FOOD ----
# The star feature — takes a photo and returns calories + macros
@app.route("/scan_food", methods=["POST"])
def scan_food():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Not logged in"})

    try:
        # Get the image from the request
        file = request.files.get("image")
        image_data = file.read()

        # Convert image to base64 so Gemini can read it
        image_base64 = base64.b64encode(image_data).decode("utf-8")

        # Ask Gemini to analyze the food
        # This prompt is carefully written to get structured data back
        prompt = """
        Analyze this food image and provide nutritional information.
        This may include South Asian / Pakistani dishes like biryani, daal, 
        karahi, roti, nihari, halwa puri, samosa, or any other dish.
        
        Identify the dish name and provide:
        - Dish name (in English and original name if applicable)
        - Estimated serving size
        - Calories
        - Protein (grams)
        - Carbohydrates (grams)
        - Fat (grams)
        - Fiber (grams)
        
        Respond in this exact JSON format:
        {
            "dish_name": "...",
            "original_name": "...",
            "serving_size": "...",
            "calories": 000,
            "protein": 00,
            "carbs": 00,
            "fat": 00,
            "fiber": 0
        }
        Only respond with the JSON, nothing else.
        """

        # Send image + prompt to Gemini
        response = model.generate_content([
            prompt,
            {"mime_type": "image/jpeg", "data": image_base64}
        ])

        # Parse the response
        import json
        nutrition = json.loads(response.text.strip())

        # Log this meal to the database
        supabase.table("meals").insert({
            "user_id": session["user_id"],
            "dish_name": nutrition["dish_name"],
            "calories": nutrition["calories"],
            "protein": nutrition["protein"],
            "carbs": nutrition["carbs"],
            "fat": nutrition["fat"],
            "fiber": nutrition["fiber"],
            "serving_size": nutrition["serving_size"]
        }).execute()

        return jsonify({"success": True, "nutrition": nutrition})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

# ---- GET TODAY'S MEALS ----
# Returns all meals logged today for the logged in user
@app.route("/get_todays_meals")
def get_todays_meals():
    if "user_id" not in session:
        return jsonify({"success": False})

    try:
        from datetime import date
        today = date.today().isoformat()

        response = supabase.table("meals").select("*").eq(
            "user_id", session["user_id"]
        ).gte("created_at", today).execute()

        meals = response.data
        total_calories = sum(m["calories"] for m in meals)
        total_protein = sum(m["protein"] for m in meals)
        total_carbs = sum(m["carbs"] for m in meals)
        total_fat = sum(m["fat"] for m in meals)

        return jsonify({
            "success": True,
            "meals": meals,
            "totals": {
                "calories": total_calories,
                "protein": total_protein,
                "carbs": total_carbs,
                "fat": total_fat
            }
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

# ---- START THE APP ----
if __name__ == "__main__":
    # debug=True means the server auto-restarts when you save changes
    # Great for development, turn off in production
    app.run(debug=True, port=5000)



