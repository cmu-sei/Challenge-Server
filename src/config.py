#!/usr/bin/python3

import os, sys
from flask import Flask, session
# local import
from app.extensions import globals

class Config:
    SECRET_KEY = 'NOT_A_TOKEN'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(globals.basedir,'hub.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    FLASK_APP = 'app.py'
    BASE_DIR = globals.basedir
    STATIC_FOLDER = f"{globals.basedir}/app/main/static"
    TEMPLATES_FOLDER = f"{globals.basedir}/app/main/templates"
    ## Below configs are related to setting up the Scheduler API and allowing calls to it
    #SCHEDULER_API_ENABLED = True
    #SCHEDULER_AUTH =  HTTPBasicAuth()
    #SCHEDULER_API_PREFIX = "/scheduler"        ## Wasnt used but was present
    #SCHEDULER_ENDPOINT_PREFIX = "scheduler."   ## Wasnt used but was present
    #SCHEDULER_ALLOWED_HOSTS = ["*"]            ## Wasnt used but was present