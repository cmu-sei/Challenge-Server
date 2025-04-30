#!/usr/bin/env python3
#
# Challenge Sever
# Copyright 2024 Carnegie Mellon University.
# NO WARRANTY. THIS CARNEGIE MELLON UNIVERSITY AND SOFTWARE ENGINEERING INSTITUTE MATERIAL IS FURNISHED ON AN "AS-IS" BASIS. CARNEGIE MELLON UNIVERSITY MAKES NO WARRANTIES OF ANY KIND, EITHER EXPRESSED OR IMPLIED, AS TO ANY MATTER INCLUDING, BUT NOT LIMITED TO, WARRANTY OF FITNESS FOR PURPOSE OR MERCHANTABILITY, EXCLUSIVITY, OR RESULTS OBTAINED FROM USE OF THE MATERIAL. CARNEGIE MELLON UNIVERSITY DOES NOT MAKE ANY WARRANTY OF ANY KIND WITH RESPECT TO FREEDOM FROM PATENT, TRADEMARK, OR COPYRIGHT INFRINGEMENT.
# Licensed under a MIT (SEI)-style license, please see license.txt or contact permission@sei.cmu.edu for full terms.
# [DISTRIBUTION STATEMENT A] This material has been approved for public release and unlimited distribution.  Please see Copyright notice for non-US Government use and distribution.
# DM24-0645
#


from app.extensions import db
from sqlalchemy import func, JSON


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
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


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


class FileUpload(db.Model):
    __tablename__ = 'FileUploads'

    id            = db.Column(db.Integer, primary_key=True)
    file_name      = db.Column(db.String,  nullable=False)
    file_path           = db.Column(db.String,  nullable=False)
    submission_number = db.Column(db.Integer, nullable=False)
    uploaded_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default = func.now()
    )
    contained_files   = db.Column(
                        JSON,
                        nullable=False,
                        default=list
                    )

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
