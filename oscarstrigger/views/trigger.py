import json
import sys
from flask import Blueprint, render_template, abort, request, \
                    url_for, flash, jsonify, redirect, g
from flask.ext.login import login_user, logout_user, current_user, login_required
from oscarstrigger.trigger import SFlowTrigger, FloodlightTrigger
from oscarstrigger import app, Pagination, lm


# Forms
from flask.ext.wtf import Form
from wtforms import TextField, BooleanField, SelectMultipleField, \
                    SelectField
from wtforms.validators import Required, IPAddress, NumberRange, \
                    ValidationError
                    
from oscarstrigger import app
log = app.logger

bp = Blueprint('trigger', __name__, url_prefix='/trigger')

PER_PAGE = 10

def url_for_other_page(page):
    args = request.view_args.copy()
    args['page'] = page
    return url_for(request.endpoint, **args)

app.jinja_env.globals['url_for_other_page'] = url_for_other_page


@bp.route('/')
def default(switch=None):
    # stats = ""
    # try:
    #     if isinstance(app.config['trigger_instance'], FloodlightMonitor):
    #         stats = app.config['trigger_istance'].
    # except Exception, e:
    #     log.debug('Error:' + str(e.message))
    #     raise e
    return render_template('about.html');

def get_trigger():
    try:
        if isinstance(app.config['trigger_instance'], SFlowTrigger):
            return app.config['trigger_instance']
        elif isinstance(app.config['trigger_instance'], FloodlightTrigger):
            return app.config['trigger_instance']
        #raise Exception()
    except:
        flash('Trigger not available', 'error')
    return None

def get_switches(trigger=None):
    switches = {}
    if app.debug:
        switches = {'127.0.0.1': {'error': 'Problem', 'datapath': {u's9': {560: {'ifindex': 560, 'port': 1, 'name': u's9-eth1'}, 562: {'ifindex': 562, 'port': 2, 'name': u's9-eth2'}, 566: {'ifindex': 566, 'port': 3, 'name': u's9-eth3'}}, u's8': {563: {'ifindex': 563, 'port': 1, 'name': u's8-eth1'}, 564: {'ifindex': 564, 'port': 2, 'name': u's8-eth2'}}, u's3': {553: {'ifindex': 553, 'port': 2, 'name': u's3-eth2'}, 548: {'ifindex': 548, 'port': 1, 'name': u's3-eth1'}}, u's2': {546: {'ifindex': 546, 'port': 1, 'name': u's2-eth1'}, 570: {'ifindex': 570, 'port': 4, 'name': u's2-eth4'}, 549: {'ifindex': 549, 'port': 2, 'name': u's2-eth2'}, 551: {'ifindex': 551, 'port': 3, 'name': u's2-eth3'}}, u's1': {571: {'ifindex': 571, 'port': 3, 'name': u's1-eth3'}, 547: {'ifindex': 547, 'port': 1, 'name': u's1-eth1'}, 561: {'ifindex': 561, 'port': 2, 'name': u's1-eth2'}}, u's7': {568: {'ifindex': 568, 'port': 2, 'name': u's7-eth2'}, 572: {'ifindex': 572, 'port': 3, 'name': u's7-eth3'}, 558: {'ifindex': 558, 'port': 1, 'name': u's7-eth1'}}, u's6': {556: {'ifindex': 556, 'port': 2, 'name': u's6-eth2'}, 573: {'ifindex': 573, 'port': 4, 'name': u's6-eth4'}, 550: {'ifindex': 550, 'port': 1, 'name': u's6-eth1'}, 559: {'ifindex': 559, 'port': 3, 'name': u's6-eth3'}}, u's5': {554: {'ifindex': 554, 'port': 1, 'name': u's5-eth1'}, 557: {'ifindex': 557, 'port': 2, 'name': u's5-eth2'}}, u's4': {552: {'ifindex': 552, 'port': 1, 'name': u's4-eth1'}, 555: {'ifindex': 555, 'port': 2, 'name': u's4-eth2'}}}, 'address': '127.0.0.1'}}
    if trigger:
        switches = trigger.getSwitches()
    return switches

def get_events(trigger=None):
    events = []
    if app.debug:
        events = json.loads(
        '[{"id":1,"agent":"bla","flowKey":"ble", "value":30},\
          {"id":2,"agent":"bla","flowKey":"ble", "value":30},\
          {"id":3,"agent":"bla","flowKey":"ble", "value":30},\
          {"id":4,"agent":"bla","flowKey":"ble", "value":30},\
          {"id":5,"agent":"bla","flowKey":"ble", "value":30},\
          {"id":6,"agent":"bla","flowKey":"ble", "value":30},\
          {"id":7,"agent":"bla","flowKey":"ble", "value":30},\
          {"id":8,"agent":"bla","flowKey":"ble", "value":30},\
          {"id":8,"agent":"bla","flowKey":"ble", "value":30},\
          {"id":9,"agent":"bla","flowKey":"ble", "value":30},\
          {"id":0,"agent":"bla","flowKey":"ble", "value":30}]')
    if trigger:
        events = trigger.getEvents().values()
    return events

class SFlowEventForm(Form):
    name = TextField('Event Name', validators = [Required()])
    keys = SelectMultipleField(
        'Event Keys', 
        choices = [
            ('ipsource', 'Source IP'), 
            ('ipdestination', 'Destination IP'),
            ('tcpsourceport', 'Source TCP Port'),
            ('tcpdestinationport', 'Destination TCP Port')
        ]
    )
    switch = TextField(
        'Switch', 
        validators = [Required()]
    )
    datapath = TextField(
        'Datapath', 
        validators = [Required()]
    )
    port = TextField(
        'Port', 
        validators = [Required()]
    )
    metric = SelectField(
        'Metric', 
        choices = [('frames', '# Frames'), ('bytes', '# Bytes')]
    )
    by_flow = BooleanField('By Flow')
    threshold = TextField(
        'Threshold',
        validators = [Required(),NumberRange(min=1)]
    )
    def __init__(self, **kwargs):
        super(SFlowEventForm, self).__init__(**kwargs)
        self._switches = get_switches(get_trigger())

    def validate_port(form, field):
        message = "Port %s not found on datapath %s"
        switches = form._switches
        switch_port = field.data
        switch_name = form.switch.data
        switch_datapath = form.datapath.data
        if not switches.has_key(switch_name) or \
           not switches[switch_name]['datapath'].has_key(switch_datapath) or \
           not switches[switch_name]['datapath'][switch_datapath].has_key(
               int(switch_port)):
            raise ValidationError(message % (switch_port,switch_datapath))
            
    def validate_switch(form, field):
        message = "Switch %s not found"
        switch_name = field.data
        switches = form._switches
        if not switches.has_key(switch_name):
            raise ValidationError(message % switch_name)

    def validate_datapath(form, field):
        message = "Datapath %s not found on switch %s"
        switches=form._switches
        switch_name = form.switch.data
        switch_datapath = field.data
        if not switches.has_key(switch_name) or \
           not switches[switch_name]['datapath'].has_key(switch_datapath):
            raise ValidationError(message % (switch_datapath,switch_name))
            
class FloodlightEventForm(Form):
    src_dpid = TextField(
        'Source DPID', 
        validators = [Required()]
    )
    src_port = TextField(
        'Source Port', 
        validators = [Required()]
    )
    
    dst_dpid = TextField(
        'Destination DPID',
        validators = [Required()]
    )
    dst_port = TextField(
        'Destination Port',
        validators = [Required()]
    )
    threshold = TextField(
        'Threshold',
        validators = [Required(),NumberRange(min=1)]
    )
    act = BooleanField('Offload automatically')
    
    def __init__(self, **kwargs):
        super(FloodlightEventForm, self).__init__(**kwargs)


@bp.route('/events', defaults={'page': 1}, methods=['GET', 'POST'])
@bp.route('/events/page/<int:page>')
def events(page):
    trigger = get_trigger()
    if isinstance(trigger, FloodlightTrigger):
        form = FloodlightEventForm()
        template = 'trigger/floodlight_events.html'
    else: # if isinstance(trigger, SFlowTrigger):
        form = SFlowEventForm()
        template = 'trigger/events.html'
    
    if form.validate_on_submit():
        try:
            if trigger:
                if isinstance(trigger, FloodlightTrigger):
                    trigger.registerEventListener(
                        form.src_dpid.data,
                        form.src_port.data,
                        form.threshold.data,
                        form.dst_dpid.data,
                        form.dst_port.data,
                        form.act.data
                    )
                else: #elif isinstance(trigger, SFlowTrigger):
                    trigger.registerEventListener(
                        form.name.data,
                        form.keys.data,
                        form.switch.data,
                        form.datapath.data,
                        form.port.data,
                        form.metric.data,
                        form.by_flow.data,
                        form.threshold.data
                    )
                flash('Event added!', 'success')
            return redirect(url_for('trigger.events'))
        except Exception, e:
            flash(str(e), 'error')
    elif form.is_submitted():
        flash('Invalid data. Please check the values provided', 'error')
        # flash(str(form.errors))
    
    revents = {}
    if trigger:
        revents = trigger.getRegisteredEvents()
    events = get_events(trigger)
    count = len(events)
    start = (page-1)*PER_PAGE
    end   = start + PER_PAGE if (start + PER_PAGE) < count else count
    events = events[start:end]
    if not events and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, count)
    
    return render_template(template,
        pagination=pagination,
        events=events,
        revents=revents,
        form=form)

@bp.route('/events/offload/<event_id>')
@login_required
def offload(event_id):
    trigger = get_trigger()
    events = get_events(trigger)
    if not g.user.is_admin():
        flash('Only admins can take that action!', 'error')
        return redirect(url_for('trigger.events'))
    
    for event in events:
        if event_id == event['id']:
            log.info('Offloading %s\n' % str(event))
            flash('Offloading %s' % event_id, 'success')
            if isinstance(trigger, FloodlightTrigger):
                trigger.actOnEvent(event_id)
            return redirect(url_for('trigger.events'))

    flash('Event %s not found!' % event_id, 'error')
    return redirect(url_for('trigger.events'))

@bp.route('/events/delete/<event_id>')
@login_required
def delete_event(event_id):
    trigger = get_trigger();
    
    if not g.user.is_admin():
        flash('Only admins can take that action!', 'error')
        return redirect(url_for('trigger.events'))
    
    # for event in events:
    #     if event_id == event['id']:
    log.info('Deleting %s\n' % str(event_id))
    if isinstance(trigger, FloodlightTrigger):
        trigger.deleteEventListener(event_id)
        flash('Event listener %s deleted!' % event_id, 'success')
        return redirect(url_for('trigger.events'))
    else:
        flash('Trigger not available!', 'error')
        return redirect(url_for('trigger.events'))
            

    flash('Event listener %s not found!' % event_id, 'error')
    return redirect(url_for('trigger.events'))

@bp.route('/json/events', defaults={'page': 1})
@bp.route('/json/events/page/<int:page>')
def json_events(page):
    events = get_events(get_trigger())
    count = len(events)
    start = (page-1)*PER_PAGE
    end   = start + PER_PAGE if (start + PER_PAGE) < count else count
    events = events[start:end]
    return jsonify(events)

class SwitchForm(Form):
    switch_name = TextField('switch_name', validators = [Required()])
    switch_address = TextField('switch_address', validators = [Required(), IPAddress()])


@bp.route('/switches', methods = ['GET', 'POST'])
@bp.route('/switches/<switch>')
#@login_required
def switches(switch=None):
    form = SwitchForm()
    trigger = get_trigger()

    if form.validate_on_submit():
        try:
            if trigger:
                trigger.addSwitch(form.switch_name.data,
                                  form.switch_address.data)
                flash('Switch added!', 'success')
                redirect(url_for('trigger.switches'))
        except Exception, e:
            flash(str(e), 'error')
    elif form.is_submitted():
        flash('Invalid data. Please check the values provided', 'error')
    
    switches = get_switches(trigger)
    if switch and switch not in switches:
        flash('Switch not found', 'error')
        switch=None

    return render_template(
        'trigger/switches.html',
        switches=switches,
        switch=switch,
        form=form)
        
# @bp.route('/switches')
# @bp.route('/switches/<switch>')
# def switches(switch=None):
#     switches = get_switches(get_trigger())
#     if switch and switch not in switches:
#         flash('Switch not found', 'error')
#         switch=None
#     
#     return render_template(
#         'trigger/switches.html',
#         switches=switches,
#         switch=switch)
        
@bp.route('/json/switches')
def json_switches():
    log.debug(str(get_switches(get_trigger()))+'\n')
    return jsonify(get_switches(get_trigger()))
    
