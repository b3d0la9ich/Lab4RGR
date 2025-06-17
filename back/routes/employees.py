from flask import Blueprint, request, jsonify, make_response
from models import Employee, Incident, IncidentStatus
from schemas.incident_schema import EmployeeSchema
from extensions import db
from flask_jwt_extended import jwt_required, get_jwt_identity
from functools import wraps
from werkzeug.security import generate_password_hash

employees_bp = Blueprint('employees', __name__)
employee_schema = EmployeeSchema()
employee_list_schema = EmployeeSchema(many=True)


# 🔒 Проверка роли администратора
def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        user = Employee.query.get(user_id)
        if not user or user.role != 'admin':
            return jsonify({"error": "Доступ запрещён"}), 403
        return fn(*args, **kwargs)
    return wrapper


# 🔍 Все сотрудники с назначением
@employees_bp.route('/', methods=['GET'])
@admin_required
def get_all_employees():
    employees = Employee.query.all()
    result = []

    for e in employees:
        assigned_incident = (
            db.session.query(Incident)
            .join(IncidentStatus)
            .filter(Incident.assigned_employee_id == e.id)
            .filter(IncidentStatus.name != 'завершён')
            .first()
        )

        result.append({
            "id": e.id,
            "name": f"{e.first_name} {e.last_name}",
            "email": e.email,
            "role": e.role,
            "is_busy": bool(assigned_incident),
            "assigned_incident": {
                "id": assigned_incident.id,
                "title": assigned_incident.title,
                "status": assigned_incident.status.name
            } if assigned_incident else None
        })

    return jsonify(result), 200


# 🔍 Один сотрудник
@employees_bp.route('', methods=['GET'])
@jwt_required()
def get_employees():
    employees = Employee.query.all()
    result = []

    for emp in employees:
        active_incident = (
            db.session.query(Incident)
            .filter(Incident.assigned_employee_id == emp.id)
            .join(IncidentStatus)
            .filter(IncidentStatus.name != 'завершён')
            .first()
        )

        emp_data = {
            'id': emp.id,
            'name': f"{emp.first_name} {emp.last_name}",
            'email': emp.email,
            'role': emp.role,
            'assigned_incident': None
        }

        if active_incident:
            emp_data['assigned_incident'] = {
                'id': active_incident.id,
                'title': active_incident.title,
                'status': active_incident.status.name
            }

        result.append(emp_data)

    return jsonify(result), 200


# ➕ Создание сотрудника
@employees_bp.route('/', methods=['POST'])
@admin_required
def create_employee():
    data = request.get_json()
    if Employee.query.filter_by(email=data.get("email")).first():
        return jsonify({"error": "Пользователь с таким email уже существует"}), 400

    data["role"] = data.get("role", "user")
    if "password" not in data:
        return jsonify({"error": "Пароль обязателен"}), 400

    data["password"] = generate_password_hash(data["password"])
    try:
        new_employee = employee_schema.load(data)
        db.session.add(new_employee)
        db.session.commit()
        return employee_schema.dump(new_employee), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ✏️ Обновление
@employees_bp.route('/<int:employee_id>', methods=['PUT'])
@admin_required
def update_employee(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    data = request.get_json()
    if "password" in data:
        data["password"] = generate_password_hash(data["password"])
    try:
        updated = employee_schema.load(data, instance=employee, partial=True)
        db.session.commit()
        return employee_schema.dump(updated), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ❌ Удаление
@employees_bp.route('/<int:employee_id>', methods=['DELETE'])
@admin_required
def delete_employee(employee_id):
    employee = Employee.query.get_or_404(employee_id)

    # получаем все незавершённые инциденты, назначенные на этого сотрудника
    open_incidents = (
        db.session.query(Incident)
        .join(IncidentStatus)
        .filter(Incident.assigned_employee_id == employee_id)
        .filter(IncidentStatus.name != 'завершён')
        .all()
    )

    # если нет активных инцидентов — просто удаляем
    if not open_incidents:
        db.session.delete(employee)
        db.session.commit()
        return jsonify({"message": "Сотрудник удалён"}), 200

    # получаем reassigned_to из тела запроса
    data = request.get_json(silent=True) or {}
    reassigned_to = data.get('reassigned_to')

    free_employees = Employee.query.filter(
        Employee.id != employee_id,
        Employee.role == 'user'
    ).all()

    admin_id = get_jwt_identity()
    admin = Employee.query.get(admin_id)

    for incident in open_incidents:
        reassignee = None

        if reassigned_to:
            reassignee = Employee.query.get(reassigned_to)
            if not reassignee:
                return jsonify({"error": "Неверный reassigned_to ID"}), 400
        elif free_employees:
            reassignee = free_employees.pop(0)
        else:
            reassignee = admin

        # вот здесь происходит переназначение!
        incident.assigned_employee_id = reassignee.id
        db.session.add(incident)

    db.session.delete(employee)
    db.session.commit()

    return jsonify({"message": "Сотрудник удалён, инциденты переназначены"}), 200


# 🔄 Preflight CORS support
@employees_bp.route('/', methods=['OPTIONS'])
@employees_bp.route('/<int:employee_id>', methods=['OPTIONS'])
def preflight_employees(employee_id=None):
    resp = make_response()
    resp.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
    resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    resp.headers['Access-Control-Allow-Headers'] = 'Authorization, Content-Type'
    resp.headers['Access-Control-Allow-Credentials'] = 'true'
    return resp, 200
