from oscars_te import app, communicator

from flask import Blueprint, render_template, request

bp = Blueprint('plot', __name__, url_prefix='/plot')

def get_url(key):
    url = ''
    if app.config.has_key(key):
        url = app.config[key];
    if len(request.args.get(key,'')) > 0:
        url = request.args.get(key,'')
    return url

@bp.route('/static')
def static():
    oscarsdb = get_url('oscars')
    controller = get_url('controller')
    location = request.args.get('location','')
    location = 'floodlight' if len(location) < 1 else location
    errormsg = communicator.get_all(controller, oscarsdb)
    return render_template('plot.html', location=location, errormsg=errormsg)

@bp.route('/interactive')
def interactive():
    controller = ''
    if app.config.has_key('controller'):
        controller = app.config['controller'];
    if len(request.args.get('controller','')) > 0:
        controller = request.args.get('controller','')

    oscars = ''
    if app.config.has_key('oscars'):
        oscars = app.config['oscars'];
    if len(request.args.get('oscars','')) > 0:
        oscars = request.args.get('oscars','')

    return render_template('intplot.html',
        controller=controller, oscarsdb=oscars)