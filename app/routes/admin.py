import os
import uuid
from urllib.parse import urlsplit
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from app import db
from app.models import AdminUser, Enquiry, Project

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

def _safe_next(target):
    """Only allow redirects to local paths (prevents open-redirect after login)."""
    if not target:
        return None
    parts = urlsplit(target)
    if parts.scheme or parts.netloc or not target.startswith("/") or target.startswith("//") or "\\" in target:
        return None
    return target

@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = AdminUser.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash("Welcome back.", "success")
            return redirect(_safe_next(request.args.get("next")) or url_for("admin.dashboard"))
        flash("Invalid username or password.", "error")
    return render_template("admin/login.html")

@admin_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("main.home"))

@admin_bp.route("/")
@login_required
def dashboard():
    enquiries = Enquiry.query.order_by(Enquiry.created_at.desc()).limit(10).all()
    return render_template(
        "admin/dashboard.html",
        project_count=Project.query.count(),
        enquiry_count=Enquiry.query.count(),
        new_count=Enquiry.query.filter_by(status="New").count(),
        enquiries=enquiries,
    )

@admin_bp.route("/projects")
@login_required
def projects():
    items = Project.query.order_by(Project.created_at.desc()).all()
    return render_template("admin/projects.html", projects=items)

@admin_bp.route("/projects/new", methods=["GET", "POST"])
@admin_bp.route("/projects/<int:project_id>/edit", methods=["GET", "POST"])
@login_required
def edit_project(project_id=None):
    project = db.session.get(Project, project_id) if project_id else Project()
    if project_id and not project:
        abort(404)
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        summary = request.form.get("summary", "").strip()
        if not title or not summary:
            flash("Project title and summary are required.", "error")
        else:
            project.title = title[:160]
            project.category = request.form.get("category", "Construction").strip()[:80] or "Construction"
            project.location = request.form.get("location", "").strip()[:160] or None
            project.summary = summary[:320]
            project.description = request.form.get("description", "").strip()[:10000] or None
            project.status = request.form.get("status", "Showcase").strip()[:50]
            project.completion_year = request.form.get("completion_year", "").strip()[:10] or None
            project.is_published = request.form.get("is_published") == "on"
            image = request.files.get("image")
            if image and image.filename:
                safe_name = secure_filename(image.filename)
                ext = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else ""
                if ext not in ALLOWED_IMAGE_EXTENSIONS:
                    flash("Use PNG, JPG, JPEG, or WEBP project images.", "error")
                    return render_template("admin/project_form.html", project=project)
                filename = f"{uuid.uuid4().hex}_{safe_name}"
                image.save(os.path.join(current_app.config["UPLOAD_FOLDER"], filename))
                project.image_filename = filename
            if not project.id:
                db.session.add(project)
            db.session.commit()
            flash("Project saved.", "success")
            return redirect(url_for("admin.projects"))
    return render_template("admin/project_form.html", project=project)

@admin_bp.route("/projects/<int:project_id>/delete", methods=["POST"])
@login_required
def delete_project(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        abort(404)
    db.session.delete(project)
    db.session.commit()
    flash("Project deleted.", "success")
    return redirect(url_for("admin.projects"))

@admin_bp.route("/enquiries")
@login_required
def enquiries():
    items = Enquiry.query.order_by(Enquiry.created_at.desc()).all()
    return render_template("admin/enquiries.html", enquiries=items)

@admin_bp.route("/enquiries/<int:enquiry_id>/attachment")
@login_required
def enquiry_attachment(enquiry_id):
    enquiry = db.session.get(Enquiry, enquiry_id)
    if not enquiry or not enquiry.attachment_filename:
        abort(404)
    return send_from_directory(
        current_app.config["ENQUIRY_UPLOAD_FOLDER"],
        enquiry.attachment_filename,
        as_attachment=True,
        download_name=enquiry.attachment_filename.split("_", 1)[-1],
    )

@admin_bp.route("/enquiries/<int:enquiry_id>/status", methods=["POST"])
@login_required
def update_enquiry(enquiry_id):
    enquiry = db.session.get(Enquiry, enquiry_id)
    if not enquiry:
        abort(404)
    allowed = {"New", "Under Review", "Quotation in Progress", "Quotation Sent", "Approved", "Declined", "Completed"}
    status = request.form.get("status", "")
    if status not in allowed:
        flash("Invalid enquiry status.", "error")
    else:
        enquiry.status = status
        db.session.commit()
        flash("Enquiry status updated.", "success")
    return redirect(url_for("admin.enquiries"))
