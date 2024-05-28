import os
from os.path import join, dirname
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime, timedelta
import jwt
import hashlib
from flask import (
    Flask,
    render_template,
    jsonify,
    request,
    redirect,
    url_for,
)
from werkzeug.utils import secure_filename

app=Flask(__name__)

app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['UPLOAD_FOLDER'] = './static/profile_pics'

SECRET_KEY = 'SPARTA'
TOKEN_KEY = 'mytoken'

client=MongoClient('mongodb+srv://Aryama:1234@cluster0.9x3eatx.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
db=client.dbPPA

app = Flask(__name__)

@app.route("/")
def home():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.users.find_one({"username": payload["id"]})
        return render_template("index.html", user_info=user_info)
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="Your token has expired"))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="There was problem logging you in"))


@app.route("/login")
def login():
    msg = request.args.get("msg")
    return render_template("login.html", msg=msg)


@app.route("/user/<username>")
def user(username):
    # an endpoint for retrieving a user's profile information
    # and all of their posts
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        # if this is my own profile, True
        # if this is somebody else's profile, False
        status = username == payload["id"]

        user_info = db.users.find_one({"username": username}, {"_id": False})
        return render_template("user.html", user_info=user_info, status=status)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))


@app.route("/sign_in", methods=["POST"])
def sign_in():
    # Sign in
    username_receive = request.form["username_give"]
    password_receive = request.form["password_give"]
    pw_hash = hashlib.sha256(password_receive.encode("utf-8")).hexdigest()
    print(username_receive, pw_hash)
    result = db.users.find_one(
        {
            "username": username_receive,
            "password": pw_hash,
        }
    )
    if result:
        payload = {
            "id": username_receive,
            # the token will be valid for 24 hours
            "exp": datetime.utcnow() + timedelta(seconds=60 * 60 * 24),
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

        return jsonify(
            {
                "result": "success",
                "token": token,
            }
        )
    # Let's also handle the case where the id and
    # password combination cannot be found
    else:
        return jsonify(
            {
                "result": "fail",
                "msg": "We could not find a user with that id/password combination",
            }
        )


@app.route("/sign_up/save", methods=["POST"])
def sign_up():
    username_receive = request.form["username_give"]
    password_receive = request.form["password_give"]
    password_hash = hashlib.sha256(password_receive.encode("utf-8")).hexdigest()
    doc = {
        "username": username_receive,  # id
        "password": password_hash,  # password
        "profile_name": username_receive,  # user's name is set to their id by default
        "profile_pic": "",  # profile image file name
        "profile_pic_real": "profile_pics/profile_placeholder.png",  # a default profile image
        "profile_info": "",  # a profile description
    }
    db.users.insert_one(doc)
    return jsonify({"result": "success"})


@app.route("/sign_up/check_dup", methods=["POST"])
def check_dup():
    # ID we should check whether or not the id is already taken
    username_receive = request.form["username_give"]
    exists = bool(db.users.find_one({"username": username_receive}))
    return jsonify({"result": "success", "exists": exists})

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)   