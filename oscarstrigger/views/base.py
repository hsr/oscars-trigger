import sys
from flask import abort, render_template, jsonify, url_for, redirect
from jinja2 import TemplateNotFound
from oscarstrigger import app


@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html', error=error  ), 500

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


@app.route('/', defaults={'page': 'index'})
@app.route('/<page>')
def default(page):
    try:
        if page == 'index':
            return redirect(url_for('plot.interactive'));

        return render_template('%s.html' % page)
    except TemplateNotFound:
        abort(404)