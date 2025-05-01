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
from typing import Any


class QuestionTracking(db.Model):
    """
    SQLAlchemy model for tracking the status and metadata of individual challenge questions.

    Attributes:
        id (int): Primary key representing the unique question ID.
        label (str): Identifier label for the question (e.g., 'GradingCheck1').
        task (str): Descriptive text or task associated with the question.
        response (str): The user's response.
        q_type (str): Type of question (e.g., 'manual', 'cron').
        solved (bool): Whether the question has been successfully completed.
        time_solved (str): Timestamp string indicating when the question was solved.
    """

    __tablename__ = 'QuestionTracking'
    id = db.Column(db.Integer, primary_key=True)                        # question number
    label = db.Column(db.String, nullable=False)                        # 'GradingCheck1', 'GradingCheck2', etc.
    task = db.Column(db.String, nullable=False)                         # Question text
    response = db.Column(db.String, nullable=False)
    q_type = db.Column(db.String, nullable=False)                       # type of question
    solved = db.Column(db.Boolean, nullable=False)
    time_solved = db.Column(db.String, nullable=False)

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize the QuestionTracking instance into a dictionary.

        Returns:
            Dict[str, Any]: A dictionary representation of the model's columns and values.
        """

        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class PhaseTracking(db.Model):
    """
    SQLAlchemy model for tracking progress through phases in a phased challenge configuration.

    Attributes:
        id (int): Primary key representing the phase ID.
        label (str): Unique label for the phase.
        tasks (str): Serialized list of tasks completed in the phase.
        solved (bool): Boolean indicating whether the phase has been completed.
        time_solved (str): Timestamp string of when the phase was marked as solved.
    """

    __tablename__ = 'PhaseTracking'
    id = db.Column(db.Integer, primary_key=True)                        # Phase number
    label = db.Column(db.String, nullable=False)
    tasks = db.Column(db.String, nullable=False)                        # questions solved
    solved = db.Column(db.Boolean, nullable=False)                      # Solve time of entire phase
    time_solved = db.Column(db.String, nullable=False)

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize the PhaseTracking instance into a dictionary.

        Returns:
            Dict[str, Any]: A dictionary representation of the model's columns and values.
        """

        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class EventTracker(db.Model):
    """
    SQLAlchemy model for logging user events such as page requests, submissions, or uploads.

    Attributes:
        id (int): Auto-incrementing primary key.
        data (str): JSON-encoded string storing metadata about the event (IP, method, form data, etc.).
    """

    __tablename__ = 'EventTracker'
    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    data = db.Column(db.String, nullable=False)

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize the EventTracker instance into a dictionary.

        Returns:
            Dict[str, Any]: A dictionary representation of the model's columns and values.
        """

        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class FileUpload(db.Model):
    """
    SQLAlchemy model for storing metadata about uploaded files.

    Attributes:
        id (int): Primary key for the file upload record.
        file_name (str): The original name of the uploaded file.
        file_path (str): Path where the file is stored on the server.
        submission_number (int): Identifier to group file uploads under a submission.
        uploaded_at (datetime): Timestamp when the file was uploaded (defaults to current time).
        contained_files (list): JSON list of filenames contained in the uploaded archive or batch.
    """

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

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize the FileUpload instance into a dictionary.

        Returns:
            Dict[str, Any]: A dictionary representation of the model's columns and values.
        """

        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
