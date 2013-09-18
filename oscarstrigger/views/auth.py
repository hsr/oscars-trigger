import sys
import pprint

from flask import render_template, session, request, \
                  url_for, redirect, flash, g
from oscarstrigger import app, db, lm, oid
from flask.ext.login import login_user, logout_user, \
                            current_user, login_required

# Forms
from flask.ext.wtf import Form
from wtforms import TextField, BooleanField
from wtforms.validators import Required

import config

# Models
from oscarstrigger.models import User, ROLE_USER, ROLE_ADMIN

class LoginForm(Form):
    openid = TextField('openid', validators = [Required()])
    remember_me = BooleanField('remember_me', default = False)

@app.before_request
def before_request():
    g.user = current_user
    if g.user is None or not g.user.is_authenticated():
        g.authform = LoginForm()
        g.authproviders = config.OPENID_PROVIDERS

@lm.user_loader
def load_user(id):
    return User.query.get(int(id))

@app.route('/login', methods = ['GET', 'POST'])
@oid.loginhandler
def login():
    if g.user is not None and g.user.is_authenticated():
        return redirect(url_for('default'))
    
    if g.authform.validate_on_submit():
        session['remember_me'] = g.authform.remember_me.data
        return oid.try_login(
            g.authform.openid.data,
            ask_for = ['nickname', 'email'])

    return render_template('login.html', error=oid.fetch_error())

@oid.errorhandler
def on_error(message):
    flash(u'OpenID Error: %s' % message, 'error')

@oid.after_login
def after_login(resp):
    s = pprint.pformat(resp)
    sys.stderr.write(s+'\n')
    if resp.email is None or resp.email == "":
        flash('Invalid login. Please try again.')
        return redirect(url_for('login'))
    user = User.query.filter_by(email = resp.email).first()
    if user is None:
        nickname = resp.nickname
        if nickname is None or nickname == "":
            nickname = resp.email.split('@')[0]
        user = User(nickname = nickname, 
                    email = resp.email, 
                    role = ROLE_USER,
                    openid = resp.identity_url)
        db.session.add(user)
        db.session.commit()
    remember_me = False
    if 'remember_me' in session:
        remember_me = session['remember_me']
        session.pop('remember_me', None)
    login_user(user, remember = remember_me)
    flash('You were successfully logged in!','success')
    return redirect(request.args.get('next') or url_for('default'))

@app.route('/logout')
def logout():
    logout_user()
    return redirect(request.args.get('next') or url_for('default'))
