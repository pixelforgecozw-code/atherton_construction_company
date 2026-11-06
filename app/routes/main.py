import os
import re
import smtplib
import uuid
from email.message import EmailMessage
from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename
from app import db
from app.models import Enquiry, Project

try:  # optional dependency: stricter checking when installed
    from email_validator import EmailNotValidError, validate_email
except ImportError:  # pragma: no cover - fallback keeps the site working without it
    validate_email = None

main_bp = Blueprint("main", __name__)
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "webp", "doc", "docx"}

SERVICES = [
    {"title": "Construction", "slug": "construction", "icon": "▦", "text": "Building works for homes and other structures, from foundations and walls through to a finished build, delivered to the agreed scope."},
    {"title": "Electrical", "slug": "electrical", "icon": "ϟ", "text": "Electrical installation work including conduit, wiring, and connection points for new builds and existing buildings."},
    {"title": "Renovation", "slug": "renovation", "icon": "↻", "text": "Renovation, extension, and improvement work to refresh, modernize, and make better use of existing buildings."},
    {"title": "Painting", "slug": "painting", "icon": "✎", "text": "Surface preparation, repairs, and painting to protect and refresh the interior and exterior of your property."},
    {"title": "Plumbing", "slug": "plumbing", "icon": "◉", "text": "Plumbing installation, fitting, and repair work for bathrooms, kitchens, and water systems."},
    {"title": "Roofing", "slug": "roofing", "icon": "⌂", "text": "Roof installation and repair, including tiling, sheeting, and guttering, with attention to safety and workmanship."},
]

def _services_with_images():
    """Attach an image to each service.

    Drop a photo named after the service slug (e.g. roofing.jpg) into
    app/static/images/services/ and it is used for that service.
    """
    folder = os.path.join(current_app.static_folder, "images", "services")
    result = []
    for service in SERVICES:
        image = None
        for ext in ("jpg", "jpeg", "png", "webp", "svg"):
            if os.path.exists(os.path.join(folder, f"{service['slug']}.{ext}")):
                image = f"{service['slug']}.{ext}"
                break
        result.append({**service, "image": image})
    return result

def _send_notification(enquiry):
    cfg = current_app.config
    if not (cfg.get("MAIL_SERVER") and cfg.get("MAIL_DEFAULT_SENDER") and cfg.get("COMPANY_NOTIFICATION_EMAIL")):
        return
    msg = EmailMessage()
    msg["Subject"] = f"New {enquiry.enquiry_type.title()} enquiry — Atherton Construction"
    msg["From"] = cfg["MAIL_DEFAULT_SENDER"]
    msg["To"] = cfg["COMPANY_NOTIFICATION_EMAIL"]
    msg.set_content(
        f"New website enquiry\n\nType: {enquiry.enquiry_type}\nName: {enquiry.full_name}\n"
        f"Email: {enquiry.email}\nPhone: {enquiry.phone or 'Not provided'}\n"
        f"Project: {enquiry.project_type or 'Not specified'}\nLocation: {enquiry.project_location or 'Not specified'}\n\n"
        f"Message:\n{enquiry.message}"
    )
    try:
        with smtplib.SMTP(cfg["MAIL_SERVER"], cfg["MAIL_PORT"], timeout=10) as server:
            if cfg["MAIL_USE_TLS"]:
                server.starttls()
            if cfg.get("MAIL_USERNAME"):
                server.login(cfg["MAIL_USERNAME"], cfg.get("MAIL_PASSWORD", ""))
            server.send_message(msg)
    except (OSError, smtplib.SMTPException):
        current_app.logger.exception("Could not send enquiry notification email.")

def _save_enquiry(enquiry_type):
    full_name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip()
    message = request.form.get("message", "").strip()
    if not full_name or not email or not message:
        flash("Please complete your name, email address, and message.", "error")
        return None
    if len(full_name) > 120 or len(email) > 160 or len(message) > 10000:
        flash("Some fields exceed the allowed length. Please review your entries.", "error")
        return None
    if validate_email is not None:
        try:
            email = validate_email(email, check_deliverability=False).normalized
        except EmailNotValidError:
            flash("Please enter a valid email address.", "error")
            return None
    elif not _EMAIL_RE.match(email):
        flash("Please enter a valid email address.", "error")
        return None

    attachment = request.files.get("attachment")
    filename = None
    if attachment and attachment.filename:
        safe_name = secure_filename(attachment.filename)
        ext = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else ""
        if ext not in ALLOWED_EXTENSIONS:
            flash("Attachment type not allowed. Use PDF, images, or DOC/DOCX files.", "error")
            return None
        # Unique name avoids overwriting; stored outside /static so it is not publicly reachable.
        filename = f"{uuid.uuid4().hex}_{safe_name}"
        attachment.save(os.path.join(current_app.config["ENQUIRY_UPLOAD_FOLDER"], filename))

    enquiry = Enquiry(
        enquiry_type=enquiry_type,
        full_name=full_name,
        company_name=request.form.get("company_name", "").strip()[:160] or None,
        phone=request.form.get("phone", "").strip()[:60] or None,
        email=email,
        project_location=request.form.get("project_location", "").strip()[:180] or None,
        project_type=request.form.get("project_type", "").strip()[:100] or None,
        budget=request.form.get("budget", "").strip()[:80] or None,
        expected_start=request.form.get("expected_start", "").strip()[:40] or None,
        message=message,
        attachment_filename=filename,
    )
    db.session.add(enquiry)
    db.session.commit()
    _send_notification(enquiry)
    return enquiry

@main_bp.route("/")
def home():
    projects = Project.query.filter_by(is_published=True).order_by(Project.created_at.desc()).limit(3).all()
    return render_template("index.html", services=_services_with_images(), projects=projects)

@main_bp.route("/about")
def about():
    return render_template("about.html")

@main_bp.route("/services")
def services():
    return render_template("services.html", services=_services_with_images())

@main_bp.route("/projects")
def projects():
    category = request.args.get("category", "").strip()
    search = request.args.get("q", "").strip()
    query = Project.query.filter_by(is_published=True)
    if category and category != "All":
        query = query.filter_by(category=category)
    if search:
        query = query.filter(Project.title.ilike(f"%{search}%"))
    items = query.order_by(Project.created_at.desc()).all()
    categories = ["All"] + [row[0] for row in db.session.query(Project.category).filter_by(is_published=True).distinct().order_by(Project.category).all()]
    return render_template("projects.html", projects=items, categories=categories, selected_category=category or "All", search=search)

@main_bp.route("/projects/<int:project_id>")
def project_detail(project_id):
    project = Project.query.filter_by(id=project_id, is_published=True).first_or_404()
    related = Project.query.filter(Project.id != project.id, Project.category == project.category, Project.is_published.is_(True)).limit(3).all()
    return render_template("project_detail.html", project=project, related=related)

@main_bp.route("/team")
def team():
    return render_template("team.html")

@main_bp.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        enquiry = _save_enquiry("contact")
        if enquiry:
            flash("Thank you. Your message has been received. Our team will review it.", "success")
            return redirect(url_for("main.contact"))
    return render_template("contact.html")

@main_bp.route("/request-a-quote", methods=["GET", "POST"])
def quote():
    if request.method == "POST":
        enquiry = _save_enquiry("quote")
        if enquiry:
            flash("Thank you. Your quotation request has been received.", "success")
            return redirect(url_for("main.quote"))
    return render_template("quote.html")

@main_bp.route("/privacy")
def privacy():
    return render_template("privacy.html")

@main_bp.route("/terms")
def terms():
    return render_template("terms.html")
