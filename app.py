from flask import Flask, render_template
from flask_mysqldb import MySQL

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('home.html')


if __name__ == '__main__':
    app.secret_key = "Rw8w2Y#3Wmoj"
    app.run(debug=True)
