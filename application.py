import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
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
app.jinja_env.filters["usd"] = usd

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


@app.route("/", methods=["GET"])
@login_required
def index():
    """Show portfolio of stocks"""
    print("get index")

    current_user = session.get("user_id")
    cash = db.execute("SELECT * FROM users WHERE id = ?", current_user)
    available_cash = cash[0]["cash"]
    share_value = db.execute("SELECT SUM (total) FROM purchased_stocks WHERE username_id = ?", current_user)
    stock_value = share_value[0]["SUM (total)"]
    if stock_value is None:
        total = available_cash
    else:
        total = stock_value + available_cash

    users_stocks = db.execute("SELECT stock, name, SUM(shares) as totalshares, purchase_value, total FROM purchased_stocks WHERE username_id = ? GROUP BY stock", current_user)


    return render_template("index.html", available_cash=available_cash, users_stocks=users_stocks, share_value=share_value, total=total)
    #return apology("TODO")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        print("post buy")
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")

        if not symbol:
            return apology("You have not entered a stock symbol", 400)

        if int(shares) <= 0:
            return apology("You must enter a positive number of shares")

        stock_data = lookup(symbol)
        print(stock_data)
        if stock_data is None:
            return apology("You have not entered a valid stock")

        username_id = session.get("user_id")
        stock_price = stock_data["price"]
        stock_name = stock_data["name"]
        stock_symbol = stock_data["symbol"]
        total_cost = int(shares) * stock_price
        row = db.execute("SELECT * FROM users WHERE id = ?", username_id)
        available_cash = row[0]["cash"]
        updated_cash = float(available_cash) - float(total_cost)
        buy="buy"

        if available_cash < total_cost:
            return apology("You do not have enough cash to make this purchase")

        db.execute ("UPDATE users SET cash = ? WHERE id = ?", updated_cash, username_id)
        db.execute ("INSERT INTO purchased_stocks (stock, shares, username_id, purchase_value, name, total, type) VALUES(?, ?, ?, ?, ?, ?, ?)", stock_symbol, shares, username_id, stock_price, stock_name, total_cost, buy)
        return redirect("/")

    else:
        print("get quote")
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    return apology("TODO")


@app.route("/login", methods=["GET", "POST"])
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
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        print("post quote")
        symbol = request.form.get("symbol")
        stock_data = lookup(symbol)
        if stock_data:
            return render_template("quoted.html", stock_data=stock_data)
        return apology("Stock does not exist")

    else:
        print("get quote")
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        # Ensure username was submitted
        print("post register")

        username = request.form.get("username")
        if not username:
            return apology("must enter username", 403)

        # Ensure password was submitted
        password = request.form.get("password")
        if not password:
            return apology("must enter password", 403)

        # Ensure password is repeated
        repeat_password = request.form.get("repeat_password")
        if not repeat_password:
            return apology("must enter password again", 403)

        if not repeat_password == password:
            return apology("passwords do not match", 403)

        rows = db.execute("SELECT * FROM users WHERE username = ?", username)
        if len(rows) == 1:
            return apology("Username already exists", 403)

        password_hash = generate_password_hash(password)

        db.execute ("INSERT INTO users (username, hash) VALUES(?, ?)", username, password_hash)

        #return apology("TODO")
        return redirect("/")

    else:
        print("get register")
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == "POST":
        current_user = session.get("user_id")
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
        stock_data=lookup(symbol)
        stock_name=stock_data["name"]

        symbols = db.execute("SELECT stock FROM purchased_stocks WHERE username_id = ?", current_user)
        total_shares_query=db.execute("SELECT SUM(shares) as totalshares FROM purchased_stocks WHERE username_id = ? AND stock = ? ", current_user, symbol)
        total_shares=total_shares_query[0]["totalshares"]

        i = 0;
        while i < len(symbols):
            available_symbols=symbols[i]["stock"]
            i+=1
            print(available_symbols)


        if symbol is None:
            return apology("You must select a stock", 400)

        if int(shares) < 1:
            return apology("You must enter a positive number of shares")

        if int(shares) > total_shares:
            return apology("You do not have enough shares")

        rows = db.execute("SELECT purchase_value FROM purchased_stocks WHERE stock = ?", symbol)
        price = rows[0]["purchase_value"]
        total_cost = int(shares) * price

        cash = db.execute("SELECT * FROM users WHERE id = ?", current_user)
        available_cash = cash[0]["cash"]
        updated_cash = float(available_cash) + float(total_cost)
        sold="sold"

        db.execute ("UPDATE users SET cash = ? WHERE id = ?", updated_cash, current_user)
        db.execute ("INSERT INTO purchased_stocks (stock, shares, username_id, purchase_value, name, total, type) VALUES(?, ?, ?, ?, ?, ?, ?)", symbol, shares, current_user, price, stock_name, total_cost, sold)

        return redirect("/")


    else:
        current_user = session.get("user_id")
        rows = db.execute("SELECT stock FROM purchased_stocks WHERE username_id = ? GROUP BY stock", current_user)
        print("get sell")
        return render_template("sell.html", rows=rows)



def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
