import json
import sys
from flask import Blueprint, render_template, abort, request, url_for
from oscars_te.trigger import SFlowTrigger
from oscars_te import app, Pagination


bp = Blueprint('trigger', __name__, url_prefix='/trigger')

PER_PAGE = 10

def url_for_other_page(page):
    args = request.view_args.copy()
    args['page'] = page
    return url_for(request.endpoint, **args)

app.jinja_env.globals['url_for_other_page'] = url_for_other_page

@bp.route('/events', defaults={'page': 1})
@bp.route('/events/page/<int:page>')
def show_events(page):
    events = []
    try:
        if isinstance(app.config['trigger_instance'], SFlowTrigger):
            events = app.config['trigger_instance'].getEvents()
    except:
        sys.stderr.write("Could not fetch events form Trigger\n")
    
    count = len(events)
    sys.stderr.write('%d\n' % count)
    start = (page-1)*PER_PAGE
    end   = start + PER_PAGE if (start + PER_PAGE) < count else count
    events = events[start:end]
    if not events and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, count)
    return render_template('trigger/events.html',
        pagination=pagination,
        events=events
    )
    
