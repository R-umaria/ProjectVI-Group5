from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS

# Singletons (initialized in app factory)
db = SQLAlchemy()
migrate = Migrate()
cors = CORS()
