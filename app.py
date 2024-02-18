from werkzeug.middleware.proxy_fix import ProxyFix
from flask import Flask, render_template, redirect, request, url_for, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_, text
import uuid
import random

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///carcatalog.db"
db = SQLAlchemy(app)

# The lab is behind a http proxy, so it's not aware of the fact that it should use https.
# We use ProxyFix to enable it: https://flask.palletsprojects.com/en/2.0.x/deploying/wsgi-standalone/#proxy-setups
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)


# Used for any other security related needs by extensions or application, i.e. csrf token
app.config['SECRET_KEY'] = 'mysecretkey'

# Required for cookies set by Flask to work in the preview window that's integrated in the lab IDE
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = True

# Required to render urls with https when not in a request context. Urls within Udemy labs must use https
app.config['PREFERRED_URL_SCHEME'] = 'https'


@app.route("/")
def index():
    print('Received headers', request.headers)
    return render_template('index.html')


@app.route("/redirect/")
def redirect_to_index():
    return redirect(url_for('index'))


class Car(db.Model):
    id = db.Column(db.String(50), primary_key=True)
    brand = db.Column(db.String(50))
    model = db.Column(db.String(50))
    transmission = db.Column(db.String(20))
    price = db.Column(db.Integer)
    release_year = db.Column(db.Integer)

    def __init__(self, id, brand, model, transmission, price, release_year):
        self.id = id
        self.brand = brand
        self.model = model
        self.transmission = transmission
        self.price = price
        self.release_year = release_year

    def to_json(self):
        return {
            'brand': self.brand,
            'model': self.model,
            'transmission': self.transmission,
            'price': self.price,
            'release_year': self.release_year
        }


with app.app_context():
    db.drop_all()
    db.create_all()

    for i in range(1, 101):
        if i <= 33:
            brand = 'Honda'
        elif i <= 66:
            brand = 'Ford'
        else:
            brand = 'BMW'

        model = brand + ' ' + str(i)

        if i % 2 != 0:
            transmission = 'AUTOMATIC'
        else:
            transmission = 'MANUAL'

        price = random.randint(30000, 80000)
        release_year = 2020 + (i % 3)

        car = Car(str(uuid.uuid4()), brand, model, transmission, price, release_year)
        db.session.add(car)
        db.session.commit()


@app.route("/api/cars")
def get_cars():
    page = request.args.get('page', 1, type=int)
    size = request.args.get('size', 10, type=int)
    brand = request.args.get('brand', '%')
    model = request.args.get('model', '%')
    transmission = request.args.get('transmission', '%')

    price_operator = request.args.get('price_operator')
    price_value = request.args.get('price', 0, type=int)
    price_max_value = request.args.get('price_max', price_value + 1, type=int)

    sort_by = request.args.get('sort_by')
    sort_direction = request.args.get('sort_direction')

    query = Car.query

    query = query.filter(and_(
        Car.brand.ilike('%' + brand + '%'),
        Car.model.ilike('%' + model + '%'),
        Car.transmission.ilike('%' + transmission + '%')
    ))

    if price_operator == 'lte':
        query = query.filter(Car.price <= price_value)
    elif price_operator == 'gte':
        query = query.filter(Car.price >= price_value)
    elif price_operator == 'between':
        query = query.filter(Car.price.between(price_value, price_max_value))

    list_sort_by = sort_by.split(',')
    list_sort_direction = sort_direction.split(',')
    diff = len(list_sort_by) - len(list_sort_direction)
    for x in range(diff):
        list_sort_direction.append('asc')

    # if sort_by and sort_direction == 'asc':
    #     query = query.order_by(getattr(Car, sort_by).asc())
    # elif sort_by and sort_direction == 'desc':
    #     query = query.order_by(getattr(Car, sort_by).desc())

    sort_columns = []
    for idx, sb in enumerate(list_sort_by):
        sort_columns.append(sb + ' ' + list_sort_direction[idx])
    query = query.order_by(text(','.join(sort_columns)))

    cars = query.paginate(page=page, per_page=size)
    cars_json = [car.to_json() for car in cars.items]

    return jsonify(
        data=cars_json,
        page=page,
        size=size,
        total_element=cars.total,
        total_pages=cars.pages
    ), 200


# def paginate(items, page, size):
#     start = (page - 1) * size
#     end = start + size
#     return items[start:end]
