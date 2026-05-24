# ============================================================
# app.py — The brain of MacroLens
# ============================================================

from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import timedelta
import os
import base64
import json

# ---- LOAD ENVIRONMENT VARIABLES ----
load_dotenv()       # Loads the safe API Keys stored in .env

# ---- INITIALIZE FLASK ----
app = Flask(__name__)
app.secret_key = "macrolens_zahan_2025_xk92"

# Keeps user logged in for 30 days without asking to login again
app.permanent_session_lifetime = timedelta(days=30)

# ---- ENABLE CORS ----
CORS(app)          # It is used to create a safe session between frontend and backend

# ---- CONNECT TO SUPABASE ----
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_ANON_KEY")
)

# ---- CONNECT TO GEMINI AI ----
from google import genai
from google.genai import types

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ============================================================
# ROUTES
# ============================================================

# ---- HOME PAGE ----
@app.route("/")
def home():
    # If already logged in, skip login page and go straight to dashboard
    if "user_id" in session:
        return render_template("dashboard.html")
    return render_template("login.html")

# ---- DASHBOARD ----
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return render_template("login.html")
    return render_template("dashboard.html")

# ---- SIGNUP ----
@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    name = data.get("name")

    try:
        response = supabase.auth.sign_up({
            "email": email,
            "password": password
        })

        user_id = response.user.id

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

        # Make session permanent so user stays logged in for 30 days
        session.permanent = True
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
@app.route("/save_profile", methods=["POST"])
def save_profile():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Not logged in"})

    data = request.get_json()
    print("Saving profile for user:", session["user_id"])
    print("Data received:", data)

    try:
        supabase.table("profiles").update({
            "height_cm": data.get("height"),
            "weight_kg": data.get("weight"),
            "age": data.get("age"),
            "goal": data.get("goal"),
            "gender": data.get("gender")
        }).eq("id", session["user_id"]).execute()

        print("Profile saved successfully")
        return jsonify({"success": True})
    except Exception as e:
        print("Error saving profile:", e)
        return jsonify({"success": False, "message": str(e)})

# ---- GET PROFILE ----
@app.route("/get_profile")
def get_profile():
    if "user_id" not in session:
        return jsonify({"success": False})

    try:
        response = supabase.table("profiles").select("*").eq(
            "id", session["user_id"]
        ).execute()

        profile = response.data[0] if response.data else {}
        calories = calculate_calories(profile)
        profile["daily_calories"] = calories

        return jsonify({"success": True, "profile": profile})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

# ---- CALORIE CALCULATOR ----
# Mifflin-St Jeor formula — used by dietitians worldwide
def calculate_calories(profile):
    try:
        weight = float(profile.get("weight_kg", 70))
        height = float(profile.get("height_cm", 170))
        age = float(profile.get("age", 20))
        gender = profile.get("gender", "male")
        goal = profile.get("goal", "maintain")

        if gender == "male":
            bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5
        else:
            bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161

        tdee = bmr * 1.55

        if goal == "cut":
            return round(tdee - 500)
        elif goal == "bulk":
            return round(tdee + 300)
        else:
            return round(tdee)
    except:
        return 2000

# ---- SCAN FOOD ----
@app.route("/scan_food", methods=["POST"])
def scan_food():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Not logged in"})

    try:
        file = request.files.get("image")
        image_data = file.read()

        prompt = """
        Analyze this food image and provide detailed nutritional information.
        This may include South Asian / Pakistani dishes like biryani, daal,
        karahi, roti, nihari, halwa puri, samosa, or any other dish.
        It may also include branded/packaged foods, fast food, or any cuisine.

        Provide:
        1. The dish name in English
        2. The original name if it's a non-English dish
        3. Estimated serving size
        4. Total nutrition for the serving
        5. A breakdown of the main ingredients with their individual calories

        Respond in this EXACT JSON format, nothing else:
        {
            "dish_name": "...",
            "original_name": "...",
            "serving_size": "...",
            "calories": 000,
            "protein": 00,
            "carbs": 00,
            "fat": 00,
            "fiber": 0,
            "ingredients": [
                {"name": "...", "calories": 00, "protein": 0, "carbs": 0, "fat": 0},
                {"name": "...", "calories": 00, "protein": 0, "carbs": 0, "fat": 0},
                {"name": "...", "calories": 00, "protein": 0, "carbs": 0, "fat": 0}
            ]
        }
        Only respond with the JSON, nothing else, no markdown, no code blocks.
        """

        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=[
                types.Part.from_text(text=prompt),
                types.Part.from_bytes(
                    data=image_data,
                    mime_type="image/jpeg"
                )
            ]
        )

        # Strip markdown code blocks if Gemini wraps response
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        nutrition = json.loads(raw.strip())

        # Save meal to database
        supabase.table("meals").insert({
            "user_id": session["user_id"],
            "dish_name": nutrition["dish_name"],
            "calories": nutrition["calories"],
            "protein": nutrition["protein"],
            "carbs": nutrition["carbs"],
            "fat": nutrition["fat"],
            "fiber": nutrition.get("fiber", 0),
            "serving_size": nutrition["serving_size"]
        }).execute()

        return jsonify({"success": True, "nutrition": nutrition})

    except Exception as e:
        print("Scan error:", e)
        return jsonify({"success": False, "message": str(e)})

# ---- GET TODAY'S MEALS ----
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

# ---- AI DIET CHATBOT ----
@app.route("/chat", methods=["POST"])
def chat():
    if "user_id" not in session:
        return jsonify({"success": False})

    data = request.get_json()
    user_message = data.get("message")
    calories_remaining = data.get("calories_remaining", 0)
    calories_consumed = data.get("calories_consumed", 0)
    daily_target = data.get("daily_target", 2000)
    protein_consumed = data.get("protein_consumed", 0)
    carbs_consumed = data.get("carbs_consumed", 0)
    fat_consumed = data.get("fat_consumed", 0)

    try:
        prompt = f"""
        You are a friendly personal nutrition coach inside the MacroLens app.

        User's stats today:
        - Daily calorie target: {daily_target} calories
        - Calories consumed so far: {calories_consumed} calories
        - Calories remaining: {calories_remaining} calories
        - Protein consumed: {protein_consumed}g
        - Carbs consumed: {carbs_consumed}g
        - Fat consumed: {fat_consumed}g

        Give short, practical, friendly advice.
        You know about Pakistani and South Asian foods like biryani, daal,
        karahi, roti, nihari, halwa puri, and more.
        Keep responses under 3 sentences unless a meal plan is requested.

        User: {user_message}
        """

        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )

        return jsonify({"success": True, "reply": response.text})

    except Exception as e:
        print("Chat error:", e)
        return jsonify({"success": True,
                        "reply": "Sorry, I'm having trouble right now. Try again!"})
        
# ---- SETTINGS PAGE ----
@app.route("/settings")
def settings():
    if "user_id" not in session:
        return render_template("login.html")
    return render_template("settings.html")

# ---- UPDATE PROFILE ----
@app.route("/update_profile", methods=["POST"])
def update_profile():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Not logged in"})

    data = request.get_json()

    try:
        supabase.table("profiles").update({
            "name": data.get("name"),
            "height_cm": data.get("height"),
            "weight_kg": data.get("weight"),
            "age": data.get("age"),
            "goal": data.get("goal"),
            "gender": data.get("gender")
        }).eq("id", session["user_id"]).execute()

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

# ---- START THE APP ----
if __name__ == "__main__":
    app.run(debug=True, port=5000)