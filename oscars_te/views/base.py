from flask import abort, render_template, jsonify
from jinja2 import TemplateNotFound
from oscars_te import app

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


@app.route('/', defaults={'page': 'index'})
@app.route('/<page>')
def default(page):
    try:
        return render_template('%s.html' % page)
    except TemplateNotFound:
        abort(404)

