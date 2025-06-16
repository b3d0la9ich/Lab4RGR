from marshmallow_sqlalchemy import SQLAlchemyAutoSchema, auto_field
from marshmallow import fields
from models import Incident, Employee, IncidentStatus, Location, IncidentResponse, IncidentSource, Attachment
from extensions import db


# Вспомогательные схемы для вложенных объектов (read-only)
class EmployeeSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Employee
        load_instance = True
        sqla_session = db.session
        include_fk = True

    full_name = fields.Method("get_full_name")
    is_busy = fields.Method("get_is_busy")

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    def get_is_busy(self, obj):
        # Учитываем только инциденты, не завершённые
        return any(
            inc.status and inc.status.name.lower() != 'завершён'
            for inc in obj.assigned_incidents
        )


class IncidentStatusSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = IncidentStatus
        load_instance = True
        sqla_session = db.session


class LocationSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Location
        load_instance = True
        sqla_session = db.session


class IncidentResponseSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = IncidentResponse
        load_instance = True
        sqla_session = db.session
        include_fk = True

    responder = fields.Nested(EmployeeSchema, dump_only=True)


class IncidentSourceSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = IncidentSource
        load_instance = True
        sqla_session = db.session
        include_fk = True


class AttachmentSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Attachment
        load_instance = True
        sqla_session = db.session
        include_fk = True


# Основная схема для Incidents
class IncidentSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Incident
        load_instance = True
        sqla_session = db.session
        include_fk = True
        dump_only = ("id", "created_at", "updated_at")

    # Поля, которые можно передавать при создании/редактировании
    title = auto_field(required=True)
    description = auto_field()
    incident_type = auto_field()
    location_id = auto_field()
    status_id = auto_field()
    assigned_employee_id = auto_field()

    # Вложенные объекты только для отдачи
    assigned_employee = fields.Nested(EmployeeSchema, dump_only=True)
    status = fields.Nested(IncidentStatusSchema, dump_only=True)
    location = fields.Nested(LocationSchema, dump_only=True)
    responses = fields.Nested(IncidentResponseSchema, many=True, dump_only=True)
    sources = fields.Nested(IncidentSourceSchema, many=True, dump_only=True)
    attachments = fields.Nested(AttachmentSchema, many=True, dump_only=True)

