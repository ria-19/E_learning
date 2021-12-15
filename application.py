import urllib.parse
from flask import Flask, flash, redirect, render_template, request, session
# from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, login_required, lookup
from dbconnect import connection
from flask_mail import Mail, Message
from werkzeug.datastructures import ImmutableOrderedMultiDict
import requests
import time


# Configure application
app = Flask(__name__)
app.secret_key = "SECRET KEY"

app.config.update(
      DEBUG=True,
      #EMAIL SETTINGS
      MAIL_SERVER='smtp.gmail.com',
      MAIL_PORT=465,
      MAIL_USE_SSL=True,
      MAIL_USERNAME = "EMAIL",
      MAIL_PASSWORD = "PASSWORD"
      )

mail = Mail(app)


# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Configure session to use filesystem (instead of signed cookies)
# app.config["SESSION_FILE_DIR"] = mkdtemp()
# app.config["SESSION_PERMANENT"] = False
# app.config["SESSION_TYPE"] = "filesystem"
# Session(app)


@app.route("/")
def home():
    """Show treading tech topics on Github as Home Page"""

    home_result = []
    home_result = lookup()[:8]
    return render_template("home.html", result=home_result)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":

        equal = request.form.get("password") == request.form.get("confirm_password")

        # Connect to database
        c, conn = connection()

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure email was submitted
        if not request.form.get("email"):
            return apology("must provide username", 403)

        # Ensure password and confirm password were submitted  and are equal
        elif not request.form.get("password") or not request.form.get("confirm_password") or not equal:
            return apology("must provide password", 403)
        
        username = request.form.get("username")
        hash = str(generate_password_hash(request.form.get("password")))
        email = request.form.get("password")

    
        # Check if username already exists
        sql = "SELECT * FROM `users` WHERE `username`=%s"
        c.execute(sql,(username,))
        rows = c.fetchall()
        if len(rows) == 1:
            return apology("username already taken", 403)

        # Store new user's data into database 
        sql = "INSERT INTO `users` (`username`, `password`, `email`) VALUES (%s, %s, %s)"
        c.execute(sql, (username, hash, email))
        conn.commit()

        # Flash user message
        flash("Registered!")

        # Extract user'id to login
        sql = "SELECT * FROM `users` WHERE `username`=%s"
        c.execute(sql,(username,))
        rows = c.fetchall()

        # Log user in and redirect to "/"
        session["user_id"] = rows[0]["uid"]
        session["username"] = rows[0]["username"]

        conn.close()
        return redirect("/")

    else:
        return render_template("register.html")

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
        c, conn  = connection()
        sql = "SELECT * FROM `users` WHERE `username`=%s"
        c.execute(sql, (request.form.get("username"),))
        rows = c.fetchall()
        conn.close()

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["password"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["uid"]
        session["username"] = rows[0]["username"]

        # Redirect user to home page
        return redirect("/collection")

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

@app.route("/collection")
@login_required
def collection():
    """Show user's collection of repositories."""

    # Connect to database to query for required information to display
    c, conn = connection() 

    # Query database of user's all repo order in alphabetical order
    sql = "SELECT * FROM `collection` WHERE `uid`=%s ORDER BY `name`"
    c.execute(sql, (session["user_id"],))
    rows = c.fetchall()

    empty = False
    if len(rows) == 0:
        empty = True

    conn.close()
    return render_template("collection.html", rows=rows, empty=empty)



@app.route("/add", methods=["POST"])
@login_required
def add():
    """ Add repo to user's collection"""

    # Connect to database to query for required information to display
    c, conn = connection() 

    name = request.form.get('name')
    url = request.form.get('url')
    des = request.form.get('des')
    
    # Insert repo to user's collection
    sql = "INSERT INTO `collection` (`uid`, `name`, `url`, `des`) VALUES (%s, %s, %s, %s)"
    c.execute(sql, (session["user_id"], name, url, des))
    conn.commit()

   # Flash user message
    flash("Added to collection!")
    
    conn.close()
    return redirect("/collection")


@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    """Search of the repositories."""

    if request.method == "POST":

        # Ensure symbol was submitted
        if not request.form.get("topic"):
            return apology("must provide topic name", 403)

        # Quote the string to be used as a search query
        safe_query = urllib.parse.quote_plus(request.form.get("topic"))

        # Search for repos on this topic using GitHub API
        res = lookup(safe_query)

        # Ensure their query was valid and have results
        if not res:
            return apology("Please provide valid topic name", 403)
        
        # Flash user message
        msg = "Most starred repositories on " + request.form.get("topic").capitalize() + "!"
        flash(msg)

        # Show them most starred repos max 10 on their queried topic.
        return render_template("results.html", result=res)  

    else:
        return render_template("search.html")


@app.route("/remove", methods=["POST"])
@login_required
def remove():
    """Remove repos from the collection"""

    # Connect to database
    c, conn = connection() 

    rid = int(request.form.get("rid"))
        
    # Query for repo that user want to remove
    sql = "DELETE FROM `collection` WHERE `uid`=%s AND `rid`=%s"
    c.execute(sql, (session["user_id"], rid))
    conn.commit()

    conn.close()
    return redirect("/collection")

    
@app.route("/change_password", methods=["GET", "POST"])
def change_password():
    """ Change password """

    # User reached route via GET
    if request.method == "GET":
        return render_template("change_password.html")
        
    else:
        # User reached route via POST (as by submitting a form via POST)
        if request.method == "POST":

            # Ensure username was submitted
            if not request.form.get("username"):
                return apology("must provide username", 403)

            # Ensure new password was submitted
            elif not request.form.get("newpassword"):
                return apology("must provide new password", 403)

            # Ensure password was submitted
            elif not request.form.get("password"):
                return apology("must provide password", 403)

            # Query database for username
            c, conn = connection()
            sql = "SELECT * FROM `users` WHERE `username`=%s"
            c.execute(sql, (request.form.get("username"),))
            rows = c.fetchall()

            # Ensure username exists and password is correct
            if len(rows) != 1 or not check_password_hash(rows[0]["password"], request.form.get("password")):
                return apology("invalid username and/or password", 403)

            username = request.form.get("username")
            hash = generate_password_hash(request.form.get("newpassword"))

            # Store new password into database 
            sql = "UPDATE `users` SET `password`=%s WHERE `username`=%s"
            c.execute(sql, (hash, username))
            conn.commit()

            # Flash user message
            flash("Your password is changed!")

            # Redirect user to home page
            return redirect("/")

@app.route('/ipn',methods=['POST'])
def ipn():
	try:
		arg = ''
		request.parameter_storage_class = ImmutableOrderedMultiDict
		values = request.form
		for x, y in values.iteritems():
			arg += "&{x}={y}".format(x=x,y=y)

		validate_url = 'https://www.sandbox.paypal.com' \
					   '/cgi-bin/webscr?cmd=_notify-validate{arg}' \
					   .format(arg=arg)
		r = requests.get(validate_url)
		if r.text == 'VERIFIED':
			try:
				payer_email =  request.form.get('payer_email')
				unix = int(time.time())
				payment_date = request.form.get('payment_date')
				username = request.form.get('custom')
				last_name = request.form.get('last_name')
				payment_gross = (request.form.get('payment_gross'))
				payment_fee = (request.form.get('payment_fee'))
				payment_net = float(payment_gross) - float(payment_fee)
				payment_status = (request.form.get('payment_status'))
				txn_id = (request.form.get('txn_id'))
			except Exception as e:
				with open('/tmp/ipnout.txt','a') as f:
					data = 'ERROR WITH IPN DATA\n'+str(values)+'\n'
					f.write(data)
			
			with open('/tmp/ipnout.txt','a') as f:
				data = 'SUCCESS\n'+str(values)+'\n'
				f.write(data)

			c,conn = connection()
			c.execute("INSERT INTO ipn (unix, payment_date, username, last_name, payment_gross, payment_fee, payment_net, payment_status, txn_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
						(unix, payment_date, username, last_name, payment_gross, payment_fee, payment_net, payment_status, txn_id))
			conn.commit()
			c.close()
			conn.close()
			

		else:
			 with open('/tmp/ipnout.txt','a') as f:
				 data = 'FAILURE\n'+str(values)+'\n'
				 f.write(data)
				
		return r.text
	except Exception as e:
		return str(e)


@app.route("/support")
@login_required
def support():
    """Integrate paypal and mailing system"""
    return render_template("support.html")

@app.route('/success')
def success():

    # Query database for email
    c, conn  = connection()
    sql = "SELECT * FROM `users` WHERE `username`=%s"
    c.execute(sql, (session["username"],))
    rows = c.fetchall()
    conn.close()

    s_email = "Sender Email"
    r_email = rows[0]["email"]
            
    # Send thank you mail for the supports
    msg = Message("Thank you", sender=s_email,recipients=[r_email], body="Thank you for supporting our content! :)")
    mail.send(msg)

    # Flash user message
    mesg = "Thank you! " + session["username"]
    flash(mesg)
            
    return redirect("/")  
	
	
@app.route("/contact")
@login_required
def contact():
    """Contact form"""
    return render_template("contact.html")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
