from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3, os, json, uuid, re
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(INSTANCE_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key-before-deployment")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
app.config["UPLOAD_FOLDER"] = UPLOAD_DIR
DB_PATH = os.path.join(INSTANCE_DIR, "potholes.db")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
INDIAN_STATES = ['Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh', 'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka', 'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram', 'Nagaland', 'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu', 'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal', 'Andaman and Nicobar Islands', 'Chandigarh', 'Dadra and Nagar Haveli and Daman and Diu', 'Delhi', 'Jammu and Kashmir', 'Ladakh', 'Lakshadweep', 'Puducherry']

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'citizen'
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL, area TEXT NOT NULL, road TEXT NOT NULL,
            state TEXT NOT NULL DEFAULT 'Gujarat', district TEXT NOT NULL DEFAULT '',
            city TEXT NOT NULL DEFAULT '', ward TEXT NOT NULL DEFAULT '', pincode TEXT NOT NULL DEFAULT '',
            description TEXT, severity TEXT NOT NULL, depth_cm REAL NOT NULL,
            latitude REAL, longitude REAL, status TEXT NOT NULL DEFAULT 'Submitted',
            image TEXT, reporter TEXT NOT NULL, created_at TEXT NOT NULL,
            is_demo INTEGER NOT NULL DEFAULT 0
        )""")
        admin = db.execute("SELECT id FROM users WHERE email=?", ("admin@potholereporter.local",)).fetchone()
        if not admin:
            db.execute("INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)",
                       ("Demo Admin", "admin@potholereporter.local",
                        generate_password_hash("Admin@12345"), "admin"))
        count = db.execute("SELECT COUNT(*) AS n FROM reports").fetchone()["n"]
        if count == 0:
            now = datetime.now()
            demo = [
                ("Deep pothole near bus stop","Vastrapur","IIM Road","Large pothole near the bus stop", "High", 12.0, 23.0395,72.5300,"In Progress",now- timedelta(days=1)),
                ("Road surface damage","Navrangpura","CG Road","Several connected depressions", "Medium", 6.5,23.0350,72.5600,"Submitted",now-timedelta(days=3)),
                ("Pothole near school gate","Satellite","100 Feet Road","Potential hazard for two-wheelers", "High",10.0,23.0250,72.5100,"Resolved",now-timedelta(days=6)),
                ("Small road cavity","Bodakdev","Sindhu Bhavan Road","Small pothole on left lane", "Low",2.5,23.0450,72.5050,"Submitted",now-timedelta(days=9)),
                ("Multiple potholes","Maninagar","Station Road","Multiple potholes after rainfall", "High",14.0,22.9970,72.6030,"In Progress",now-timedelta(days=12)),
                ("Damaged junction","Thaltej","S.G. Highway","Damaged road at junction", "Medium",7.0,23.0500,72.5150,"Submitted",now-timedelta(days=18)),
                ("Pothole by market","Paldi","Anandnagar Road","Pothole close to market entrance", "Low",3.0,23.0120,72.5550,"Resolved",now-timedelta(days=25)),
                ("Large pothole","Vastrapur","Drive-In Road","Deep pothole affecting traffic", "High",13.0,23.0400,72.5350,"Submitted",now-timedelta(days=32)),
                ("Uneven road patch","Navrangpura","Commerce Six Road","Uneven road surface", "Medium",5.5,23.0320,72.5650,"Resolved",now-timedelta(days=40)),
                ("Pothole near crossing","Maninagar","Rambaug Road","Pothole near pedestrian crossing", "High",9.5,22.9990,72.6000,"Submitted",now-timedelta(days=50)),
                ("Minor road damage","Satellite","Prahlad Nagar Road","Small depression in road", "Low",2.0,23.0150,72.5100,"Resolved",now-timedelta(days=65)),
                ("Waterlogged pothole","Bodakdev","Thaltej-Shilaj Road","Water-filled pothole", "High",11.0,23.0480,72.5000,"In Progress",now-timedelta(days=80)),
            ]
            for r in demo:
                title,area,road,desc,severity,depth,lat,lon,status,dt = r
                db.execute("""INSERT INTO reports(title,area,road,state,district,city,ward,pincode,description,severity,depth_cm,latitude,longitude,status,image,reporter,created_at,is_demo)
                              VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)""",
                           (title,area,road,"Gujarat","Ahmedabad","Ahmedabad","West Zone","3800{}".format((len(area)+1)%10),desc,severity,depth,lat,lon,status,None,"Demo Dataset",dt.isoformat(timespec="seconds")))
        db.commit()

def allowed_file(filename):
    return "." in filename and filename.rsplit(".",1)[1].lower() in ALLOWED_EXTENSIONS

def current_user():
    return session.get("user")

def fetch_reports():
    with get_db() as db:
        rows = db.execute("SELECT * FROM reports ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]

def analytics(reports):
    """Descriptive and inferential-style statistics over the available report dataset."""
    if not reports:
        return {
            "total":0,"resolved":0,"pending":0,"resolution_rate":0,
            "avg_depth":0,"median_depth":0,"std_depth":0,"mean_severity":0,
            "severity_counts":{"Low":0,"Medium":0,"High":0},
            "area_labels":[],"area_values":[],"state_labels":[],"state_values":[],"month_labels":[],"month_values":[],
            "hotspots":[],"correlation":None,"trend_slope":0,"insight":"No reports yet."
        }

    df = pd.DataFrame(reports)
    df["depth_cm"] = pd.to_numeric(df["depth_cm"], errors="coerce").fillna(0)
    severity_map = {"Low":1, "Medium":2, "High":3}
    df["severity_score"] = df["severity"].map(severity_map).fillna(1)
    total = int(len(df))
    resolved = int((df["status"] == "Resolved").sum())
    pending = total - resolved
    avg_depth = float(df["depth_cm"].mean())
    median_depth = float(df["depth_cm"].median())
    std_depth = float(df["depth_cm"].std(ddof=0)) if total > 1 else 0.0
    mean_severity = float(df["severity_score"].mean())

    severity_counts = {k:int((df["severity"]==k).sum()) for k in ["Low","Medium","High"]}
    area_counts = df.groupby("area").size().sort_values(ascending=False)
    area_labels = area_counts.index.astype(str).tolist()[:7]
    area_values = [int(x) for x in area_counts.values[:7]]
    state_counts = df.groupby("state").size().sort_values(ascending=False)
    state_labels = state_counts.index.astype(str).tolist()[:10]
    state_values = [int(x) for x in state_counts.values[:10]]

    dates = pd.to_datetime(df["created_at"], errors="coerce")
    df["month"] = dates.dt.to_period("M").astype(str)
    month_counts = df.groupby("month").size().sort_index()
    month_labels = month_counts.index.astype(str).tolist()[-6:]
    month_values = [int(x) for x in month_counts.values[-6:]]

    # Risk index: combines average severity, mean depth and report volume.
    location_counts = df.groupby(["state","city","area"]).size().sort_values(ascending=False)
    max_area_count = max(location_counts.max(), 1)
    hotspots = []
    for (state_name, city_name, area_name), count in location_counts.items():
        subset = df[(df["state"] == state_name) & (df["city"] == city_name) & (df["area"] == area_name)]
        severity_avg = float(subset["severity_score"].mean())
        depth_avg = float(subset["depth_cm"].mean())
        risk = min(100, round((severity_avg/3*45) + (min(depth_avg,15)/15*35) + (count/max_area_count*20), 1))
        hotspots.append({"state":str(state_name),"city":str(city_name),"area":str(area_name),
                         "reports":int(count),"avg_depth":round(depth_avg,1),"risk":risk})
    hotspots.sort(key=lambda x:x["risk"], reverse=True)

    corr = None
    if total > 1 and df["depth_cm"].std(ddof=0) > 0 and df["severity_score"].std(ddof=0) > 0:
        corr = round(float(np.corrcoef(df["depth_cm"], df["severity_score"])[0,1]), 3)

    # Linear trend on monthly report counts; slope is reports/month.
    slope = 0.0
    if len(month_values) > 1:
        slope = round(float(np.polyfit(np.arange(len(month_values)), month_values, 1)[0]), 2)

    resolution_rate = round(resolved/total*100, 1)
    if hotspots:
        insight = f"{hotspots[0]['area']} currently has the highest calculated risk index ({hotspots[0]['risk']}/100)."
    else:
        insight = "Add reports to generate hotspot insights."

    return {
        "total":total,"resolved":resolved,"pending":pending,"resolution_rate":resolution_rate,
        "avg_depth":round(avg_depth,1),"median_depth":round(median_depth,1),
        "std_depth":round(std_depth,2),"mean_severity":round(mean_severity,2),
        "severity_counts":severity_counts,"area_labels":area_labels,"area_values":area_values,
        "state_labels":state_labels,"state_values":state_values,
        "month_labels":month_labels,"month_values":month_values,"hotspots":hotspots[:6],
        "correlation":corr,"trend_slope":slope,"insight":insight
    }

@app.route("/")
def index():
    reports = fetch_reports()
    stats = analytics(reports)
    return render_template("index.html", reports=reports[:8], stats=stats, user=current_user())

@app.route("/report", methods=["GET","POST"])
def report():
    if request.method == "POST":
        title = request.form.get("title","").strip()
        area = request.form.get("area","").strip()
        road = request.form.get("road","").strip()
        state = request.form.get("state","").strip()
        district = request.form.get("district","").strip()
        city = request.form.get("city","").strip()
        ward = request.form.get("ward","").strip()
        pincode = request.form.get("pincode","").strip()
        description = request.form.get("description","").strip()
        severity = request.form.get("severity","Medium")
        try:
            depth = float(request.form.get("depth_cm", 0))
            lat = float(request.form["latitude"]) if request.form.get("latitude") else None
            lon = float(request.form["longitude"]) if request.form.get("longitude") else None
        except ValueError:
            flash("Please enter valid numeric values for depth and coordinates.", "error")
            return redirect(url_for("report"))
        if (not title or not area or not road or state not in INDIAN_STATES or
            not district or not city or not re.fullmatch(r"\d{6}", pincode) or
            depth < 0 or severity not in {"Low","Medium","High"}):
            flash("Please complete all required fields with valid values.", "error")
            return redirect(url_for("report"))
        image_name = None
        upload = request.files.get("photo")
        if upload and upload.filename:
            if not allowed_file(upload.filename):
                flash("Upload a PNG, JPG, JPEG or WEBP image.", "error")
                return redirect(url_for("report"))
            ext = secure_filename(upload.filename).rsplit(".",1)[1].lower()
            image_name = f"{uuid.uuid4().hex}.{ext}"
            upload.save(os.path.join(UPLOAD_DIR, image_name))
        reporter = current_user()["name"] if current_user() else "Guest Citizen"
        with get_db() as db:
            db.execute("""INSERT INTO reports(title,area,road,state,district,city,ward,pincode,description,severity,depth_cm,latitude,longitude,status,image,reporter,created_at,is_demo)
                          VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)""",
                       (title,area,road,state,district,city,ward,pincode,description,severity,depth,lat,lon,"Submitted",image_name,reporter,datetime.now().isoformat(timespec="seconds")))
            db.commit()
        flash("Your pothole report has been submitted successfully.", "success")
        return redirect(url_for("index"))
    return render_template("report.html", user=current_user(), states=INDIAN_STATES)

@app.route("/reports")
def reports_page():
    reports = fetch_reports()
    return render_template("reports.html", reports=reports, user=current_user())

@app.route("/analytics")
def analytics_page():
    stats = analytics(fetch_reports())
    return render_template("analytics.html", stats=stats, user=current_user())

@app.route("/api/analytics")
def analytics_api():
    return jsonify(analytics(fetch_reports()))

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email","").lower().strip()
        password = request.form.get("password","")
        with get_db() as db:
            user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session["user"] = {"id":user["id"],"name":user["name"],"email":user["email"],"role":user["role"]}
            flash("Welcome back!", "success")
            return redirect(url_for("index"))
        flash("Invalid email or password.", "error")
    return render_template("login.html", user=current_user())

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name","").strip()
        email = request.form.get("email","").lower().strip()
        password = request.form.get("password","")
        if not name or not email or len(password) < 8:
            flash("Enter your name, a valid email and a password of at least 8 characters.", "error")
        else:
            try:
                with get_db() as db:
                    db.execute("INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,'citizen')",
                               (name,email,generate_password_hash(password)))
                    db.commit()
                flash("Account created. You can now sign in.", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("That email is already registered.", "error")
    return render_template("register.html", user=current_user())

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("index"))

@app.route("/admin/update/<int:report_id>", methods=["POST"])
def update_report(report_id):
    user = current_user()
    if not user or user.get("role") != "admin":
        flash("Admin access is required to update report status.", "error")
        return redirect(url_for("reports_page"))
    status = request.form.get("status")
    if status not in {"Submitted","In Progress","Resolved"}:
        flash("Invalid status.", "error")
    else:
        with get_db() as db:
            db.execute("UPDATE reports SET status=? WHERE id=?", (status,report_id))
            db.commit()
        flash("Report status updated.", "success")
    return redirect(url_for("reports_page"))

@app.errorhandler(413)
def too_large(_):
    flash("Image must be smaller than 5 MB.", "error")
    return redirect(url_for("report"))

init_db()

if __name__ == "__main__":
    app.run(debug=True)
