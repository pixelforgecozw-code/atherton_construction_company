# Atherton Construction Company Website

A responsive construction company website built with HTML, CSS, JavaScript, Python Flask, and SQLite. It includes public pages, project filtering, contact and quotation forms, and a protected admin dashboard for managing projects and reviewing enquiries.

## Features

- Responsive homepage using Atherton's teal-and-gold brand palette
- About, Services, Projects, Project Details, Team, Contact, and Request a Quote pages
- Project category filtering and search
- Contact and quotation enquiry forms stored in the database
- Admin login and dashboard
- Admin project creation, editing, and deletion
- Enquiry status updates
- CSRF protection, password hashing, server-side validation, upload limits, and configurable secrets
- Optional SMTP email notification configuration
- SQLite for local development; configurable database URL for PostgreSQL/MySQL deployments

## Requirements

- Python 3.10+
- pip

## Run locally

1. Extract the project folder.
2. Create and activate a virtual environment:

   **Windows PowerShell**
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   **macOS/Linux**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Copy `.env.example` to `.env`. Set `SECRET_KEY` to a long random value. For local development, `DEBUG=true` is acceptable; set it to `false` for production.

5. Start the site:

   ```bash
   python run.py
   ```

   On first run this automatically creates the database tables and a **default administrator account** (see below). You can also do this step on its own with `flask --app run.py init-db`.

6. Open `http://127.0.0.1:5000`.

## Admin access

Visit `/admin/login` and sign in with the default account:

| Username | Password |
|----------|----------|
| `admin`  | `Atherton@2026!` |

The default is created only when no admin exists yet, and can be overridden with `ADMIN_USERNAME` / `ADMIN_PASSWORD` in `.env` before first run.

**Change the default password before going live:**

```bash
flask --app run.py reset-admin      # change an existing admin's password
flask --app run.py create-admin     # add another administrator
```

Passwords are hashed before they are stored, and the dashboard is protected by Flask-Login.

## Add company content

- The logo is `app/static/images/atherton-logo.png` (cropped wide version). Replace it with an official high-resolution transparent version if available.
- Replace demonstration project images and text with real, approved company information.
- Company contact details are set in `.env`: `COMPANY_PHONES` (comma-separated), `WHATSAPP_NUMBER`, `FACEBOOK_URL`, `COMPANY_ADDRESS`, `COMPANY_EMAIL` and `COMPANY_HOURS`. They appear in the footer and on the Contact page; the floating WhatsApp button links to `WHATSAPP_NUMBER`.
- The service list (Construction, Electrical, Renovation, Painting, Plumbing, Roofing) is in `app/routes/main.py`. Each service's picture is `app/static/images/services/<slug>.jpg` (e.g. `roofing.jpg`); replace the file to change it.
- No fabricated project statistics, certifications, testimonials, staff identities, or contact details are presented as verified facts.

## Email notifications

To send enquiry notifications, configure the SMTP settings in `.env`, including `COMPANY_NOTIFICATION_EMAIL`. If email settings are blank, enquiries will still be saved to the database and visible in the admin dashboard.

## Production checklist

- Set a strong, unique `SECRET_KEY` and change the default admin password.
- Quote/contact attachments are stored privately in `instance/enquiry_uploads/` and are only downloadable by signed-in admins.
- Set `DEBUG=false`.
- Use HTTPS.
- Use PostgreSQL or MySQL for a multi-user production deployment.
- Configure persistent storage for uploaded files, backups, and database data.
- Configure SMTP and verify the notification recipient.
- Add rate limiting, monitoring, backups, and a production WSGI server such as Gunicorn.
- Review privacy, terms, and data-retention policies before launch.
- Replace all sample content and verify every service and company claim.
