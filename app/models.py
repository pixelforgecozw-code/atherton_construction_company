from datetime import datetime, timezone
from flask_login import UserMixin
from app import db


def _utcnow():
    """Naive UTC timestamp (SQLite stores naive datetimes)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AdminUser(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    category = db.Column(db.String(80), nullable=False, default="Construction")
    location = db.Column(db.String(160), nullable=True)
    summary = db.Column(db.String(320), nullable=False)
    description = db.Column(db.Text, nullable=True)
    image_filename = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(50), nullable=False, default="Showcase")
    completion_year = db.Column(db.String(10), nullable=True)
    is_published = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)

class Enquiry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    enquiry_type = db.Column(db.String(30), nullable=False, default="contact")
    full_name = db.Column(db.String(120), nullable=False)
    company_name = db.Column(db.String(160), nullable=True)
    phone = db.Column(db.String(60), nullable=True)
    email = db.Column(db.String(160), nullable=False)
    project_location = db.Column(db.String(180), nullable=True)
    project_type = db.Column(db.String(100), nullable=True)
    budget = db.Column(db.String(80), nullable=True)
    expected_start = db.Column(db.String(40), nullable=True)
    message = db.Column(db.Text, nullable=False)
    attachment_filename = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(40), nullable=False, default="New")
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)
