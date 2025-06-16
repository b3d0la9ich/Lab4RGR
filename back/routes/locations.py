# routes/locations.py
from flask import Blueprint, jsonify
from models import Location
from schemas.incident_schema import LocationSchema
from flask_jwt_extended import jwt_required

locations_bp = Blueprint('locations', __name__)

location_schema = LocationSchema()
location_list_schema = LocationSchema(many=True)

# 🔍 Получить все локации
@locations_bp.route('', methods=['GET', 'OPTIONS'])
@jwt_required()
def get_locations():
    print("📥 GET /api/locations")
    locations = Location.query.all()
    return jsonify(location_list_schema.dump(locations)), 200
