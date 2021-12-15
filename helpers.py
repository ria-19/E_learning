import os
import requests
import urllib.parse

from flask import redirect, render_template, request, session
from functools import wraps


def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def lookup(val="python+java"):
    """Look up most starred repo of topics."""
    
    # Contact API
    try:
        url = f"https://api.github.com/search/repositories?q=language:{val}&sort=stars"
        headers = {'Accept': 'application/vnd.github.v3+json'}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.RequestException:
        return None

    # Parse response
    res = []
    try: 
        response_dict = response.json()
        if response_dict["total_count"] >= 12:
            search = response_dict["items"][:12]
        else:
            search = response_dict["items"]
        for item in search:
            result= {}
            result["name"] = item["name"].capitalize()
            result["pic"] = item["owner"]["avatar_url"]
            result["url"] = item["html_url"]
            result["des"] = item["description"][:80].capitalize() + "..."
            result["stars"] = item["stargazers_count"]
            result["owner_usr"] = item["owner"]["login"]
            res.append(result)
    except (KeyError, TypeError, ValueError):
        return None

    if len(res) == 0:
        return None
    return res




