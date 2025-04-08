#!/usr/bin/python3

import os, sys
from flask import Flask, session
from app.extensions import globals

class Config:
    SECRET_KEY = 'NOT_A_TOKEN'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(globals.basedir,'challenge.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    FLASK_APP = 'app.py'
    BASE_DIR = globals.basedir
    STATIC_FOLDER = f"{globals.basedir}/app/main/static"
    TEMPLATES_FOLDER = f"{globals.basedir}/app/main/templates"
    ## Below configs are related to setting up the Scheduler API and allowing calls to it
    #SCHEDULER_API_ENABLED = True
    #SCHEDULER_AUTH =  HTTPBasicAuth()
