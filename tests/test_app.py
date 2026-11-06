import os
import tempfile
import unittest
from app import create_app, db
from app.models import AdminUser, Enquiry, Project
from werkzeug.security import generate_password_hash

class AthertonAppTestCase(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.app = create_app({
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///" + self.db_path,
            "UPLOAD_FOLDER": tempfile.mkdtemp(),
            "ENQUIRY_UPLOAD_FOLDER": tempfile.mkdtemp(),
        })
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            db.session.add(AdminUser(username="tester", password_hash=generate_password_hash("a-very-long-test-password")))
            db.session.add(Project(title="Test project", category="Construction", summary="A test project", is_published=True))
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_homepage_loads(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Building today", response.data)

    def test_projects_page_loads(self):
        response = self.client.get("/projects")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Test project", response.data)

    def test_footer_uses_white_logo_without_box(self):
        html = self.client.get("/").data.decode()
        self.assertIn("images/atherton-logo-white.png", html)
        self.assertEqual(self.client.get("/static/images/atherton-logo-white.png").status_code, 200)
        css = self.client.get("/static/css/style.css").data.decode()
        self.assertNotIn(".footer-brand img{width:235px;max-height:95px;object-fit:contain;background:#fff", css)

    def test_privacy_policy_content(self):
        r = self.client.get("/privacy")
        self.assertEqual(r.status_code, 200)
        html = r.data.decode()
        for text in ("Information we collect", "Cookies", "Third-party services", "Your rights and choices",
                     "65 Second Street Avenues, Harare, Zimbabwe", "+263 71 503 0000", "wa.me/263779195531"):
            self.assertIn(text, html)
        self.assertNotIn("starter policy", html)

    def test_approach_section_uses_site_photo(self):
        css = self.client.get("/static/css/style.css").data.decode()
        self.assertIn("atherton-approach.jpg", css)
        self.assertNotIn("photo-1504307651254", css)
        self.assertEqual(self.client.get("/static/images/atherton-approach.jpg").status_code, 200)

    def test_team_page_shows_team_photo(self):
        html = self.client.get("/team").data.decode()
        self.assertIn("images/team-on-site.jpg", html)
        self.assertEqual(self.client.get("/static/images/team-on-site.jpg").status_code, 200)

    def test_contact_details_and_whatsapp_button(self):
        for path in ("/", "/contact", "/services"):
            html = self.client.get(path).data.decode()
            self.assertIn('href="https://wa.me/263779195531', html, path)
            self.assertIn("whatsapp-float", html, path)
            self.assertIn('href="tel:+263715030000"', html, path)
            self.assertIn('href="tel:+263779195531"', html, path)
            self.assertIn("65 Second Street Avenues, Harare, Zimbabwe", html, path)
        self.assertIn("+263 71 503 0000", self.client.get("/contact").data.decode())

    def test_facebook_icon_links_to_page(self):
        for path in ("/", "/contact", "/privacy"):
            html = self.client.get(path).data.decode()
            self.assertIn("facebook-float", html, path)
            self.assertIn('href="https://www.facebook.com/share/19r4oPeuja/"', html, path)

    def test_contact_submission_is_saved(self):
        response = self.client.post("/contact", data={
            "full_name": "Test User",
            "email": "test@example.com",
            "message": "Please contact me",
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            self.assertEqual(Enquiry.query.count(), 1)

    def test_admin_login(self):
        response = self.client.post("/admin/login", data={
            "username": "tester",
            "password": "a-very-long-test-password",
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Dashboard", response.data)

    def test_services_show_pictures(self):
        html = self.client.get("/services").data.decode()
        for slug in ("construction", "electrical", "renovation", "painting", "plumbing", "roofing"):
            self.assertIn(f"images/services/{slug}.jpg", html)
            self.assertEqual(self.client.get(f"/static/images/services/{slug}.jpg").status_code, 200)
        for title in ("Construction", "Electrical", "Renovation", "Painting", "Plumbing", "Roofing"):
            self.assertIn(f"<h2>{title}</h2>", html)
        for old in ("Residential Construction", "Civil &amp; Structural", "Project Management"):
            self.assertNotIn(old, html)

    def test_invalid_email_rejected(self):
        self.client.post("/contact", data={"full_name": "A", "email": "not-an-email", "message": "hi"})
        with self.app.app_context():
            self.assertEqual(Enquiry.query.count(), 0)

    def test_login_next_blocks_external_redirect(self):
        data = {"username": "tester", "password": "a-very-long-test-password"}
        for bad in ("https://evil.example", "//evil.example", "/\\evil.example"):
            self.client.get("/admin/logout")
            r = self.client.post("/admin/login?next=" + bad, data=data)
            self.assertEqual(r.status_code, 302)
            self.assertNotIn("evil", r.headers["Location"])
            self.client.post("/admin/logout")
        r = self.client.post("/admin/login?next=/admin/projects", data=data)
        self.assertTrue(r.headers["Location"].endswith("/admin/projects"))

    def test_admin_pages_require_login(self):
        for path in ("/admin/", "/admin/projects", "/admin/enquiries", "/admin/enquiries/1/attachment"):
            r = self.client.get(path)
            self.assertEqual(r.status_code, 302, path)
            self.assertIn("/admin/login", r.headers["Location"])

    def test_attachment_is_private_and_admin_downloadable(self):
        import io
        r = self.client.post("/request-a-quote", data={
            "full_name": "Q", "email": "q@example.com", "message": "plans attached",
            "attachment": (io.BytesIO(b"%PDF-1.4 test"), "plan.pdf"),
        }, content_type="multipart/form-data")
        self.assertEqual(r.status_code, 302)
        with self.app.app_context():
            enquiry = Enquiry.query.one()
            stored = enquiry.attachment_filename
            self.assertTrue(os.path.exists(os.path.join(self.app.config["ENQUIRY_UPLOAD_FOLDER"], stored)))
            self.assertFalse(os.path.exists(os.path.join(self.app.config["UPLOAD_FOLDER"], stored)))
        self.assertEqual(self.client.get(f"/admin/enquiries/{enquiry.id}/attachment").status_code, 302)
        self.client.post("/admin/login", data={"username": "tester", "password": "a-very-long-test-password"})
        r = self.client.get(f"/admin/enquiries/{enquiry.id}/attachment")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, b"%PDF-1.4 test")

    def test_default_admin_seeded_once(self):
        app = create_app({
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "UPLOAD_FOLDER": tempfile.mkdtemp(),
            "ENQUIRY_UPLOAD_FOLDER": tempfile.mkdtemp(),
        })
        with app.app_context():
            self.assertTrue(app.setup_database())
            self.assertFalse(app.setup_database())  # idempotent
            self.assertEqual(AdminUser.query.count(), 1)
        client = app.test_client()
        client.application.config["WTF_CSRF_ENABLED"] = False
        r = client.post("/admin/login", data={"username": "admin", "password": "Atherton@2026!"}, follow_redirects=True)
        self.assertIn(b"Dashboard", r.data)


if __name__ == "__main__":
    unittest.main()
