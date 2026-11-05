"""Computer Hub Check-in — application factory."""
import os

from flask import Flask, jsonify

from .services import HubError


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev"),
        DATABASE=os.path.join(app.instance_path, "hub.sqlite"),
    )
    if test_config:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)

    from . import db
    db.init_app(app)

    from .api import bp as api_bp
    from .web import bp as web_bp
    app.register_blueprint(api_bp)
    app.register_blueprint(web_bp)

    @app.errorhandler(HubError)
    def handle_hub_error(err: HubError):
        return jsonify(error=str(err)), err.status

    return app
