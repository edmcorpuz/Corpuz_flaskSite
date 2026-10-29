"""Lecture 05–07 Flask app.

Run: flask --app flask_site run
Test: python -m unittest discover -s tests -v

This is a shared classroom demo, not an authenticated multi-user service.
Set a persistent SECRET_KEY environment variable before any deployment.
"""

import os
import secrets

from flask import Flask, flash, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()


class Item(db.Model):
    idNum = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        SQLALCHEMY_DATABASE_URI="sqlite:///items.db",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MAX_CONTENT_LENGTH=16 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("FLASK_SITE_ENV") == "production",
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    CSRFProtect(app)

    with app.app_context():
        db.create_all()

    def submitted_name():
        name = request.form.get("name", "").strip()
        if not name:
            return name, "Please enter an item name."
        if len(name) > 100:
            return name, "Item names must be 100 characters or fewer."
        return name, None

    @app.route("/")
    def index():
        items = db.session.execute(
            db.select(Item).order_by(Item.idNum)
        ).scalars().all()
        return render_template("index.html", items=items)

    @app.route("/hello")
    @app.route("/hello/")
    @app.route("/hello/<user_name>")
    def hello(user_name=None):
        # Jinja autoescapes user input in HTML templates.
        return render_template("home.html", user=user_name)

    @app.route("/create", methods=["GET", "POST"])
    def create():
        name, error = "", None
        if request.method == "POST":
            name, error = submitted_name()
            if error is None:
                db.session.add(Item(name=name))
                db.session.commit()
                flash("Item created. One less thing to remember.")
                return redirect(url_for("index"))
        return render_template("create.html", name=name, error=error), (
            400 if error else 200
        )

    @app.route("/update/<int:idNum>", methods=["GET", "POST"])
    def update(idNum):
        item = db.get_or_404(Item, idNum)
        name, error = item.name, None
        if request.method == "POST":
            name, error = submitted_name()
            if error is None:
                item.name = name
                db.session.commit()
                flash("Changes saved.")
                return redirect(url_for("index"))
        return render_template(
            "update.html", item=item, name=name, error=error
        ), (400 if error else 200)

    @app.route("/delete/<int:idNum>", methods=["POST"])
    def delete(idNum):
        item = db.get_or_404(Item, idNum)
        db.session.delete(item)
        db.session.commit()
        flash("Item deleted.")
        return redirect(url_for("index"))

    return app


app = create_app()


if __name__ == "__main__":
    app.run()
