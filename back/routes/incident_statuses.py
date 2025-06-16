# routes/incident_statuses.py
from flask import Blueprint, jsonify
from models import IncidentStatus
from schemas.incident_schema import IncidentStatusSchema
from flask_jwt_extended import jwt_required

incident_statuses_bp = Blueprint('incident_statuses', __name__)
status_schema = IncidentStatusSchema()
status_list_schema = IncidentStatusSchema(many=True)

@incident_statuses_bp.route('', methods=['GET', 'OPTIONS'])
@jwt_required()
def get_all_statuses():
    statuses = IncidentStatus.query.all()
    return jsonify(status_list_schema.dump(statuses)), 200
