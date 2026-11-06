import os
from pathlib import Path
from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv

load_dotenv()
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY", "dev-only-change-me"),
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", "sqlite:///atherton.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MAX_CONTENT_LENGTH=8 * 1024 * 1024,
        UPLOAD_FOLDER=os.path.join(app.root_path, "static", "uploads"),
        ENQUIRY_UPLOAD_FOLDER=os.path.join(app.instance_path, "enquiry_uploads"),
        DEFAULT_ADMIN_USERNAME=os.getenv("ADMIN_USERNAME", "admin"),
        DEFAULT_ADMIN_PASSWORD=os.getenv("ADMIN_PASSWORD", "Atherton@2026!"),
        DEBUG=os.getenv("DEBUG", "false").lower() == "true",
        COMPANY_NAME="Atherton Construction Company",
        COMPANY_PHONES=[p.strip() for p in os.getenv("COMPANY_PHONES", "+263 78 820 3192, +263 77 919 5531").split(",") if p.strip()],
        WHATSAPP_NUMBER="".join(c for c in os.getenv("WHATSAPP_NUMBER", "+263 77 919 5531") if c.isdigit()),
        FACEBOOK_URL=os.getenv("FACEBOOK_URL", "https://www.facebook.com/share/19r4oPeuja/"),
        COMPANY_EMAIL=os.getenv("COMPANY_EMAIL", ""),
        COMPANY_ADDRESS=os.getenv("COMPANY_ADDRESS", "65 Second Street Avenues, Harare, Zimbabwe"),
        COMPANY_HOURS=os.getenv("COMPANY_HOURS", ""),
        MAIL_SERVER=os.getenv("MAIL_SERVER", ""),
        MAIL_PORT=int(os.getenv("MAIL_PORT", "587")),
        MAIL_USE_TLS=os.getenv("MAIL_USE_TLS", "true").lower() == "true",
        MAIL_USERNAME=os.getenv("MAIL_USERNAME", ""),
        MAIL_PASSWORD=os.getenv("MAIL_PASSWORD", ""),
        MAIL_DEFAULT_SENDER=os.getenv("MAIL_DEFAULT_SENDER", ""),
        COMPANY_NOTIFICATION_EMAIL=os.getenv("COMPANY_NOTIFICATION_EMAIL", ""),
    )
    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["ENQUIRY_UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    login_manager.login_view = "admin.login"
    login_manager.login_message_category = "info"

    from app.models import AdminUser, Project, Enquiry
    from app.routes.main import main_bp
    from app.routes.admin import admin_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(AdminUser, int(user_id))

    def ensure_default_admin():
        """Create the default administrator if no admin account exists yet.

        Returns True when an account was created.
        """
        from werkzeug.security import generate_password_hash
        if AdminUser.query.count() > 0:
            return False
        db.session.add(AdminUser(
            username=app.config["DEFAULT_ADMIN_USERNAME"],
            password_hash=generate_password_hash(app.config["DEFAULT_ADMIN_PASSWORD"]),
        ))
        db.session.commit()
        return True

    def setup_database():
        """Create tables and the default admin (safe to run repeatedly)."""
        db.create_all()
        return ensure_default_admin()

    app.setup_database = setup_database

    @app.cli.command("init-db")
    def init_db_command():
        """Create all database tables and the default admin account."""
        created = setup_database()
        print("Database tables created.")
        if created:
            print(f"Default admin created -> username: {app.config['DEFAULT_ADMIN_USERNAME']}  "
                  f"password: {app.config['DEFAULT_ADMIN_PASSWORD']}")
            print("Sign in at /admin/login and change this password with: flask --app run.py reset-admin")

    @app.cli.command("create-admin")
    def create_admin_command():
        """Create an additional administrator account interactively."""
        import getpass
        from werkzeug.security import generate_password_hash
        db.create_all()
        username = input("Admin username: ").strip()
        if not username:
            print("Username cannot be blank.")
            return
        if AdminUser.query.filter_by(username=username).first():
            print("That username already exists.")
            return
        password = getpass.getpass("Password (minimum 12 characters): ")
        confirm = getpass.getpass("Confirm password: ")
        if len(password) < 12 or password != confirm:
            print("Passwords must match and contain at least 12 characters.")
            return
        db.session.add(AdminUser(username=username, password_hash=generate_password_hash(password)))
        db.session.commit()
        print("Administrator created.")

    @app.cli.command("reset-admin")
    def reset_admin_command():
        """Change an administrator's password (use this to replace the default)."""
        import getpass
        from werkzeug.security import generate_password_hash
        db.create_all()
        username = input(f"Admin username [{app.config['DEFAULT_ADMIN_USERNAME']}]: ").strip() \
            or app.config["DEFAULT_ADMIN_USERNAME"]
        user = AdminUser.query.filter_by(username=username).first()
        if not user:
            print("No admin with that username.")
            return
        password = getpass.getpass("New password (minimum 12 characters): ")
        confirm = getpass.getpass("Confirm password: ")
        if len(password) < 12 or password != confirm:
            print("Passwords must match and contain at least 12 characters.")
            return
        user.password_hash = generate_password_hash(password)
        db.session.commit()
        print("Password updated.")

    @app.context_processor
    def inject_globals():
        from datetime import datetime
        return {"current_year": datetime.now().year}

    @app.errorhandler(413)
    def too_large(_error):
        from flask import render_template
        return render_template("errors/413.html"), 413

    @app.errorhandler(404)
    def not_found(_error):
        from flask import render_template
        return render_template("errors/404.html"), 404

    return app
