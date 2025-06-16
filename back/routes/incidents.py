from flask import Blueprint, request, jsonify, current_app as app, make_response
from models import Incident, Employee
from schemas.incident_schema import IncidentSchema
from extensions import db
from flask_jwt_extended import jwt_required, get_jwt_identity
from functools import wraps
from models import Incident, Employee, IncidentStatus


incidents_bp = Blueprint('incidents', __name__)
incident_schema = IncidentSchema()
incident_list_schema = IncidentSchema(many=True)

# 🔒 Декоратор для проверки роли администратора
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

# 🔍 Получить список всех инцидентов (только админ)
@incidents_bp.route('/', methods=['GET'])
@admin_required
def get_all_incidents():
    incidents = Incident.query.order_by(Incident.incident_datetime.desc()).all()
    return jsonify(incident_list_schema.dump(incidents)), 200

# 🔍 Получить один инцидент по ID (любой сотрудник)
@incidents_bp.route('/<int:incident_id>', methods=['GET'])
@jwt_required()
def get_incident(incident_id):
    incident = Incident.query.get_or_404(incident_id)
    return jsonify(incident_schema.dump(incident)), 200

# 🆕 Создать инцидент
@incidents_bp.route('', methods=['POST'])
@admin_required
def create_incident():
    app.logger.info("📥 POST /api/incidents — получен запрос")
    data = request.get_json()
    app.logger.debug(f"🔎 Полученные данные: {data}")

    try:
        # Принудительно устанавливаем статус "новый" (id=1)
        data['status_id'] = 1

        new_incident = incident_schema.load(data)
        db.session.add(new_incident)

        assigned_id = data.get("assigned_employee_id")
        if assigned_id:
            employee = Employee.query.get(assigned_id)
            if employee:
                app.logger.info(f"👤 Сотрудник {employee.id} ({employee.email}) помечен как занятый")

        db.session.commit()
        app.logger.info(f"💾 Инцидент сохранён в базе: ID {new_incident.id}")
        return incident_schema.dump(new_incident), 201

    except Exception as e:
        app.logger.error(f"❌ Ошибка при создании инцидента: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 400


# 🛰️ Preflight запрос (OPTIONS)
@incidents_bp.route('', methods=['OPTIONS'])
@incidents_bp.route('/<int:incident_id>', methods=['OPTIONS'])
def preflight_incident(incident_id=None):
    resp = make_response()
    resp.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
    resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    resp.headers['Access-Control-Allow-Headers'] = 'Authorization, Content-Type'
    resp.headers['Access-Control-Allow-Credentials'] = 'true'
    return resp, 200

# ✏️ Обновить инцидент
@incidents_bp.route('/<int:incident_id>', methods=['PUT'])
@admin_required
def update_incident(incident_id):
    app.logger.info(f"✏️ PUT /api/incidents/{incident_id} — обновление инцидента")
    incident = Incident.query.get_or_404(incident_id)
    data = request.get_json()
    app.logger.debug(f"🔄 Новые данные: {data}")
    try:
        updated = incident_schema.load(data, instance=incident, partial=True)
        db.session.commit()
        app.logger.info(f"✅ Обновлено успешно: ID {updated.id}")
        return incident_schema.dump(updated), 200
    except Exception as e:
        app.logger.error(f"❌ Ошибка при обновлении: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 400

# ❌ Удалить инцидент
@incidents_bp.route('/<int:incident_id>', methods=['DELETE'])
@admin_required
def delete_incident(incident_id):
    incident = Incident.query.get_or_404(incident_id)
    db.session.delete(incident)
    db.session.commit()
    return jsonify({"message": "Инцидент удалён"}), 200

# 📌 Назначить сотрудника
@incidents_bp.route('/<int:incident_id>/assign/<int:employee_id>', methods=['POST'])
@admin_required
def assign_incident(incident_id, employee_id):
    incident = Incident.query.get_or_404(incident_id)
    employee = Employee.query.get_or_404(employee_id)

    if incident.assigned_employee_id == employee.id:
        return jsonify({"message": "Инцидент уже назначен этому сотруднику"}), 200

    if incident.status_id:
        status = str(incident.status.name).lower()
        if status in ['закрыт', 'завершён']:
            return jsonify({"error": "Нельзя назначать завершённый инцидент"}), 400

    incident.assigned_employee_id = employee.id
    db.session.commit()
    return jsonify({
        "message": f"Инцидент назначен {employee.first_name} {employee.last_name}",
        "incident_id": incident.id,
        "assigned_to": employee.id
    }), 200

# 📄 Получить список инцидентов для текущего сотрудника
@incidents_bp.route('/my', methods=['GET'])
@jwt_required()
def get_my_incidents():
    user_id = get_jwt_identity()
    employee = Employee.query.get_or_404(user_id)

    assigned = Incident.query.filter_by(
        assigned_employee_id=employee.id
    ).order_by(Incident.incident_datetime.desc()).all()

    return jsonify(incident_list_schema.dump(assigned)), 200

@incidents_bp.route('/<int:incident_id>/complete', methods=['POST'])
@jwt_required()
def complete_incident(incident_id):
    user_id = get_jwt_identity()
    incident = Incident.query.get_or_404(incident_id)

    # Проверка: только ответственный сотрудник может завершить
    if incident.assigned_employee_id != user_id:
        return jsonify({"error": "Вы не назначены на этот инцидент"}), 403

    # Устанавливаем статус "завершён"
    status = IncidentStatus.query.filter_by(name='завершён').first()
    if not status:
        return jsonify({"error": "Статус 'завершён' не найден в базе"}), 500

    incident.status_id = status.id
    db.session.commit()

    return jsonify({"message": f"Инцидент #{incident.id} завершён"}), 200

