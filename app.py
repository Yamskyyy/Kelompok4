from flask import Flask, render_template, jsonify, request, redirect, url_for, send_file, flash
import os
from os.path import join, dirname
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime, timedelta
import jwt
import hashlib
import csv
from io import StringIO, BytesIO
from functools import wraps
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Load environment variables from a .env file
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

app = Flask(__name__)

app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['UPLOAD_FOLDER'] = './static/profile_pics'
app.secret_key = os.getenv('SECRET_KEY')

SECRET_KEY = os.getenv('SECRET_KEY')
TOKEN_KEY = os.getenv('TOKEN_KEY')
MONGO_URI = os.getenv('MONGO_URI')

client = MongoClient(MONGO_URI)
db = client.dbPPA

def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token_receive = request.cookies.get(TOKEN_KEY)
        if token_receive:
            try:
                payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
                user_info = db.expert_users.find_one({'username': payload.get('id')})
                if user_info:
                    return f(*args, **kwargs)
            except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
                pass
        flash("You do not have permission to access this page.", "danger")
        return redirect(url_for('home'))
    return decorated_function

def admin_or_user(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token_receive = request.cookies.get(TOKEN_KEY)
        if token_receive:
            try:
                payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
                user_info = db.normal_users.find_one({'username': payload.get('id')}) or db.expert_users.find_one({'username': payload.get('id')})
                if user_info:
                    return f(*args, **kwargs)
            except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
                pass
        flash("You do not have permission to access this page.", "danger")
        return redirect(url_for('home'))
    return decorated_function

@app.route('/financial_report', methods=['GET', 'POST'])
@admin_only
def financial_report():
    if request.method == 'POST':
        pemasukan = int(request.form['pemasukan'])
        pengeluaran = int(request.form['pengeluaran'])
        saldo = int(request.form['saldo'])
    else:
        # Data default, bisa diganti dengan data dari database jika ada
        pemasukan = 10431
        pengeluaran = 7061
        saldo = 291009

    return render_template('financial_report.html', pemasukan=pemasukan, pengeluaran=pengeluaran, saldo=saldo)

@app.route("/")
def home():
    token_receive = request.cookies.get(TOKEN_KEY)
    if token_receive:
        try:
            payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
            user_info = db.normal_users.find_one({'username': payload.get('id')})
            user_info2 = db.expert_users.find_one({'username': payload.get('id')})

            if user_info:
                return render_template('home.html', user_info=user_info)
            elif user_info2:
                return render_template('home2.html', user_info2=user_info2)
            else:
                return render_template('login.html')
        except jwt.ExpiredSignatureError:
            msg = 'Your token has expired'
            return redirect(url_for('login', msg=msg))
        except jwt.exceptions.DecodeError:
            msg = 'There was a problem logging you in'
            return redirect(url_for('login', msg=msg))
    else:
        return render_template('login.html')

@app.route("/login")
def login():
    token_receive = request.cookies.get(TOKEN_KEY)
    msg = request.args.get("msg")
    if msg:
        return render_template('login.html', msg=msg)
    else:
        if token_receive:
            try:
                payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
                user_info = db.normal_users.find_one({'username': payload.get('id')})
                user_info2 = db.expert_users.find_one({'username': payload.get('id')})
                
                if user_info:
                    return render_template('about.html', user_info=user_info)
                elif user_info2:
                    return render_template('contact.html', user_info2=user_info2)
                else:
                    return render_template('login.html')
                    
            except jwt.ExpiredSignatureError:
                msg = 'Your token has expired'
                return redirect(url_for('login', msg=msg))
            except jwt.exceptions.DecodeError:
                msg = 'There was a problem logging you in'
                return redirect(url_for('login', msg=msg))
        else:
            return render_template('login.html', msg=msg)

@app.route("/user/<username>")
def user(username):
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        status = username == payload["id"]

        user_info = db.users.find_one({"username": username}, {"_id": False})
        return render_template("user.html", user_info=user_info, status=status)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

@app.route("/sign_in", methods=["POST"])
def sign_in():
    username_receive = request.form["username_give"]
    password_receive = request.form["password_give"]
    pw_hash = hashlib.sha256(password_receive.encode("utf-8")).hexdigest()
    result = db.normal_users.find_one(
        {
            "username": username_receive,
            "password": pw_hash,
        }
    )
    result2 = db.expert_users.find_one(
        {
            "username": username_receive,
            "password": pw_hash,
        }
    )
    if result or result2:
        payload = {
            "id": username_receive,
            "exp": datetime.utcnow() + timedelta(seconds=60 * 60 * 24),
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
        response = jsonify({"result": "success", "token": token})
        response.set_cookie(TOKEN_KEY, token)
        return response
    else:
        return jsonify({"result": "fail", "msg": "We could not find a user with that id/password combination"})

@app.route("/sign_up/save", methods=["POST"])
def sign_up():
    username_receive = request.form["username_give"]
    password_receive = request.form["password_give"]
    role_receive = request.form["role_give"]
    password_hash = hashlib.sha256(password_receive.encode("utf-8")).hexdigest()
    if role_receive == 'expert':
        doc = {
            "username": username_receive,
            "password": password_hash,
            "profile_name": username_receive,
            "role": role_receive,
        }
        db.expert_users.insert_one(doc)
    elif role_receive == 'normal':
        doc = {
            "username": username_receive,
            "password": password_hash,
            "profile_name": username_receive,
            "role": role_receive,
        }
        db.normal_users.insert_one(doc)
    return jsonify({'result': 'success'})

@app.route("/sign_up/check_dup", methods=["POST"])
def check_dup():
    username_receive = request.form["username_give"]
    exists = bool(db.normal_users.find_one({'username': username_receive})) or bool(db.expert_users.find_one({'username': username_receive}))
    return jsonify({"result": "success", "exists": exists})

@app.route("/act", methods=["POST"])
def act_post():
    act_receive = request.form['act_give']
    count = db.act.count_documents({})
    num = count + 1
    doc = {
        'num': num,
        'act': act_receive,
        'done': 0,
    }
    db.act.insert_one(doc)
    return jsonify({'msg': 'Kegiatan Berhasil Ditambah!'})

@app.route("/act/done", methods=["POST"])
def act_done():
    num_receive = request.form['num_give']
    db.act.update_one({'num': int(num_receive)}, {'$set': {'done': 1}})
    return jsonify({'msg': 'Update Kegiatan Selesai!'})

@app.route("/delete", methods=["POST"])
def act_bucket():
    num_receive = request.form['num_give']
    db.act.delete_one({'num': int(num_receive)})
    return jsonify({'msg': 'delete success!'})

@app.route("/act", methods=["GET"])
def act_get():
    act_list = list(db.act.find({}, {'_id': False}))
    return jsonify({'acts': act_list})

@app.route("/act_week", methods=["POST"])
def act_week_post():
    act_week_receive = request.form['act_week_give']
    count = db.act_week.count_documents({})
    num = count + 1
    doc = {
        'num': num,
        'act_week': act_week_receive,
        'done': 0,
    }
    db.act_week.insert_one(doc)
    return jsonify({'msg': 'Rencana Minggu Ini Berhasil Ditambah!'})

@app.route("/act_week/done", methods=["POST"])
def act_week_done():
    num_receive = request.form['num_give']
    db.act_week.update_one({'num': int(num_receive)}, {'$set': {'done': 1}})
    return jsonify({'msg': 'Update Rencana Selesai!'})

@app.route("/delete_week", methods=["POST"])
def act_week_bucket():
    num_receive = request.form['num_give']
    db.act_week.delete_one({'num': int(num_receive)})
    return jsonify({'msg': 'delete success!'})

@app.route("/act_week", methods=["GET"])
def act_week_get():
    act_week_list = list(db.act_week.find({}, {'_id': False}))
    return jsonify({'acts_week': act_week_list})

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/about2')
def about2():
    return render_template('about2.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/report', methods=['GET', 'POST'])
@admin_or_user
def report():
    if request.method == 'POST':
        data_type = request.form['data_type']
        name = request.form['name']
        position_or_class = request.form['position_or_class']
        hadir = request.form.get('hadir') == 'on'
        sakit = request.form.get('sakit') == 'on'
        izin = request.form.get('izin') == 'on'
        tanpa_keterangan = request.form.get('tanpa_keterangan') == 'on'
        
        doc = {
            'name': name,
            'position_or_class': position_or_class,
            'hadir': hadir,
            'sakit': sakit,
            'izin': izin,
            'tanpa_keterangan': tanpa_keterangan,
        }
        
        if data_type == 'anak':
            db.absensi_anak.insert_one(doc)
        elif data_type == 'staff':
            db.absensi_staff.insert_one(doc)
        
        return redirect(url_for('report'))
    
    absensi_anak = list(db.absensi_anak.find({}, {'_id': False}))
    absensi_staff = list(db.absensi_staff.find({}, {'_id': False}))
    return render_template('report.html', absensi_anak=absensi_anak, absensi_staff=absensi_staff)

@app.route('/download_report/<report_type>')
def download_report(report_type):
    if report_type == 'csv':
        absensi_anak = list(db.absensi_anak.find({}, {'_id': False}))
        absensi_staff = list(db.absensi_staff.find({}, {'_id': False}))
        
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Name', 'Position/Class', 'Hadir', 'Sakit', 'Izin', 'Tanpa Keterangan'])
        
        for row in absensi_anak:
            writer.writerow([row['name'], row['position_or_class'], row['hadir'], row['sakit'], row['izin'], row['tanpa_keterangan']])
        for row in absensi_staff:
            writer.writerow([row['name'], row['position_or_class'], row['hadir'], row['sakit'], row['izin'], row['tanpa_keterangan']])
        
        output.seek(0)
        return send_file(output, mimetype='text/csv', attachment_filename='report.csv', as_attachment=True)
    
    elif report_type == 'pdf':
        absensi_anak = list(db.absensi_anak.find({}, {'_id': False}))
        absensi_staff = list(db.absensi_staff.find({}, {'_id': False}))
        
        # Generate PDF using reportlab
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        c.drawString(100, 750, "Absensi Anak")
        c.drawString(100, 735, "Name, Position/Class, Hadir, Sakit, Izin, Tanpa Keterangan")
        
        y = 720
        for row in absensi_anak:
            c.drawString(100, y, f"{row['name']}, {row['position_or_class']}, {row['hadir']}, {row['sakit']}, {row['izin']}, {row['tanpa_keterangan']}")
            y -= 15
            
        c.drawString(100, y-30, "Absensi Staff")
        c.drawString(100, y-45, "Name, Position/Class, Hadir, Sakit, Izin, Tanpa Keterangan")
        
        y -= 60
        for row in absensi_staff:
            c.drawString(100, y, f"{row['name']}, {row['position_or_class']}, {row['hadir']}, {row['sakit']}, {row['izin']}, {row['tanpa_keterangan']}")
            y -= 15
        
        c.save()
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, attachment_filename='report.pdf', mimetype='application/pdf')

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query').lower()
    categories = ['absensi', 'laporan keuangan', 'progresif anak']
    results = [category for category in categories if query in category]
    return jsonify(results)

@app.route('/report_progresif_anak', methods=['GET', 'POST'])
@admin_only
def report_progresif_anak():
    if request.method == 'POST':
        name = request.form['name']
        academic_score = int(request.form['academic_score'])
        physical_score = int(request.form['physical_score'])
        attendance_score = int(request.form['attendance_score'])
        
        doc = {
            'name': name,
            'academic_score': academic_score,
            'physical_score': physical_score,
            'attendance_score': attendance_score,
        }
        
        db.progresif_anak.insert_one(doc)
        
        return redirect(url_for('report_progresif_anak'))
    
    progresif_anak = list(db.progresif_anak.find({}, {'_id': False}))
    return render_template('report_progresif_anak.html', progresif_anak=progresif_anak)

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
