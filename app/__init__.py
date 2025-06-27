from flask import Flask
from .route import music_bp, health_bp


def create_app():
    app = Flask(__name__)

    app.register_blueprint(music_bp, url_prefix='/api')
    app.register_blueprint(health_bp, url_prefix='/api')

    return app
