from flask import Flask
from flask_cors import CORS
from extensions import db, jwt
from werkzeug.security import generate_password_hash

app = Flask(__name__)
app.config.from_object('config.Config')

app.config['JWT_TOKEN_LOCATION'] = ['headers']
app.config['JWT_HEADER_NAME'] = 'Authorization'
app.config['JWT_HEADER_TYPE'] = 'Bearer'

CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}}, supports_credentials=True)

db.init_app(app)
jwt.init_app(app)


# 👤 Создание администратора
def create_admin():
    with app.app_context():
        from models import Employee
        if not Employee.query.filter_by(email="admin@airport.com").first():
            admin = Employee(
                first_name="Админ",
                last_name="Системы",
                position="",
                phone="0000000000",
                email="admin@airport.com",
                role="admin",
                password=generate_password_hash("Pa$$w0rd!")
            )
            db.session.add(admin)
            db.session.commit()

# 📍 Добавление локаций
def create_locations():
    with app.app_context():
        from models import Location
        if not Location.query.first():
            db.session.add_all([
                Location(location_name="Терминал A", location_type="пассажирская зона"),
                Location(location_name="Грузовой отсек", location_type="техническая зона"),
                Location(location_name="Зона контроля", location_type="безопасность")
            ])
            db.session.commit()

# Регистрация маршрутов
from routes.auth import auth_bp
from routes.employees import employees_bp
from routes.incidents import incidents_bp
from routes.locations import locations_bp
from routes.incident_statuses import incident_statuses_bp

app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(employees_bp, url_prefix='/api/employees')
app.register_blueprint(incidents_bp, url_prefix='/api/incidents')
app.register_blueprint(locations_bp, url_prefix='/api/locations')
app.register_blueprint(incident_statuses_bp, url_prefix='/api/incident_statuses')

if __name__ == '__main__':
    create_admin()
    create_locations()
    app.run(debug=True, host="0.0.0.0", port=5000)
