import os
import string
import random
from urllib.parse import urlparse

import click
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default_fallback_secret_key_for_dev')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///' + os.path.join(basedir, 'shortener.db'))
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


db = SQLAlchemy(app)


class Link(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    original_url = db.Column(db.String(2048), nullable=False)
    short_code = db.Column(db.String(10), unique=True, nullable=False, index=True)

    def __repr__(self):
        return f'<Link {self.short_code}>'


def generate_short_code(length=6):
    characters = string.ascii_letters + string.digits
    while True:
        short_code = ''.join(random.choice(characters) for _ in range(length))
        with app.app_context():
             existing_link = Link.query.filter_by(short_code=short_code).first()
        if not existing_link:
            return short_code

def is_valid_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme in ['http', 'https'], result.netloc])
    except ValueError:
        return False


@app.route('/', methods=['GET', 'POST'])
def index():
    """صفحه اصلی برای نمایش فرم و نتیجه"""
    short_url_display = None
    error_message = None

    if request.method == 'POST':
        original_url = request.form.get('original_url')

        if not original_url:
            error_message = "لطفاً یک URL وارد کنید."
        elif not is_valid_url(original_url):
             error_message = "ساختار URL وارد شده معتبر نیست (باید با http:// یا https:// شروع شود و دامنه داشته باشد)."
        else:
            existing_link = Link.query.filter_by(original_url=original_url).first()
            if existing_link:
                short_url_display = request.host_url + existing_link.short_code
                flash("این URL قبلاً کوتاه شده بود.", "info")
            else:
                short_code = generate_short_code()
                new_link = Link(original_url=original_url, short_code=short_code)
                db.session.add(new_link)
                try:
                    db.session.commit()
                    short_url_display = request.host_url + short_code
                    flash("لینک شما با موفقیت کوتاه شد!", "success")
                except Exception as e:
                    db.session.rollback()
                    error_message = f"خطا در ذخیره سازی لینک: {e}"
                    app.logger.error(f"Database commit failed: {e}")

    return render_template('index.html', short_url=short_url_display, error_message=error_message)

@app.route('/<short_code>')
def redirect_to_original(short_code):
    link = Link.query.filter_by(short_code=short_code).first()

    if link:
        return redirect(link.original_url)
    else:
        flash(f"کد کوتاه '{short_code}' یافت نشد.", "warning")
        return redirect(url_for('index'))

@app.cli.command('init-db')
def init_db_command():
    try:
        db.create_all()
        click.echo('Initialized the database.')
    except Exception as e:
        click.echo(f'Error initializing database: {e}')
