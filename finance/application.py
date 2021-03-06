# HELLO
import os

from datetime import datetime

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session  # type: ignore
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd  # type: ignore

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    cash = db.execute("SELECT cash FROM users WHERE id=?", session["user_id"])
    temp = cash[0]["cash"]
    cash = temp
    return render_template("index.html", cash=cash)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "GET":
        return render_template("buy.html")
    stock = lookup(request.form.get("stock"))
    if stock == None:
        return apology("Please enter valid stock name", 403)
    stock_symbol = stock["symbol"]
    company_name = stock["name"]
    stock_price = float(stock["price"])
    qty = float(request.form.get("qty"))  # type: ignore
    shares = qty*stock_price
    cash = db.execute(
        "SELECT cash FROM users WHERE id = ?", session["user_id"])
    temp = float(cash[0]["cash"])  # type: ignore
    cash = temp
    user = int(session["user_id"])

    if cash >= shares:
        db.execute(
            "INSERT INTO txn (stock_name, company_name, qty, user_id, price, time) VALUES(?,?,?,?,?,?)", stock_symbol, company_name, qty, user, shares, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        cash -= shares
        db.execute("UPDATE users SET cash = ? WHERE id=?", cash, user)
    else:
        return apology("not enough funds", 403)

    return render_template("buy.html", qty=qty, company_name=company_name, shares=shares)


@ app.route("/history")
@ login_required
def history():
    """Show history of transactions"""
    stocks = db.execute(
        "SELECT txn_id, company_name, stock_name, qty, price, time FROM txn WHERE user_id=?", session["user_id"])

    return render_template("history.html", history=history, stocks=stocks)


@ app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?",
                          request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"],  # type: ignore
                                                     request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]  # type: ignore
        session["user_name"] = rows[0]["username"]  # type: ignore

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@ app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@ app.route("/quote", methods=["GET", "POST"])
@ login_required
def quote():
    """Get stock quote."""
    if request.method == "GET":
        return render_template("quote.html")
    stock = lookup(request.form.get("stock"))
    if stock == None:
        return apology("no stock found", 403)
    return render_template("quote.html", stock_symbol=stock["symbol"], stock_name=stock["name"], stock_price=stock["price"])


@ app.route("/register", methods=["GET", "POST"])  # type: ignore
def register():
    if request.method == "GET":
        return render_template("register.html")
    if request.method == "POST":
        if not request.form.get("username"):
            return apology("Please provide username", 403)
        if not request.form.get("password"):
            return apology("Please provide password", 403)
        if request.form.get("password") != request.form.get("confirm_password"):
            return apology("Passwords don't match", 403)
        username = request.form.get("username")
        password_hash = generate_password_hash(request.form.get("password"))

        check = len(db.execute(  # type: ignore
            "SELECT username FROM users WHERE username=?", username))

        if check == 0:
            db.execute("INSERT INTO users (username,hash) VALUES(?, ?)",
                       username, password_hash)
            return index()
        else:
            return apology("username already exists", 403)


@ app.route("/sell", methods=["GET", "POST"])
@ login_required
def sell():
    """Sell shares of stock"""
    cash = db.execute(
        "SELECT cash FROM users WHERE id = ?", session["user_id"])
    temp = float(cash[0]["cash"])  # type: ignore
    cash = temp
    user = int(session["user_id"])
    stocks = db.execute(
        "SELECT * FROM txn WHERE user_id=?", user)
    stock_dict = db.execute(
        "SELECT DISTINCT stock_name FROM txn WHERE user_id=?", user)

    # Create a list of stocks the user owns
    stock_list = []
    stock_qty = {}
    for x in stock_dict:  # type: ignore
        stock_list.append(x["stock_name"])

    for x in stock_list:
        for y in stocks:  # type: ignore
            if x == y["stock_name"]:
                if x in stock_qty:
                    stock_qty[x] += y["qty"]
                else:
                    stock_qty[x] = y["qty"]

    if request.method == "GET":
        return render_template("sell.html", stock_qty=stock_qty, stock_dict=stock_dict, x=stock_qty)

    stock = lookup(request.form.get("stock"))

    if stock == None:
        return apology("Please enter valid stock name", 403)

    stock_symbol = stock["symbol"]
    company_name = stock["name"]
    stock_price = float(stock["price"])
    qty = float(request.form.get("qty"))  # type: ignore
    shares = qty*stock_price

    if qty > stock_qty[stock_symbol] or qty <= 0:
        return apology("you don't own enough of this share", 403)

    cash += shares
    qty *= -1
    shares *= -1

    db.execute(
        "INSERT INTO txn (stock_name, company_name, qty, user_id, price, time) VALUES(?,?,?,?,?,?)", stock_symbol, company_name, qty, user, shares, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    db.execute("UPDATE users SET cash=? WHERE id=?", cash, user)
    return render_template("sell.html", qty=qty, company_name=company_name, shares=shares, stock_qty=stock_qty)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
