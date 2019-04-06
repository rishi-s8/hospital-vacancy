from flask import Flask, render_template, flash, redirect, url_for, session, request, logging
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators, IntegerField
from passlib.context import CryptContext
from functools import wraps
cryptcontext = CryptContext(schemes=["sha256_crypt", "md5_crypt", "des_crypt"])

app = Flask(__name__)

# Config MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'hospitalVacancy'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# init MySQL
mysql = MySQL(app)

def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized. Please log in.', 'danger')
            return redirect(url_for('login'))
    return wrap

@app.route('/')
def index():
    return render_template('home.html')

class RegisterForm(Form):
    name = StringField('Hospital Name', [validators.Length(min=1, max=100), validators.DataRequired()])
    username = StringField('Hospital ID', [validators.Length(min=1, max=50), validators.DataRequired()])
    password = PasswordField('Password', [validators.Length(min=6, max=50), validators.DataRequired(), validators.EqualTo('confirm', message='Passwords Do not match')])
    confirm = PasswordField('Confirm Password', [validators.DataRequired()])
    rooms = IntegerField('Total Rooms', [validators.DataRequired()])
    vacant_rooms = IntegerField('Vacant Rooms', [validators.DataRequired()])
    wards = IntegerField('Total Wards', [validators.DataRequired()], render_kw={"style": "display:inline;"})
    vacant_wards = IntegerField('Vacant Wards', [validators.DataRequired()])
    icus = IntegerField('Total ICUs', [validators.DataRequired()])
    vacant_icus = IntegerField('Vacant ICUs', [validators.DataRequired()])

class AddDoctorsForm(Form):
    did = StringField('Doctor ID', [validators.Length(min=1, max=100), validators.DataRequired()])
    name = StringField('Doctor Name', [validators.Length(min=1, max=50), validators.DataRequired()])
    dept = StringField('Department', [validators.Length(min=1, max=50), validators.DataRequired()])
    contact = StringField('Contact', [validators.DataRequired()])


@app.route('/addDoctor', methods=['GET', 'POST'])
def addDoctor():
    form = AddDoctorsForm(request.form)
    if request.method == 'POST' and form.validate():
        did = form.did.data
        name = form.name.data
        dept = form.dept.data
        contact = form.contact.data

        #Create Cursor
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO Doctors(docId, docName, speciality, contact) Values(%s, %s, %s, %s)", (did, name, dept, contact))
        cur.execute("INSERT INTO Doc_hospital(hid, docID) Values(%s, %s)", (session["username"], did))
        mysql.connection.commit()

        #Close Connection
        #cur.close()

        flash("Added Successfully", "success")
        return redirect(url_for('index'))

    return render_template('addDoctor.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        username = form.username.data
        password = cryptcontext.hash(str(form.password.data))
        rooms = form.rooms.data
        wards = form.wards.data
        icus = form.icus.data
        vacant_rooms = form.vacant_rooms.data
        vacant_wards = form.vacant_wards.data
        vacant_icus = form.vacant_icus.data
        #Create Cursor
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO Login(hname, hid, password) Values(%s, %s, %s)", (name, username, password))
        cur.execute("INSERT INTO hospitals(hid, num_of_rooms, num_of_wards, num_of_icus, vacant_rooms, vacant_icus, vacant_wards) Values(%s, %s, %s, %s, %s, %s, %s)", (username, int(rooms), int(wards), int(icus), int(vacant_rooms), int(vacant_icus), int(vacant_wards)))
        mysql.connection.commit()

        #Close Connection
        cur.close()

        flash("Registered Successfully", "success")
        return redirect(url_for('index'))

    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password_candidate = request.form['password']

        cur = mysql.connection.cursor()
        result = cur.execute("SELECT * FROM Login where hid = %s", [username])
        if result>0:
            data = cur.fetchone()
            password = data['password']
            if cryptcontext.verify(password_candidate, password):
                result = cur.execute("SELECT hname FROM Login where hid = %s", [username])
                data = cur.fetchone()
                session['logged_in'] = True
                session['username'] = username
                session['hname'] = data['hname']
                flash("You are now logged in", 'success')
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid Login'
                return render_template('login.html', error= error)
        else:
            error = 'Invalid Login'
            return render_template('login.html', error= error)
        cur.close()
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("You are now logged out", "success")
    return redirect(url_for('login'))


@app.route('/dashboard')
@is_logged_in
def dashboard():
    cur = mysql.connection.cursor()
    result = cur.execute("SELECT speciality FROM Doctors, Doc_hospital where Doc_hospital.hid = %s and Doc_hospital.docId = Doctors.docId", [session["username"]])
    data = cur.fetchall()

    if result > 0:
        return render_template('dashboard.html', articles = data)
    else:
        msg = "No Departments Found"
        return render_template('dashboard.html', msg = msg)

    cur.close()

def get_specialties():
    cur = mysql.connection.cursor()
    result = cur.execute("SELECT speciality FROM Doctors, Doc_hospital where Doc_hospital.hid = %s and Doc_hospital.docId = Doctors.docId", [session["username"]])
    data = cur.fetchall()
    cur.close()
    return result, data

@app.route('/vacancies')
@is_logged_in
def vacancies():
    if session.get('page'):
        session.pop('page')
    result, data = get_specialties()
    if result > 0:
        return render_template('vacancies.html', articles = data)
    else:
        msg = "No Departments Found"
        return render_template('vacancies.html', msg = msg)

def get_doctors():
    cur = mysql.connection.cursor()
    result = cur.execute("SELECT Doctors.docName, Doctors.docId, Doctors.contact FROM Doctors, Doc_hospital where Doc_hospital.hid = %s and Doc_hospital.docId = Doctors.docId and Doctors.speciality = %s", [session["username"], session["page"]])
    data = cur.fetchall()
    cur.close()
    return data

@app.route('/departments')
@is_logged_in
def departments():
    if not(session.get('page')):
        return redirect(url_for('dashboard'))
    result, articles_data = get_specialties()
    doctors = get_doctors()

    if result > 0:
        return render_template('departments.html', articles = articles_data, doctors = doctors)
    else:
        msg = "No Departments Found"
        return render_template('departments.html', msg = msg)

@app.route('/departments/<string:id>')
@is_logged_in
def department(id):
    session["page"] = id
    return redirect(url_for('departments'))

if __name__ == '__main__':
    app.secret_key = "Rw8w2Y#3Wmoj"
    app.run(debug=True)
