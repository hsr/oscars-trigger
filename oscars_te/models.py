from oscars_te import db

ROLE_USER = 0
ROLE_ADMIN = 1

class User(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    nickname = db.Column(db.String(64), unique = True)
    email = db.Column(db.String(120), unique = True)
    role = db.Column(db.SmallInteger, default = ROLE_USER)
    # posts = db.relationship('Post', backref = 'author', lazy = 'dynamic')
    # The is_authenticated method has a misleading name. In general this method
    # should just return True unless the object represents a user that should
    # not be allowed to authenticate for some reason.
    def is_authenticated(self):
        return True

    # The is_active method should return True for users unless they are
    # inactive, for example because they have been banned.
    def is_active(self):
        return True

    # The is_anonymous method should return True only for fake users that are
    # not supposed to log in to the system.                    
    def is_anonymous(self):
        return False

    def get_id(self):
        return unicode(self.id)

    def __repr__(self):
        return '<User %r>' % (self.nickname)