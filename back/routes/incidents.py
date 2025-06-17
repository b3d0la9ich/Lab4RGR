from flask import Blueprint, request, jsonify, current_app as app, make_response
from models import Incident, Employee, IncidentStatus
from schemas.incident_schema import IncidentSchema
from extensions import db
from flask_jwt_extended import jwt_required, get_jwt_identity
from functools import wraps
from datetime import datetime
import os
from fpdf import FPDF

incidents_bp = Blueprint('incidents', __name__)
incident_schema = IncidentSchema()
incident_list_schema = IncidentSchema(many=True)

def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        user = Employee.query.get(user_id)
        if not user or user.role != 'admin':
            return jsonify({"error": "Access denied"}), 403
        return fn(*args, **kwargs)
    return wrapper

@incidents_bp.route('/', methods=['GET'])
@admin_required
def get_all_incidents():
    incidents = Incident.query.order_by(Incident.incident_datetime.desc()).all()
    return jsonify(incident_list_schema.dump(incidents)), 200

@incidents_bp.route('/<int:incident_id>', methods=['GET'])
@jwt_required()
def get_incident(incident_id):
    incident = Incident.query.get_or_404(incident_id)
    return jsonify(incident.to_dict()), 200

@incidents_bp.route('', methods=['POST'])
@admin_required
def create_incident():
    data = request.get_json()
    data['status_id'] = 1
    try:
        new_incident = incident_schema.load(data)
        db.session.add(new_incident)
        db.session.commit()
        return incident_schema.dump(new_incident), 201
    except Exception as e:
        app.logger.error(f"Create incident error: {str(e)}")
        return jsonify({"error": str(e)}), 400

@incidents_bp.route('/<int:incident_id>', methods=['PUT'])
@admin_required
def update_incident(incident_id):
    incident = Incident.query.get_or_404(incident_id)

    # 🔒 Запрет на редактирование завершённых
    if incident.status and incident.status.name.lower() == 'завершён':
        return jsonify({"error": "Нельзя редактировать завершённый инцидент"}), 403

    data = request.get_json()
    try:
        updated = incident_schema.load(data, instance=incident, partial=True)
        db.session.commit()
        return incident_schema.dump(updated), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@incidents_bp.route('/<int:incident_id>', methods=['DELETE'])
@admin_required
def delete_incident(incident_id):
    incident = Incident.query.get_or_404(incident_id)
    db.session.delete(incident)
    db.session.commit()
    return jsonify({"message": "Incident deleted"}), 200

@incidents_bp.route('/<int:incident_id>/assign/<int:employee_id>', methods=['POST'])
@admin_required
def assign_incident(incident_id, employee_id):
    incident = Incident.query.get_or_404(incident_id)
    employee = Employee.query.get_or_404(employee_id)

    if incident.assigned_employee_id == employee.id:
        return jsonify({"message": "Incident already assigned"}), 200

    if incident.status.name.lower() in ['завершён', 'закрыт']:
        return jsonify({"error": "Cannot assign closed incident"}), 400

    incident.assigned_employee_id = employee.id
    db.session.commit()
    return jsonify({
        "message": f"Incident assigned to {employee.first_name} {employee.last_name}",
        "incident_id": incident.id,
        "assigned_to": employee.id
    }), 200

@incidents_bp.route('/my', methods=['GET'])
@jwt_required()
def get_my_incidents():
    user_id = get_jwt_identity()
    assigned = Incident.query.filter_by(assigned_employee_id=user_id).order_by(Incident.incident_datetime.desc()).all()
    return jsonify(incident_list_schema.dump(assigned)), 200

@incidents_bp.route('/<int:incident_id>/complete', methods=['POST'])
@jwt_required()
def complete_incident(incident_id):
    user_id = int(get_jwt_identity())
    user = Employee.query.get(user_id)
    incident = Incident.query.get_or_404(incident_id)

    app.logger.warning(f"🧾 Запрос на завершение инцидента #{incident.id}")
    app.logger.warning(f"👤 Пользователь: id={user.id}, email={user.email}, role={user.role}")
    app.logger.warning(f"📌 Назначен сотрудник: id={incident.assigned_employee_id}")

    if incident.assigned_employee_id != user_id:
        app.logger.warning("❌ Отказано в доступе: пользователь не назначен на инцидент")
        return jsonify({"error": "You are not authorized to complete this incident"}), 403

    status = IncidentStatus.query.filter_by(name='завершён').first()
    if not status:
        app.logger.error("❌ Статус 'завершён' не найден")
        return jsonify({"error": "Status 'завершён' not found"}), 500

    try:
        # PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.add_font('DejaVu', '', os.path.join(app.root_path, 'static', 'fonts', 'DejaVuSans.ttf'), uni=True)
        pdf.set_font('DejaVu', '', 14)
        pdf.cell(200, 10, txt="Incident Resolution Report", ln=True, align="C")
        pdf.ln(10)
        pdf.set_font('DejaVu', '', 12)
        pdf.cell(200, 10, txt=f"Incident ID: {incident.id}", ln=True)
        pdf.cell(200, 10, txt=f"Title: {incident.title}", ln=True)
        pdf.cell(200, 10, txt=f"Type: {incident.incident_type}", ln=True)
        pdf.cell(200, 10, txt=f"Description: {incident.description or '-'}", ln=True)
        pdf.cell(200, 10, txt=f"Location: {incident.location.location_name}", ln=True)
        pdf.cell(200, 10, txt=f"Resolved by: {user.first_name} {user.last_name}", ln=True)
        pdf.cell(200, 10, txt=f"Resolved at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC", ln=True)

        reports_dir = os.path.join(app.root_path, 'static', 'reports')
        os.makedirs(reports_dir, exist_ok=True)
        pdf_path = os.path.join(reports_dir, f'incident-{incident.id}.pdf')
        pdf.output(pdf_path)

        incident.status_id = status.id
        incident.conclusion = f"/static/reports/incident-{incident.id}.pdf"
        db.session.commit()

        app.logger.info(f"✅ Инцидент #{incident.id} успешно завершён пользователем {user.email}")
        app.logger.info(f"📎 PDF: {incident.conclusion}")

        return jsonify({
            "message": f"Incident #{incident.id} resolved",
            "pdf_url": incident.conclusion
        }), 200

    except Exception as e:
        app.logger.exception(f"💥 Ошибка завершения инцидента #{incident.id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@incidents_bp.route('', methods=['OPTIONS'])
@incidents_bp.route('/<int:incident_id>', methods=['OPTIONS'])
def preflight_incident(incident_id=None):
    resp = make_response()
    resp.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
    resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    resp.headers['Access-Control-Allow-Headers'] = 'Authorization, Content-Type'
    resp.headers['Access-Control-Allow-Credentials'] = 'true'
    return resp, 200
