import os
from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager
from flask.ext.openid import OpenID

from config import *
from pagination import Pagination

app = Flask(__name__)

app.config.from_object('config')

lm = LoginManager()
oid = OpenID(app, os.path.join(basedir, 'tmp'))
lm.login_view = 'login'
lm.init_app(app)
db = SQLAlchemy(app)

# Blueprints
from oscars_te.views import data
from oscars_te.views import monitor
from oscars_te.views import plot
from oscars_te.views import trigger

app.register_blueprint(data.bp)
app.register_blueprint(monitor.bp)
app.register_blueprint(plot.bp)
app.register_blueprint(trigger.bp)

from oscars_te.views import base
from oscars_te.views import auth
