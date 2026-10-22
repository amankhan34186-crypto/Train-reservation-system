# RailWayGo — Train Reservation System (Flask + MySQL)

A second-year BTech AIDS DBMS mini-project. This version connects the website to a real MySQL database through Python Flask.

**Important:** All train names, fares, schedules and seats are sample data for a college demonstration. This is not connected to Indian Railways, live train information, or payment services.

## Features
- Train search by source, destination and journey date, backed by MySQL
- User registration/login with password hashing
- Booking one to six passengers, with generated PNR
- My Bookings page
- Cancellation, with seat restoration
- Database transactions and row locking to reduce overselling
- Parameterized SQL queries
- MySQL foreign keys, unique constraints and indexes

## Requirements
- Python 3.10 or later
- MySQL Server 8.x (or compatible MySQL server)
- VS Code (recommended)

## 1. Create the database
1. Start your MySQL server.
2. Open MySQL Workbench and connect to your local server.
3. Open `schema.sql` and execute the whole script.
4. It creates `railway_reservation`, the tables, sample trains and demo schedules for today through the next 14 days.

If MySQL Workbench reports that a `CREATE PROCEDURE` or `DELIMITER` command cannot be run in the selected execution mode, execute the entire script as a script (not statement-by-statement), or run the procedure section in the MySQL command-line client.

## 2. Install Python dependencies
Open a terminal in this project folder:

### Windows
```powershell
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### macOS / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. Set your MySQL credentials
Set environment variables in the same terminal where you run Flask.

### Windows PowerShell
```powershell
$env:DB_HOST="localhost"
$env:DB_USER="root"
$env:DB_PASSWORD="YOUR_MYSQL_PASSWORD"
$env:DB_NAME="railway_reservation"
$env:FLASK_SECRET_KEY="replace-with-a-long-random-secret"
```

### macOS / Linux
```bash
export DB_HOST="localhost"
export DB_USER="root"
export DB_PASSWORD="YOUR_MYSQL_PASSWORD"
export DB_NAME="railway_reservation"
export FLASK_SECRET_KEY="replace-with-a-long-random-secret"
```

If your MySQL root account has no password on your local lab machine, set `DB_PASSWORD` to an empty string. Prefer a dedicated MySQL project user for better security.

## 4. Run the application
```bash
python app.py
```
Open **http://127.0.0.1:5000** in your browser.

To check the database connection, visit **http://127.0.0.1:5000/health**. A healthy connection returns `{"status":"ok","database":"connected"}`.

## 5. Demonstrate it
1. Open Register and create an account.
2. Log in.
3. Search a route, such as Mumbai → Pune, and choose a journey date between today and the next 14 days.
4. Click Book ticket and enter passenger details.
5. Show the generated PNR and total fare.
6. Open My Bookings and cancel the demo ticket.
7. Search again to show that available seats were restored.

## Troubleshooting
- **Can't connect to MySQL:** confirm MySQL Server is running and credentials are correct.
- **Unknown database:** execute `schema.sql` in MySQL Workbench.
- **No trains found:** sample schedules are seeded for today through 14 days; choose one of those dates and a route present in `trains`.
- **mysql.connector not found:** activate the virtual environment and run `pip install -r requirements.txt`.
- **Port 5000 busy:** stop the other app using it or change the port at the bottom of `app.py`.

## DBMS concepts for viva
- **Primary key:** uniquely identifies each row.
- **Foreign key:** links bookings to users/schedules and passengers to bookings.
- **Normalization:** separates user, train, schedule, booking and passenger facts into related tables.
- **JOIN:** combines train, schedule and booking details for results.
- **Transaction:** booking inserts records and decrements seats together; on error, rollback prevents partial booking.
- **Row lock (`FOR UPDATE`):** serializes competing bookings for the same schedule.
- **Parameterized query:** uses `%s` placeholders to reduce SQL injection risk.

## Limitations
This is a local learning project. It has no live train data, payment gateway, email/SMS notifications, real seat/coach assignment, waitlist, or production-grade admin panel. Flask debug mode is enabled for local development only; do not deploy this configuration publicly.
