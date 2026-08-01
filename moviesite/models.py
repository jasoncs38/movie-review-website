from datetime import datetime
from itsdangerous import URLSafeTimedSerializer as Serializer
from moviesite import db, login_manager,app
from flask_login import UserMixin

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model,UserMixin):
    id=db.Column(db.Integer,primary_key=True)
    username=db.Column(db.String(20),unique=True,nullable=False)
    email=db.Column(db.String(120),unique=True,nullable=False)
    password=db.Column(db.String(60),nullable=False)
    image_file=db.Column(db.String(100),nullable=False,default='default.jpg')
    is_admin=db.Column(db.Boolean,nullable=False,default=False)
    reviews=db.relationship('Review',backref='author',lazy=True)

     
    def get_reset_token(self):
        s=Serializer(app.config['SECRET_KEY'])
        return s.dumps({'user_id':self.id})
    
    @staticmethod
    def verify_reset_token(token):
        s=Serializer(app.config['SECRET_KEY'])
        try:
            user_id=s.loads(token,max_age=1800)['user_id']
        except:
            return None
        return User.query.get(user_id)


    def __repr__(self):
        return f"User('{self.username}','{self.email}','{self.image_file}')"

class Movie(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    title=db.Column(db.String(100),nullable=False)
    description=db.Column(db.Text,nullable=False)
    release_year = db.Column(db.Integer, nullable=False)
    genre=db.Column(db.Text,nullable=False)
    poster=db.Column(db.String(100),nullable=False,default='default.jpg')
    reviews=db.relationship('Review',backref='movie',cascade='all, delete-orphan',lazy=True)

    def __repr__(self):
        return f"Movie('{self.title}')"


class Review(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    content=db.Column(db.Text,nullable=False)
    rating=db.Column(db.Float(),nullable=False)
    date_posted=db.Column(db.DateTime,nullable=False,default=datetime.utcnow)
    user_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False)
    movie_id=db.Column(db.Integer,db.ForeignKey('movie.id'),nullable=False)

    def __repr__(self):
        return f"Review('{self.author.username}','{self.movie.title}','{self.rating}','{self.date_posted}')"
