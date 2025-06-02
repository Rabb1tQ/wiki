from flask import Flask
from extensions import es, md
from views.main import main_bp
from views.import_zip import import_zip_bp
import os


def create_app():
    app = Flask(__name__)
    app.config['UPLOAD_FOLDER'] = 'static/uploads'
    # 这里es和md是全局单例，直接用
    app.register_blueprint(main_bp)
    app.register_blueprint(import_zip_bp)
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
