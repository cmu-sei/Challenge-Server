#!/usr/bin/env python3

# local imports
from app.extensions import db

class QuestionTracking(db.Model):
    __tablename__ = 'QuestionTracking'
    id = db.Column(db.Integer, primary_key=True)                        # question number
    label = db.Column(db.String, nullable=False)                        # 'GradingCheck1', 'GradingCheck2', etc.
    task = db.Column(db.String, nullable=False)                         # Question text
    response = db.Column(db.String, nullable=False)
    q_type = db.Column(db.String, nullable=False)                       # type of question
    solved = db.Column(db.Boolean, nullable=False)                  
    time_solved = db.Column(db.String, nullable=False)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}      #  if c.name != ''


class PhaseTracking(db.Model):
    __tablename__ = 'PhaseTracking'
    id = db.Column(db.Integer, primary_key=True)                        # Phase number 
    label = db.Column(db.String, nullable=False)  
    tasks = db.Column(db.String, nullable=False)                        # questions solved
    solved = db.Column(db.Boolean, nullable=False)                      # Solve time of entire phase
    time_solved = db.Column(db.String, nullable=False)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class EventTracker(db.Model):
    __tablename__ = 'EventTracker'
    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    data = db.Column(db.String, nullable=False) 