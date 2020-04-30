
from sqlalchemy import *
from sqlalchemy import create_engine, ForeignKey
from sqlalchemy import Column, Date, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref

from sqlalchemy.orm import sessionmaker

from sqlalchemy.sql.elements import TextClause
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, render_template, request, send_file, send_from_directory, jsonify

from hashlib import sha256

import secrets

import datetime

from datetime import timedelta


from scipy import stats

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test1.db'
db = SQLAlchemy(app) # set up database

engine = create_engine('sqlite:///test1.db')

Base = declarative_base()

class User(Base):
    """"""
    __tablename__ = "user"

    user_name = Column(String, primary_key=True)
    firstname = Column(String)
    lastname = Column(String)
    password = Column(String) #HashedPassword

    #----------------------------------------------------------------------
    def __init__(self, username, firstname, lastname, password):
        """"""
        self.user_name = username
        self.firstname = firstname
        self.lastname = lastname
        self.password = password

class Rating(Base):
    """"""
    __tablename__ = "rating"
 
    id = Column(Integer, primary_key=True)
    user_name = Column(String)
    date = Column(DateTime)
    rating = Column(Integer)
    streak = Column(Integer)

    #----------------------------------------------------------------------
    def __init__(self, user_name, rating, streak):
        """"""
        self.user_name = user_name
        self.rating = rating
        self.streak = streak
        self.date = datetime.datetime.now()

class UserSession(Base):
    """"""
    __tablename__ = "usersession"
 
    id = Column(Integer, primary_key=True)
    user_name = Column(String)
    date = Column(DateTime)
    token = Column(String)
    active = Column(Boolean)

    #----------------------------------------------------------------------
    def __init__(self, user_id, token):
        """"""
        self.user_name = user_id
        self.token = token
        self.date = datetime.datetime.now()
        self.active = True

# create tables
Base.metadata.create_all(engine)


class MoodResponse:
    def __init__(self, username,streak,percentile=None):
        self.username = username
        self.streak = streak
        self.percentile = percentile



@app.route("/login", methods=['GET'])
def login():
    content = request.form

    user_name = content["user_name"]
    unhashed_password = content["password"]




    data = unhashed_password
    hashValue = sha256(data.encode('utf-8'))

    output = hashValue.hexdigest()


    result = db.session.query(User).filter(User.user_name == user_name)

    count = len([student for student in result])

    authorized = False
    if count == 1:
        for student in result:
            if student.password == output:
                authorized = True
                break
    else:
        return ""


    if authorized:
        

        result_session = db.session.query(UserSession).filter(User.user_name == user_name)

        count = result_session.count()


        if (count > 0):
            ses = result_session[-1]
            if ses.active:
                if (ses.date + timedelta(minutes=5)) < datetime.datetime.now():
                    token = secrets.token_hex(20)
                    usersession = UserSession(user_name,token)

                    ses.active = False

                    db.session.add(usersession)
                    db.session.commit()
                    return token
                else:
                    #return ses.date
                    return ses.token
            else:
                token = secrets.token_hex(20)
                usersession = UserSession(user_name,token)

                db.session.add(usersession)
                db.session.commit()
                return token
        else:
            token = secrets.token_hex(20)
            usersession = UserSession(user_name,token)


            db.session.add(usersession)
            db.session.commit()

            return token




        
        
    else:
        return ""

    

@app.route("/addrating", methods=['POST'])
def add_rating():
    content = request.form

    user_name = content["user_name"]
    rating = content["rating"]
    token = content["token"]

    result = db.session.query(UserSession).filter(UserSession.user_name == user_name and UserSession.active == 1)

    count = result.count()





    

    if (count >= 1):
        user_session = result[-1]
        if user_session.token == token:

            if (user_session.date + timedelta(minutes=5)) < datetime.datetime.now():
                user_session.active = False
                db.session.commit()
                return "Credentials Not Active. Please reattain token."
            else:
                last_rating = db.session.query(Rating).filter(Rating.user_name == user_name).order_by(desc(Rating.date)).first()

                if (last_rating):
                    tDelta = abs((datetime.datetime.now() - last_rating.date).days)

                    if (tDelta == 1):
                        streak = last_rating.streak + 1

                    else:
                        streak = 1
                else:
                    streak = 1

                rating = Rating(user_name,rating,streak)
                db.session.add(rating)
                db.session.commit()
                return "Added Rating"
        return "Unauthorized"
    else:
        return "No Active Sessions"



@app.route("/mood", methods=['GET'])
def mood():
    content = request.form

    user_name = content["user_name"]
    token = content["token"]

    result = db.session.query(UserSession).filter(UserSession.user_name == user_name and UserSession.active == 1)

    count = result.count()

    if result[-1].token == token:
        last_rating = db.session.query(Rating).filter(Rating.user_name == user_name).order_by(desc(Rating.date)).first()
        perc = percentile(last_rating.streak)
        
        if perc >= 50:
            md = MoodResponse(user_name,last_rating.streak,perc)
            return jsonify(
                    {"user_name":md.username,
                    "streak":md.streak,
                    "percentile":md.percentile
                    }
                )
        else:
            md = MoodResponse(user_name,last_rating.streak)
            return jsonify(
                    {"user_name":md.username,
                    "streak":md.streak
                    }
                )


def percentile(num):
    result = get_most_recent_streaks()

    if (len(result) > 1):
        perc = stats.percentileofscore(result, num)

        return perc
    else:
        return 0




def get_most_recent_streaks():
    streaks = []

    result = db.session.query(User)


    for user in result:
        last_rating = db.session.query(Rating).filter(Rating.user_name == user.user_name).order_by(desc(Rating.date)).first()
        streaks.append(int(last_rating.streak))
    
    return streaks





@app.route("/createuser", methods=['POST'])
def create_user():
    content = request.form

    user_name = content["user_name"]
    first_name = content["first_name"]
    last_name = content["last_name"]
    unhashed_password = content["password"]


    data = unhashed_password
    hashValue = sha256(data.encode('utf-8'))

    output = hashValue.hexdigest()


    result = db.session.query(User).filter(User.user_name == user_name)

    count = result.count()

    if count == 0:
        user = User(user_name,first_name,last_name,output)
        db.session.add(user)
        db.session.commit()
        return str(user.user_name)

    else:
        return "User Name Taken"


if __name__ == "__main__":
    app.run(debug=True)
