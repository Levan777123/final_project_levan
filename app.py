from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    age = db.Column(db.Integer)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    image = db.Column(db.String(100), default="default.png")
    balance = db.Column(db.Float, default=1000)
    role = db.Column(db.String(10), default='user')

class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    description = db.Column(db.Text)
    price = db.Column(db.Float)
    showtime = db.Column(db.String(100))
    image = db.Column(db.String(100), default="default_movie.png")
    available = db.Column(db.Boolean, default=True)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    user = db.relationship('User', backref='orders')
    movie = db.relationship('Movie')


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route("/")
@login_required
def home():
    movies = Movie.query.filter_by(available=True).all()
    return render_template("home.html", movies=movies)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        age = int(request.form.get("age"))
        email = request.form.get("email")
        role = request.form["role"]

        password = generate_password_hash(request.form.get("password"))


        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return "მომხმარებელი უკვე არსებობს"

        if role == "Admin":
            new_user = User(name=name, password=password, age = age, email=email, role="Admin")
        else:
            new_user = User(name=name, password=password, age=age, email=email, role="user")

        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('home'))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":

        email = request.form.get("email")
        password = request.form.get("password")
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            return "ელ. ფოსტა ან პაროლი არასწორია"

    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/book/<int:movie_id>", methods=["GET", "POST"])
@login_required
def book_movie(movie_id):
    movie = Movie.query.get_or_404(movie_id)

    if not movie.available:
        flash("ფილმი მიუწვდომელია.")
        return redirect(url_for("home"))

    if current_user.balance < movie.price:
        flash("არასაკმარისი ბალანსი!")
        return redirect(url_for("home"))

    order = Order(user_id=current_user.id, movie_id=movie.id)
    db.session.add(order)
    current_user.balance -= movie.price
    db.session.commit()

    flash("დაჯავშნა წარმატებით შესრულდა!")
    return redirect(url_for("home"))

@app.route("/add_movie", methods=["GET", "POST"])
@login_required
def add_movie():
    if current_user.role.lower() != "admin":
        return "დაშვება მხოლოდ ადმინისთვის", 403

    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        price = float(request.form.get("price"))
        showtime = request.form.get("showtime")
        image_file = request.files["image"]

        filename = image_file.filename
        image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        image_file.save(image_path)

        new_movie = Movie(
            title=title,
            description=description,
            price=price,
            showtime=showtime,
            image=filename
        )
        db.session.add(new_movie)
        db.session.commit()
        flash("ფილმი წარმატებით დაემატა!")
        return redirect(url_for("admin_panel"))

    return render_template("add_movie.html")

@app.route("/admin")
@login_required
def admin_panel():
    if current_user.role == "user":
        return "დაშვება მხოლოდ ადმინებისთვის", 403

    movies = Movie.query.all()
    return render_template("admin.html", movies=movies)


    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        price = float(request.form.get("price"))
        showtime = request.form.get("showtime")
        image_file = request.files["image"]

        filename = image_file.filename
        image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        image_file.save(image_path)

        new_movie = Movie(
            title=title,
            description=description,
            price=price,
            showtime=showtime,
            image=filename
        )
        db.session.add(new_movie)
        db.session.commit()
        return redirect(url_for("admin_panel"))

    movies = Movie.query.all()
    return render_template("admin.html", movies=movies)
@app.route("/delete_movie/<int:movie_id>", methods=["POST"])
@login_required
def delete_movie(movie_id):
    if current_user.role == "user":
        return "დაშვება მხოლოდ ადმინებისთვის", 403

    movie = Movie.query.get_or_404(movie_id)
    db.session.delete(movie)
    db.session.commit()
    flash("ფილმი წაიშალა წარმატებით!")
    return redirect(url_for("admin_panel"))
@app.route("/edit_movie/<int:movie_id>", methods=["GET", "POST"])
@login_required
def edit_movie(movie_id):
    if current_user.role == "user":
        return "დაშვება მხოლოდ ადმინებისთვის", 403

    movie = Movie.query.get_or_404(movie_id)

    if request.method == "POST":
        movie.title = request.form.get("title")
        movie.description = request.form.get("description")
        movie.price = float(request.form.get("price"))
        movie.showtime = request.form.get("showtime")

        image_file = request.files.get("image")
        if image_file and image_file.filename:
            filename = image_file.filename
            image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            image_file.save(image_path)
            movie.image = filename

        db.session.commit()
        flash("ფილმი განახლდა წარმატებით!")
        return redirect(url_for("admin_panel"))

    return render_template("edit_movie.html", movie=movie)
@app.route("/my_tickets")
@login_required
def my_tickets():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.timestamp.desc()).all()
    return render_template("my_tickets.html", orders=orders)
@app.route("/admin/orders")
@login_required
def admin_orders():
    if current_user.role == "user":
        return "დაშვება მხოლოდ ადმინებისთვის", 403

    orders = Order.query.order_by(Order.timestamp.desc()).all()
    return render_template("admin_orders.html", orders=orders)
@app.route("/admin/delete_order/<int:order_id>", methods=["POST"])
@login_required
def delete_order(order_id):
    if current_user.role == "user":
        return "დაშვება მხოლოდ ადმინებისთვის", 403

    order = Order.query.get_or_404(order_id)
    db.session.delete(order)
    db.session.commit()
    flash("ბილეთი წაიშალა.")
    return redirect(url_for("admin_orders"))
@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html", user=current_user)
@app.route("/edit_profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    if request.method == "POST":
        name = request.form.get("name")
        age = request.form.get("age")
        password = request.form.get("password")
        image_file = request.files.get("image")


        current_user.name = name
        current_user.age = age

        if password:
            current_user.password = generate_password_hash(password)


        if image_file and image_file.filename != "":
            filename = image_file.filename
            image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            image_file.save(image_path)
            current_user.image = filename

        db.session.commit()
        flash("პროფილი წარმატებით განახლდა.")
        return redirect(url_for("profile"))

    return render_template("edit_profile.html", user=current_user)
@app.route("/add_balance", methods=["GET", "POST"])
@login_required
def add_balance():
    if request.method == "POST":
        amount = float(request.form.get("amount"))
        if amount > 0:
            current_user.balance += amount
            db.session.commit()
            flash("ბალანსი წარმატებით დაემატა!")
            return redirect(url_for("profile"))
        else:
            flash("გთხოვ შეიყვანე დადებითი რიცხვი")
    return render_template("add_balance.html")
@app.route("/users")
@login_required
def users():
    if current_user.role == "user":
        return "დაშვება მხოლოდ ადმინისტრატორისთვის", 403

    all_users = User.query.filter(User.role == 'user').all()
    return render_template("users.html", users=all_users)
@app.route("/user/<int:user_id>/orders")
@login_required
def user_orders(user_id):
    if current_user.role == "user":
        return "დაშვება მხოლოდ ადმინისტრატორისთვის", 403

    user = User.query.get_or_404(user_id)
    orders = Order.query.filter_by(user_id=user.id).all()
    return render_template("user_orders.html", user=user, orders=orders)


class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    user = db.relationship('User', backref='cart_items')
    movie = db.relationship('Movie')

@app.route("/add_to_cart/<int:movie_id>")
@login_required
def add_to_cart(movie_id):
    movie = Movie.query.get_or_404(movie_id)
    existing = CartItem.query.filter_by(user_id=current_user.id, movie_id=movie.id).first()
    if not existing:
        item = CartItem(user_id=current_user.id, movie_id=movie.id)
        db.session.add(item)
        db.session.commit()
        flash("დაემატა კალათაში!")
    else:
        flash("ეს ფილმი უკვე კალათაშია.")
    return redirect(url_for('home'))

@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    total = sum(item.movie.price * item.quantity for item in cart_items)


    if request.method == "POST":
        if current_user.balance < total:
            flash("არასაკმარისი ბალანსი")
            return redirect(url_for("checkout"))

        for item in cart_items:
            order = Order(user_id=current_user.id, movie_id=item.movie.id, quantity=item.quantity)
            db.session.add(order)
            db.session.delete(item)

        current_user.balance -= total
        db.session.commit()
        flash("გადახდა წარმატებით შესრულდა!")
        return redirect(url_for("home"))


    return render_template("checkout.html", cart_items=cart_items, total=total)

    return render_template("checkout.html", cart_items=cart_items, total=total)
@app.route("/remove_from_cart/<int:item_id>")
@login_required
def remove_from_cart(item_id):
    item = CartItem.query.get_or_404(item_id)

    if item.user_id != current_user.id and current_user.role == "user":
        flash("არ გაქვს წაშლის უფლება.")
        return redirect(url_for("checkout"))

    db.session.delete(item)
    db.session.commit()
    flash("წაშლილია კალათიდან.")
    return redirect(url_for("checkout"))
@app.route("/cart/decrease/<int:item_id>")
@login_required
def decrease_quantity(item_id):
    item = CartItem.query.get_or_404(item_id)
    if item.user_id != current_user.id:
        return "არ გაქვს წვდომა", 403
    if item.quantity > 1:
        item.quantity -= 1
    else:
        db.session.delete(item)
    db.session.commit()
    return redirect(url_for("checkout"))
@app.route("/cart/increase/<int:item_id>")
@login_required
def increase_quantity(item_id):
    item = CartItem.query.get_or_404(item_id)
    if item.user_id != current_user.id:
        return "არ გაქვს წვდომა", 403
    item.quantity += 1
    db.session.commit()
    return redirect(url_for("checkout"))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)
