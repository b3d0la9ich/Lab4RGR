from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from models import Employee
from extensions import db

auth_bp = Blueprint('auth', __name__)

# 🔐 Регистрация пользователя
@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    if Employee.query.filter_by(email=data['email']).first():
        return jsonify({"error": "Пользователь с таким email уже существует"}), 400

    new_user = Employee(
        first_name=data['first_name'],
        last_name=data['last_name'],
        email=data['email'],
        phone=data['phone'],
        password=generate_password_hash(data['password']),
        role='user',  # фиксированно
        position='Сотрудник'  # фиксированно
    )

    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "Пользователь зарегистрирован"}), 201


# 🔐 Вход и выдача JWT
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    user = Employee.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password, password):
        return jsonify({"error": "Неверный email или пароль"}), 401

    # ✅ Передаём identity как строку!
    access_token = create_access_token(identity=str(user.id))

    return jsonify({
        "access_token": access_token,
        "user_id": user.id
    }), 200


# 🔐 Получение профиля (с логами)
@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def profile():
    # ✅ Получаем строку и приводим к int
    user_id = int(get_jwt_identity())
    user = Employee.query.get(user_id)

    if not user:
        return jsonify({"error": "Пользователь не найден"}), 404

    return jsonify({
        "id": user.id,
        "name": f"{user.first_name} {user.last_name}",
        "email": user.email,
        "role": user.role
    }), 200


# 🧪 Тестовый маршрут без @jwt_required — просто выводит заголовки
@auth_bp.route('/profile-debug', methods=['GET'])
def profile_debug():
    from flask import request

    headers = dict(request.headers)
    print("🧪 RAW HEADERS:", headers)

    return jsonify({
        "message": "Заголовки получены",
        "headers": headers
    }), 200

