"""Regression checks for the lecture routes, forms, and SQLite persistence."""

import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import quote

from flask_site import Item, create_app, db


class FlaskSiteTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "unit-test-only-not-a-deployment-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        })
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def token(self, client=None):
        page = (client or self.client).get("/create").get_data(as_text=True)
        return re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)

    def post(self, path, data=None):
        return self.client.post(path, data={**(data or {}), "csrf_token": self.token()})

    def add_item(self, name="Read the Flask slides"):
        response = self.post("/create", {"name": name})
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            return db.session.execute(db.select(Item)).scalar_one().idNum

    def item_names(self):
        with self.app.app_context():
            return list(db.session.execute(db.select(Item.name)).scalars())

    def test_empty_index(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"No items yet", response.data)

    def test_greeting_routes(self):
        for path, greeting in [
            ("/hello", b"Hello world!"),
            ("/hello/", b"Hello world!"),
            ("/hello/Corpuz", b"Hello Corpuz!"),
        ]:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertIn(greeting, response.data)

    def test_greeting_escapes_url_input(self):
        payload = "<img src=x onerror=alert(1)>"
        response = self.client.get("/hello/" + quote(payload, safe=""))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(payload.encode(), response.data)
        self.assertIn(b"&lt;img", response.data)

    def test_create_form(self):
        response = self.client.get("/create")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'name="name"', response.data)
        self.assertIn(b'name="csrf_token"', response.data)

    def test_create_trims_and_redirects(self):
        response = self.post("/create", {"name": "  New item  "})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/")
        self.assertEqual(self.item_names(), ["New item"])
        self.assertIn(b"New item", self.client.get("/").data)

    def test_create_rejects_missing_blank_and_overlong_names(self):
        for data in [{}, {"name": ""}, {"name": "   "}, {"name": "x" * 101}]:
            with self.subTest(data=data):
                response = self.post("/create", data)
                self.assertEqual(response.status_code, 400)
                self.assertIn(b'role="alert"', response.data)
                self.assertEqual(self.item_names(), [])

    def test_name_length_boundary(self):
        self.add_item("x" * 100)
        self.assertEqual(self.item_names(), ["x" * 100])

    def test_update_form_and_save(self):
        item_id = self.add_item()
        page = self.client.get(f"/update/{item_id}")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'value="Read the Flask slides"', page.data)
        response = self.post(f"/update/{item_id}", {"name": "  Completed  "})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.item_names(), ["Completed"])

    def test_invalid_update_preserves_original(self):
        item_id = self.add_item()
        for data in [{}, {"name": " "}, {"name": "x" * 101}]:
            with self.subTest(data=data):
                response = self.post(f"/update/{item_id}", data)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(self.item_names(), ["Read the Flask slides"])

    def test_delete(self):
        item_id = self.add_item()
        response = self.post(f"/delete/{item_id}")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/")
        self.assertEqual(self.item_names(), [])

    def test_delete_get_is_not_allowed(self):
        item_id = self.add_item()
        self.assertEqual(self.client.get(f"/delete/{item_id}").status_code, 405)
        self.assertEqual(len(self.item_names()), 1)

    def test_missing_items_return_404(self):
        self.assertEqual(self.client.get("/update/999").status_code, 404)
        self.assertEqual(self.post("/update/999", {"name": "Unknown"}).status_code, 404)
        self.assertEqual(self.post("/delete/999").status_code, 404)

    def test_csrf_required_for_all_mutations(self):
        item_id = self.add_item()
        for path in ["/create", f"/update/{item_id}", f"/delete/{item_id}"]:
            for extra in [{}, {"csrf_token": "invalid"}]:
                with self.subTest(path=path, extra=extra):
                    response = self.client.post(path, data={"name": "Changed", **extra})
                    self.assertEqual(response.status_code, 400)
        self.assertEqual(self.item_names(), ["Read the Flask slides"])

    def test_saved_names_are_escaped(self):
        payload = '<script>alert("x")</script>'
        item_id = self.add_item(payload)
        for path in ["/", f"/update/{item_id}"]:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertNotIn(payload.encode(), response.data)
                self.assertIn(b"&lt;script&gt;", response.data)

    def test_delete_confirmation_is_wired(self):
        self.add_item()
        self.assertIn(b"data-confirm-delete", self.client.get("/").data)
        response = self.client.get("/static/js/site.js")
        self.assertIn(b"window.confirm", response.data)
        self.assertIn(b"event.preventDefault()", response.data)
        response.close()

    def test_templates_use_local_assets(self):
        page = self.client.get("/hello").get_data(as_text=True)
        for path in [
            "/static/css/bootstrap.min.css", "/static/css/test.css",
            "/static/js/bootstrap.bundle.min.js", "/static/js/site.js",
            "/static/favicon.svg",
        ]:
            with self.subTest(path=path):
                self.assertIn(path, page)
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertGreater(len(response.data), 20)
                response.close()

    def test_create_feedback_and_shared_demo_notice(self):
        response = self.client.post("/create", data={
            "name": "A fresh idea", "csrf_token": self.token(),
        }, follow_redirects=True)
        self.assertIn(b"Item created. One less thing to remember.", response.data)
        self.assertIn(b"Shared classroom demo", response.data)
        self.assertNotIn(b"Item created.", self.client.get("/").data)

    def test_search_markup_escapes_item_names(self):
        self.add_item('A "quoted" idea')
        page = self.client.get("/")
        self.assertIn(b'id="item-search"', page.data)
        self.assertIn(b'data-item-name="A &#34;quoted&#34; idea"', page.data)
        self.assertIn(b'id="search-status"', page.data)

    def test_production_cookies_are_secure(self):
        with patch.dict("os.environ", {"FLASK_SITE_ENV": "production"}):
            app = create_app({
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            })
        try:
            response = app.test_client().get("/create", base_url="https://example.test")
            self.assertIn("Secure", response.headers["Set-Cookie"])
            self.assertIn("HttpOnly", response.headers["Set-Cookie"])
            self.assertIn("SameSite=Lax", response.headers["Set-Cookie"])
        finally:
            with app.app_context():
                db.session.remove()
                db.engine.dispose()

    def test_sqlite_persists_between_app_instances(self):
        with tempfile.TemporaryDirectory() as directory:
            config = {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{Path(directory) / 'items.db'}",
            }
            first = create_app(config)
            with first.app_context():
                db.session.add(Item(name="Persistent item"))
                db.session.commit()
                db.session.remove()
                db.engine.dispose()
            second = create_app(config)
            with second.app_context():
                self.assertEqual(db.session.execute(db.select(Item.name)).scalar_one(), "Persistent item")
                db.session.remove()
                db.engine.dispose()


if __name__ == "__main__":
    unittest.main()
