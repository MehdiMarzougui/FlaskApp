from flask import Flask, request, render_template, flash, redirect, url_for, session, logging
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, FileField, validators
from passlib.hash import sha256_crypt
from functools import wraps
from dotenv import load_dotenv
import os

app = Flask(__name__)
load_dotenv()


# config MySQL
app.config["MYSQL_HOST"] = os.getenv("MYSQL_HOST")
app.config["MYSQL_USER"] = os.getenv("MYSQL_USER")
app.config["MYSQL_PASSWORD"] = os.getenv("MYSQL_PASSWORD")
app.config["MYSQL_DB"] = os.getenv("MYSQL_DB")
app.config["MYSQL_CURSORCLASS"] = 'DictCursor'
# init MYSQL
Mysql = MySQL(app)


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/articles')
def articles():
    cur = Mysql.connection.cursor()
    result = cur.execute(
        """SELECT * FROM articles
        """)

    articles = cur.fetchall()
    if result > 0:
        return render_template("articles.html", articles=articles)
    else:
        msg = "No Articles found"
        return render_template("articles.html", msg=msg)
    cur.close()


@app.route('/articles/<string:id>')
def article(id):
    cur = Mysql.connection.cursor()
    cur.execute("""SELECT * FROM articles WHERE id=%s""", [id])
    article = cur.fetchone()
    return render_template('article.html', article=article)


class RegisterForm(Form):
    name = StringField('name', [validators.Length(min=1, max=50)])
    username = StringField('username', [validators.Length(min=4, max=25)])
    email = StringField('email', [validators.Length(min=6, max=50)])
    password = PasswordField('password', [
        validators.data_required(),
        validators.equal_to('confirm', message="passowrds do not match")
    ])
    confirm = PasswordField('confirm Passowrd')


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == "POST":
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))
        app.logger.info(request.files)
        profile_picture = request.files['profile_picture']
        profile_picture_path = os.path.join("static\images", username+'.jpg')
        print("I print" + profile_picture_path)
        open(profile_picture_path,
             'wb').write(profile_picture.read())
        # create a cursor
        cur = Mysql.connection.cursor()
        cur.execute("INSERT INTO users(name,email,username,password) VALUES(%s,%s,%s,%s)",
                    (name, email, username, password))
        Mysql.connection.commit()
        cur.close()
        flash('you are now registered and can log in', 'success')
        return redirect(url_for('home'))
    return render_template('register.html', form=form)


@ app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        pqssword_candidate = request.form['password']
        cur = Mysql.connection.cursor()
        result = cur.execute(
            "SELECT * FROM users WHERE username=%s", [username])

        if result > 0:
            data = cur.fetchone()
            password = data['password']
            cur.close()
            # compare password
            if sha256_crypt.verify(pqssword_candidate, password):
                session['logged_in'] = True
                session['username'] = username
                return redirect(url_for("dashboard"))
            else:
                error = 'invalid login'
                return render_template('login.html', error=error)

        else:
            error = "username not found "
            cur.close()
            return render_template('login.html',  error=error)
    return render_template('login.html')


def is_logged_in(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'logged_in' in session:
            return func(*args, **kwargs)
        else:
            flash('unauthorized, please login', 'danger')
            return redirect(url_for('login'))
    return wrapper


@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))


@app.route('/dashboard')
@is_logged_in
def dashboard():
    cur = Mysql.connection.cursor()
    result = cur.execute(
        """SELECT * FROM articles
        WHERE author=%s
        """, [session["username"]]
    )
    app.logger.info(
        url_for('static', filename=f'images/{session["username"]}.jpg'))
    articles = cur.fetchall()
    cur.close()
    if result > 0:
        return render_template("dashboard.html", articles=articles)
    else:
        msg = "No Articles found"
        return render_template("dashboard.html", msg=msg)


class ArticlerForm(Form):
    title = StringField('Title', [validators.Length(min=1, max=200)])
    body = TextAreaField('Body', [validators.Length(min=30)])


@app.route('/add_article', methods=['GET', 'POST'])
@is_logged_in
def add_article():
    form = ArticlerForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        body = form.body.data
        author = session["username"]
        cur = Mysql.connection.cursor()
        cur.execute(
            "INSERT INTO articles(title,author,body) VALUES(%s,%s,%s)", (
                title, author, body)
        )
        Mysql.connection.commit()
        cur.close()
        flash('you article has been submitted', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_article.html', form=form)


@app.route("/edit_article/<string:id>", methods=["GET", "POST"])
@is_logged_in
def edit_article(id):
    cur = Mysql.connection.cursor()
    result = cur.execute("""SELECT * FROM articles WHERE id=%s""", [id])
    article = cur.fetchone()
    form = ArticlerForm(request.form)
    form.title.data = article['title']
    form.body.data = article['body']
    if request.method == "POST" and form.validate():
        form = ArticlerForm(request.form)
        title = form.title.data
        body = form.body.data
        cur = Mysql.connection.cursor()
        result = cur.execute(
            """UPDATE articles SET title=%s, body=%s WHERE id=%s""", (title, body, id))
        Mysql.connection.commit()
        cur.close()
        flash('Article updated', 'success')
        return redirect(url_for('dashboard'))
    return render_template("edit_article.html", form=form)


@app.route("/delete_article/<string:id>", methods=["POST"])
@is_logged_in
def delete_article(id):
    cur = Mysql.connection.cursor()
    cur.execute(
        "DELETE fROM articles WHERE id=%s", [id]
    )
    Mysql.connection.commit()
    cur.close()
    flash('Article Deleted', "success")
    return redirect(url_for('dashboard'))


if __name__ == "__main__":
    app.secret_key = 'secret123'
    app.run(debug=True)
