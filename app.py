import os
import secrets
import string
from datetime import date, timedelta
from functools import wraps

import mysql.connector
from mysql.connector import Error
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)

# Supports ordinary DB_* variables and Railway's MYSQL* variables.
DB_CONFIG = {
    "host": os.environ.get("DB_HOST") or os.environ.get("MYSQLHOST") or os.environ.get("MYSQL_HOST") or "localhost",
    "user": os.environ.get("DB_USER") or os.environ.get("MYSQLUSER") or os.environ.get("MYSQL_USER") or "root",
    "password": os.environ.get("DB_PASSWORD") or os.environ.get("MYSQLPASSWORD") or os.environ.get("MYSQL_PASSWORD") or "",
    "database": os.environ.get("DB_NAME") or os.environ.get("MYSQLDATABASE") or os.environ.get("MYSQL_DATABASE") or "railway_reservation",
    "port": int(os.environ.get("DB_PORT") or os.environ.get("MYSQLPORT") or os.environ.get("MYSQL_PORT") or "3306"),
    "connection_timeout": 10,
}

app.config["DB_INITIALIZED"] = False


def get_db():
    """Create a new MySQL connection for one request/operation."""
    return mysql.connector.connect(**DB_CONFIG)


def initialize_database():
    """Create project tables and demo records automatically on first visit."""
    conn = get_db()
    try:
        cursor = conn.cursor()
        statements = [
            """CREATE TABLE IF NOT EXISTS users (
                user_id INT AUTO_INCREMENT PRIMARY KEY,
                full_name VARCHAR(100) NOT NULL,
                email VARCHAR(150) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB""",
            """CREATE TABLE IF NOT EXISTS trains (
                train_id INT AUTO_INCREMENT PRIMARY KEY,
                train_number VARCHAR(10) NOT NULL UNIQUE,
                train_name VARCHAR(120) NOT NULL,
                source_station VARCHAR(80) NOT NULL,
                destination_station VARCHAR(80) NOT NULL,
                departure_time TIME NOT NULL,
                arrival_time TIME NOT NULL,
                duration VARCHAR(30) NOT NULL,
                total_seats INT NOT NULL,
                fare DECIMAL(10,2) NOT NULL,
                CHECK (total_seats > 0), CHECK (fare >= 0),
                INDEX idx_train_route (source_station, destination_station)
            ) ENGINE=InnoDB""",
            """CREATE TABLE IF NOT EXISTS train_schedules (
                schedule_id INT AUTO_INCREMENT PRIMARY KEY,
                train_id INT NOT NULL,
                journey_date DATE NOT NULL,
                available_seats INT NOT NULL,
                CONSTRAINT fk_schedule_train FOREIGN KEY (train_id) REFERENCES trains(train_id) ON DELETE CASCADE,
                CONSTRAINT uq_train_journey UNIQUE (train_id, journey_date),
                CHECK (available_seats >= 0), INDEX idx_schedule_date_route (journey_date, train_id)
            ) ENGINE=InnoDB""",
            """CREATE TABLE IF NOT EXISTS bookings (
                booking_id BIGINT AUTO_INCREMENT PRIMARY KEY,
                pnr_number VARCHAR(12) NOT NULL UNIQUE,
                user_id INT NOT NULL,
                schedule_id INT NOT NULL,
                booking_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                number_of_passengers INT NOT NULL,
                total_fare DECIMAL(10,2) NOT NULL,
                booking_status ENUM('CONFIRMED','CANCELLED') NOT NULL DEFAULT 'CONFIRMED',
                CONSTRAINT fk_booking_user FOREIGN KEY (user_id) REFERENCES users(user_id),
                CONSTRAINT fk_booking_schedule FOREIGN KEY (schedule_id) REFERENCES train_schedules(schedule_id),
                CHECK (number_of_passengers BETWEEN 1 AND 6), CHECK (total_fare >= 0),
                INDEX idx_booking_user_date (user_id, booking_date)
            ) ENGINE=InnoDB""",
            """CREATE TABLE IF NOT EXISTS passengers (
                passenger_id BIGINT AUTO_INCREMENT PRIMARY KEY,
                booking_id BIGINT NOT NULL,
                passenger_name VARCHAR(70) NOT NULL,
                age TINYINT UNSIGNED NOT NULL,
                gender ENUM('Male','Female','Other','Prefer not to say') NOT NULL DEFAULT 'Prefer not to say',
                CONSTRAINT fk_passenger_booking FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE,
                CHECK (age BETWEEN 1 AND 120), INDEX idx_passenger_booking (booking_id)
            ) ENGINE=InnoDB""",
        ]
        for statement in statements:
            cursor.execute(statement)
        trains = [
            ('12951', 'Mumbai Rajdhani Express', 'Mumbai', 'Delhi', '16:35:00', '08:35:00', '16h 00m', 100, 1850.00),
            ('12127', 'Intercity Express', 'Mumbai', 'Pune', '06:40:00', '10:05:00', '3h 25m', 100, 420.00),
            ('11010', 'Deccan Queen', 'Pune', 'Mumbai', '07:15:00', '10:25:00', '3h 10m', 100, 390.00),
            ('12902', 'Gujarat Mail', 'Mumbai', 'Ahmedabad', '22:00:00', '06:20:00', '8h 20m', 100, 760.00),
            ('12702', 'Hussain Sagar Express', 'Hyderabad', 'Bengaluru', '16:45:00', '06:10:00', '13h 25m', 100, 950.00),
            ('12028', 'Shatabdi Express', 'Bengaluru', 'Hyderabad', '06:00:00', '13:10:00', '7h 10m', 100, 1100.00),
            ('12958', 'Swarn Jayanti Express', 'Ahmedabad', 'Delhi', '18:50:00', '08:15:00', '13h 25m', 100, 1320.00),
        ]
        cursor.executemany("""INSERT INTO trains
            (train_number, train_name, source_station, destination_station, departure_time, arrival_time, duration, total_seats, fare)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE train_name=VALUES(train_name)""", trains)
        cursor.execute("SELECT train_id, total_seats FROM trains")
        train_rows = cursor.fetchall()
        today = date.today()
        for train_id, total_seats in train_rows:
            schedules = [(train_id, today + timedelta(days=i), total_seats) for i in range(15)]
            cursor.executemany("""INSERT IGNORE INTO train_schedules (train_id, journey_date, available_seats)
                VALUES (%s,%s,%s)""", schedules)
        conn.commit()
        cursor.close()
    finally:
        conn.close()


@app.before_request
def ensure_database_ready():
    if not app.config["DB_INITIALIZED"]:
        try:
            initialize_database()
            app.config["DB_INITIALIZED"] = True
        except Error:
            app.logger.exception("Automatic database setup failed; check database variables and connectivity.")
            # Allow the route to respond with its normal database error if it has one.


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def make_pnr(cursor):
    alphabet = string.ascii_uppercase + string.digits
    for _ in range(10):
        pnr = "RG" + "".join(secrets.choice(alphabet) for _ in range(8))
        cursor.execute("SELECT booking_id FROM bookings WHERE pnr_number = %s", (pnr,))
        if cursor.fetchone() is None:
            return pnr
    raise RuntimeError("Could not generate a unique PNR. Please try again.")


@app.route("/")
def index():
    return render_template("index.html", today=date.today().isoformat())


@app.route("/api/trains")
def search_trains():
    source = request.args.get("source", "").strip()
    destination = request.args.get("destination", "").strip()
    journey_date = request.args.get("date", "").strip()

    if not source or not destination or not journey_date:
        return jsonify({"error": "Source, destination and journey date are required."}), 400
    if source.casefold() == destination.casefold():
        return jsonify({"error": "Choose two different stations."}), 400
    try:
        date.fromisoformat(journey_date)
    except ValueError:
        return jsonify({"error": "Please provide a valid journey date."}), 400

    conn = get_db()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT t.train_id, t.train_number, t.train_name,
                   t.source_station, t.destination_station,
                   t.departure_time, t.arrival_time, t.duration,
                   t.fare, s.schedule_id, s.journey_date,
                   s.available_seats
            FROM trains t
            JOIN train_schedules s ON s.train_id = t.train_id
            WHERE LOWER(t.source_station) = LOWER(%s)
              AND LOWER(t.destination_station) = LOWER(%s)
              AND s.journey_date = %s
            ORDER BY t.departure_time
        """, (source, destination, journey_date))
        rows = cursor.fetchall()
        for row in rows:
            row["fare"] = float(row["fare"])
            row["journey_date"] = row["journey_date"].isoformat()
            row["departure_time"] = str(row["departure_time"])[:5]
            row["arrival_time"] = str(row["arrival_time"])[:5]
        return jsonify(rows)
    except Error:
        app.logger.exception("Train search failed")
        return jsonify({"error": "Database search failed. Check your MySQL setup and schema.sql."}), 500
    finally:
        conn.close()


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or len(password) < 8:
            flash("Enter your name and email. Password must be at least 8 characters.", "error")
            return render_template("auth.html", mode="register")
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (full_name, email, password_hash) VALUES (%s, %s, %s)",
                (name, email, generate_password_hash(password))
            )
            conn.commit()
            flash("Account created. You can now log in.", "success")
            return redirect(url_for("login"))
        except mysql.connector.IntegrityError:
            conn.rollback()
            flash("That email is already registered.", "error")
        except Error:
            conn.rollback()
            app.logger.exception("Registration failed")
            flash("Registration failed. Check your database configuration.", "error")
        finally:
            conn.close()
    return render_template("auth.html", mode="register")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        conn = get_db()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT user_id, full_name, email, password_hash FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            if user and check_password_hash(user["password_hash"], password):
                session.clear()
                session["user_id"] = user["user_id"]
                session["full_name"] = user["full_name"]
                flash("Welcome back!", "success")
                return redirect(url_for("index"))
            flash("Invalid email or password.", "error")
        except Error:
            app.logger.exception("Login failed")
            flash("Login failed. Check your database configuration.", "error")
        finally:
            conn.close()
    return render_template("auth.html", mode="login")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


@app.route("/api/bookings", methods=["GET"])
@login_required
def my_bookings():
    conn = get_db()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT b.booking_id, b.pnr_number, b.booking_status, b.number_of_passengers,
                   b.total_fare, b.booking_date, s.journey_date,
                   t.train_number, t.train_name, t.source_station, t.destination_station
            FROM bookings b
            JOIN train_schedules s ON s.schedule_id = b.schedule_id
            JOIN trains t ON t.train_id = s.train_id
            WHERE b.user_id = %s
            ORDER BY b.booking_date DESC
        """, (session["user_id"],))
        rows = cursor.fetchall()
        for row in rows:
            row["total_fare"] = float(row["total_fare"])
            row["booking_date"] = row["booking_date"].isoformat()
            row["journey_date"] = row["journey_date"].isoformat()
            row["booking_status"] = row["booking_status"]
        return jsonify(rows)
    except Error:
        app.logger.exception("Booking history failed")
        return jsonify({"error": "Could not load bookings."}), 500
    finally:
        conn.close()


@app.route("/api/bookings", methods=["POST"])
@login_required
def create_booking():
    data = request.get_json(silent=True) or {}
    try:
        schedule_id = int(data.get("schedule_id"))
        passenger_count = int(data.get("passenger_count", 1))
        passengers = data.get("passengers", [])
        if passenger_count < 1 or passenger_count > 6 or len(passengers) != passenger_count:
            return jsonify({"error": "Choose 1–6 passengers and provide each passenger's details."}), 400
        clean_passengers = []
        for p in passengers:
            name = str(p.get("name", "")).strip()
            age = int(p.get("age", 0))
            gender = str(p.get("gender", "Prefer not to say"))
            if not name or len(name) > 70 or age < 1 or age > 120:
                return jsonify({"error": "Every passenger needs a valid name and age (1–120)."}), 400
            if gender not in ("Male", "Female", "Other", "Prefer not to say"):
                gender = "Prefer not to say"
            clean_passengers.append((name, age, gender))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid booking details."}), 400

    conn = get_db()
    try:
        conn.start_transaction()
        cursor = conn.cursor(dictionary=True)
        # Lock the schedule row so simultaneous bookings cannot oversell its remaining seats.
        cursor.execute("""
            SELECT s.schedule_id, s.available_seats, t.fare, t.train_name,
                   t.source_station, t.destination_station, s.journey_date
            FROM train_schedules s
            JOIN trains t ON t.train_id = s.train_id
            WHERE s.schedule_id = %s
            FOR UPDATE
        """, (schedule_id,))
        schedule = cursor.fetchone()
        if not schedule:
            conn.rollback()
            return jsonify({"error": "This train schedule was not found."}), 404
        if schedule["journey_date"] < date.today():
            conn.rollback()
            return jsonify({"error": "You cannot book a journey in the past."}), 400
        if schedule["available_seats"] < passenger_count:
            conn.rollback()
            return jsonify({"error": "Not enough seats remain for this booking."}), 409

        pnr = make_pnr(cursor)
        total_fare = schedule["fare"] * passenger_count
        cursor.execute("""
            INSERT INTO bookings
                (pnr_number, user_id, schedule_id, number_of_passengers, total_fare, booking_status)
            VALUES (%s, %s, %s, %s, %s, 'CONFIRMED')
        """, (pnr, session["user_id"], schedule_id, passenger_count, total_fare))
        booking_id = cursor.lastrowid
        for name, age, gender in clean_passengers:
            cursor.execute("""
                INSERT INTO passengers (booking_id, passenger_name, age, gender)
                VALUES (%s, %s, %s, %s)
            """, (booking_id, name, age, gender))
        cursor.execute("""
            UPDATE train_schedules
            SET available_seats = available_seats - %s
            WHERE schedule_id = %s
        """, (passenger_count, schedule_id))
        conn.commit()
        return jsonify({
            "message": "Booking confirmed.",
            "pnr": pnr,
            "train_name": schedule["train_name"],
            "source_station": schedule["source_station"],
            "destination_station": schedule["destination_station"],
            "journey_date": schedule["journey_date"].isoformat(),
            "passenger_count": passenger_count,
            "total_fare": float(total_fare)
        }), 201
    except Error:
        conn.rollback()
        app.logger.exception("Booking transaction failed")
        return jsonify({"error": "Booking failed. No seats were deducted; check server logs."}), 500
    finally:
        conn.close()


@app.route("/api/bookings/<int:booking_id>/cancel", methods=["POST"])
@login_required
def cancel_booking(booking_id):
    conn = get_db()
    try:
        conn.start_transaction()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT b.booking_id, b.schedule_id, b.number_of_passengers, b.booking_status,
                   s.journey_date
            FROM bookings b
            JOIN train_schedules s ON s.schedule_id = b.schedule_id
            WHERE b.booking_id = %s AND b.user_id = %s
            FOR UPDATE
        """, (booking_id, session["user_id"]))
        booking = cursor.fetchone()
        if not booking:
            conn.rollback()
            return jsonify({"error": "Booking not found."}), 404
        if booking["booking_status"] != "CONFIRMED":
            conn.rollback()
            return jsonify({"error": "This booking is already cancelled."}), 409
        cursor.execute("UPDATE bookings SET booking_status = 'CANCELLED' WHERE booking_id = %s", (booking_id,))
        cursor.execute("""
            UPDATE train_schedules
            SET available_seats = available_seats + %s
            WHERE schedule_id = %s
        """, (booking["number_of_passengers"], booking["schedule_id"]))
        conn.commit()
        return jsonify({"message": "Booking cancelled and seats restored."})
    except Error:
        conn.rollback()
        app.logger.exception("Cancellation transaction failed")
        return jsonify({"error": "Cancellation failed."}), 500
    finally:
        conn.close()


@app.route("/health")
def health():
    try:
        conn = get_db()
        conn.close()
        return jsonify({"status": "ok", "database": "connected"})
    except Error:
        return jsonify({"status": "error", "database": "not connected"}), 500


if __name__ == "__main__":
    # Debug mode is suitable only for local development.
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
