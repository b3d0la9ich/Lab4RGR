from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from extensions import db

class Employee(db.Model):
    __tablename__ = 'employees'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    phone = db.Column(db.String(20))
    role = db.Column(db.String(50))  # 'admin' или 'user'
    password = db.Column(db.String(200), nullable=False)

    assigned_incidents = db.relationship(
        'Incident',
        back_populates='assigned_employee',
        foreign_keys='Incident.assigned_employee_id',
        lazy='joined'
    )

    responses = db.relationship('IncidentResponse', backref='responder', lazy=True)


class Location(db.Model):
    __tablename__ = 'locations'
    id = db.Column(db.Integer, primary_key=True)
    location_name = db.Column(db.String(100), nullable=False)
    location_type = db.Column(db.String(50))

    incidents = db.relationship('Incident', backref='location', lazy=True)


class IncidentStatus(db.Model):
    __tablename__ = 'incident_statuses'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)

    incidents = db.relationship('Incident', backref='status', lazy=True)


class Incident(db.Model):
    __tablename__ = 'incidents'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    incident_type = db.Column(db.String(50), nullable=False)
    incident_datetime = db.Column(db.DateTime, default=datetime.utcnow)

    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'))
    assigned_employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'))

    status_id = db.Column(db.Integer, db.ForeignKey('incident_statuses.id'), nullable=False, default=1)

    conclusion = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    assigned_employee = db.relationship('Employee', back_populates='assigned_incidents', foreign_keys=[assigned_employee_id])
    responses = db.relationship('IncidentResponse', backref='incident', lazy=True)
    sources = db.relationship('IncidentSource', backref='incident', lazy=True)
    attachments = db.relationship('Attachment', backref='incident', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'incident_type': self.incident_type,
            'incident_datetime': self.incident_datetime.isoformat() if self.incident_datetime else None,
            'location': {
                'id': self.location.id,
                'location_name': self.location.location_name
            } if self.location else None,
            'status': {
                'id': self.status.id,
                'name': self.status.name
            } if self.status else None,
            'assigned_employee': {
                'id': self.assigned_employee.id,
                'first_name': self.assigned_employee.first_name,
                'last_name': self.assigned_employee.last_name,
                'email': self.assigned_employee.email
            } if self.assigned_employee else None,
            'conclusion': self.conclusion,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class IncidentResponse(db.Model):
    __tablename__ = 'incident_responses'
    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(db.Integer, db.ForeignKey('incidents.id'), nullable=False)
    action_taken = db.Column(db.Text, nullable=False)
    performed_by_id = db.Column(db.Integer, db.ForeignKey('employees.id'))
    response_datetime = db.Column(db.DateTime, default=datetime.utcnow)


class IncidentSource(db.Model):
    __tablename__ = 'incident_sources'
    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(db.Integer, db.ForeignKey('incidents.id'), nullable=False)
    source_type = db.Column(db.String(50))  # "человек", "система", "камера"
    source_description = db.Column(db.Text)


class Attachment(db.Model):
    __tablename__ = 'attachments'
    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(db.Integer, db.ForeignKey('incidents.id'), nullable=False)
    file_url = db.Column(db.Text, nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
