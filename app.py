# app.py

from flask import Flask, render_template, request, jsonify, send_from_directory
from routes.main_routes import MainRoutes
import os
from dotenv import load_dotenv
load_dotenv()

class FlaskApp:
    def __init__(self):
        # Configure the Flask app with static and template folders
        self.app = Flask(__name__,
                         static_folder='static',
                         template_folder='templates')
        # Configure the upload folder
        self.app.config['UPLOAD_FOLDER'] = os.path.join(self.app.root_path, 'uploads')
        self.register_routes()

    def register_routes(self):
        main_routes = MainRoutes(self.app)

        # Home route
        self.app.add_url_rule('/', 'index', main_routes.index)

        # Existing route
        self.app.add_url_rule('/submit_prompt', 'submit_prompt', main_routes.submit_prompt, methods=['POST'])

        # Upload route
        self.app.add_url_rule('/upload', 'upload', main_routes.upload, methods=['POST'])

        # Ask question route
        self.app.add_url_rule('/ask', 'ask', main_routes.ask, methods=['POST'])

        # Advanced Processing Route
        self.app.add_url_rule('/advanced_upload', 'advanced_upload', main_routes.advanced_upload, methods=['POST'])

    
    def run(self):
        self.app.run(debug=True)

if __name__ == '__main__':
    app_instance = FlaskApp()
    app_instance.run()
