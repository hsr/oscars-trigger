from flask import Flask
app = Flask(__name__)

from oscars_te.views import data
from oscars_te.views import monitor
from oscars_te.views import plot

app.register_blueprint(data.bp)
app.register_blueprint(monitor.bp)
app.register_blueprint(plot.bp)

from oscars_te.views import base