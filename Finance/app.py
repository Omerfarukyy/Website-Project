import os

from datetime import datetime
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd


def num_there(s):
    return any(i.isdigit() for i in s)


now = datetime.now()

app = Flask(__name__)

app.jinja_env.filters["usd"] = usd

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):

    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    for ses in session["user_id"]:
        abc = ses["id"]
    usernames = db.execute("Select username FROM users WHERE id=?;", abc)
    for username in usernames:
        user = username["username"]
    rows = db.execute("SELECT * FROM owned Where username=? ", user)
    row1 = db.execute("SELECT cash FROM users where username=?", user)
    for column in row1:
        cash = column["cash"]
    total = 0
    for column in rows:
        x = lookup(column["o_symbol"])
        db.execute("UPDATE owned SET current_price0 =? where o_symbol=?", float(x["price"]), x["symbol"])
        total = float(column["o_stock"]) * float(x["price"]) + float(total)
        if x is None:
            return render_template("index.html")

    return render_template("index.html", cash=cash, rows=rows, total=total)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
        quotes = lookup(symbol)
        if not request.form.get("symbol"):
            return apology("must provide a symbol", 403)
        if not request.form.get("shares") or int(shares) < 1:
            return apology("must provide valid share number", 403)
        if quotes is None:
            return apology("must enter valid symbol", 403)
        for quote in quotes:
            symbol_price = float(quotes["price"])
            symbol_name = quotes["name"]

        for ses in session["user_id"]:
            abc = ses["id"]
        usernames = db.execute("Select username FROM users WHERE id=?;", abc)
        for username in usernames:
            user = username["username"]
        cash = db.execute("SELECT cash FROM users WHERE username =?;", user)
        if cash[0]["cash"] - symbol_price * int(shares) < 0:
            return apology("not enough money")
        db.execute("INSERT INTO trades(username,symbol,symbol_prices,how_many,date) VALUES(?,?,?,?,?)",
                   user, symbol, symbol_price, shares, now)
        db.execute("UPDATE users SET cash = cash-? WHERE username =?;", symbol_price*int(shares), user)
        db.execute("INSERT INTO owned (username,o_stock,o_symbol,o_symbol_name,current_price0) VALUES (?,?,?,?,?);",
                   user, shares, symbol, symbol_name, symbol_price)

        return redirect("/")

    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    for ses in session["user_id"]:
        abc = ses["id"]
    usernames = db.execute("Select username FROM users WHERE id=?;", abc)
    for username in usernames:
        user = username["username"]
    trades = db.execute("SELECT * from trades where username=?", user)
    return render_template("history.html", trades=trades)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    session.clear()

    if request.method == "POST":
       
        if not request.form.get("username"):
            return apology("must provide username", 403)

        elif not request.form.get("password"):
            return apology("must provide password", 403)

        rows = db.execute("SELECT * FROM users WHERE username = ?;", request.form.get("username"))

        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        session["user_id"] = rows[0]["id"]

        return redirect("/")

    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    session.clear()

    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():

    if request.method == "POST":
        symbol = request.form.get("symbol")
        quote = lookup(symbol)
        if quote is not None:
            return render_template("quoted.html",
                                   name=quote["name"], symbol=quote["symbol"], price=quote["price"])
        else:
            return apology("Invalid Symbol")

    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        if not request.form.get("username"):
            return apology("must provide username", 403)
        elif not request.form.get("password"):
            return apology("must provide password", 403)
        elif not request.form.get("confirmation"):
            return apology("must provide confirmation password", 403)
        users = db.execute("SELECT username FROM users")
        for user in users:
            if user["username"] == username:
                return apology("The username is already taken")
        if not num_there(password):
            return apology("Password must contain a number")
        if not any(not c.isalnum() for c in password):
            return apology("Password must contain a Special character")
        if password != confirmation:
            return apology("Password and confirmation is not the same")

        hash = generate_password_hash(password)
        db.execute("INSERT INTO users (username,hash) VALUES (?,?);", username, hash)
        session["user_id"] = db.execute("SELECT id FROM users WHERE username=?;", username)
        return redirect("/")

    else:

        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    for ses in session["user_id"]:
        abc = ses["id"]
    usernames = db.execute("Select username FROM users WHERE id=?;", abc)
    for username in usernames:
        user = username["username"]
    rows = db.execute("SELECT DISTINCT o_symbol from owned where username=?", user)

    if request.method == "POST":
        shares = request.form.get("shares")
        sym = request.form.get("symbol")
        try:
            shares = int(shares)
        except (ValueError, TypeError, SyntaxError, KeyError):
            return apology("Invalid value for shares")
        if shares <= 0:
            return apology("Too few shares")
        count = 0
        for row in rows:
            if sym == row["o_symbol"]:
                count += 1

        if count == 0:
            return apology("You dont have the symbol")
        o_stocks = db.execute("Select o_stock from owned where username =? and o_symbol =? ", user, sym)
        if shares > int(o_stocks[0]["o_stock"]):
            return apology("too many shares")
        if shares == int(o_stocks[0]["o_stock"]):
            symbol = lookup(sym)
            symbbol = symbol["symbol"]
            symbol = int(symbol["price"])
            db.execute("INSERT INTO trades(username,symbol,symbol_prices,how_many,date) VALUES(?,?,?,?,?)",
                       user, symbbol, symbol, -shares, now)
            db.execute("UPDATE users SET cash=cash+? where username =?", symbol*shares, user)
            db.execute("DELETE FROM owned where username =? and o_symbol=?", user, sym)
        elif shares < int(o_stocks[0]["o_stock"]):
            symbol = lookup(sym)
            symbbol = symbol["symbol"]
            symbol = int(symbol["price"])
            db.execute("INSERT INTO trades(username,symbol,symbol_prices,how_many,date) VALUES(?,?,?,?,?)",
                       user, symbbol, symbol, -shares, now)
            db.execute("UPDATE users SET cash=cash+? where username =?", symbol*shares, user)
            db.execute("UPDATE owned SET o_stock=o_stock-? where username =? and o_symbol=?",
                       shares, user, sym)
        return redirect("/")

    else:
        return render_template("sell.html", rows=rows)
