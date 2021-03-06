import os
from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager
from flask.ext.openid import OpenID
from flask.ext.bootstrap import Bootstrap

from config import *
from pagination import Pagination

app = Flask(__name__)

Bootstrap(app)

app.config.from_object('config')

lm = LoginManager()
oid = OpenID(app, os.path.join(basedir, 'tmp'))
lm.login_view = 'login'
lm.init_app(app)
db = SQLAlchemy(app)

# Blueprints
from oscarstrigger.views import data
from oscarstrigger.views import monitor
from oscarstrigger.views import plot
from oscarstrigger.views import trigger

app.register_blueprint(data.bp)
app.register_blueprint(monitor.bp)
app.register_blueprint(plot.bp)
app.register_blueprint(trigger.bp)

from oscarstrigger.views import base
from oscarstrigger.views import auth
