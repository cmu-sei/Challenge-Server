#!/usr/bin/env python3
#
# Challenge Sever
# Copyright 2024 Carnegie Mellon University.
# NO WARRANTY. THIS CARNEGIE MELLON UNIVERSITY AND SOFTWARE ENGINEERING INSTITUTE MATERIAL IS FURNISHED ON AN "AS-IS" BASIS. CARNEGIE MELLON UNIVERSITY MAKES NO WARRANTIES OF ANY KIND, EITHER EXPRESSED OR IMPLIED, AS TO ANY MATTER INCLUDING, BUT NOT LIMITED TO, WARRANTY OF FITNESS FOR PURPOSE OR MERCHANTABILITY, EXCLUSIVITY, OR RESULTS OBTAINED FROM USE OF THE MATERIAL. CARNEGIE MELLON UNIVERSITY DOES NOT MAKE ANY WARRANTY OF ANY KIND WITH RESPECT TO FREEDOM FROM PATENT, TRADEMARK, OR COPYRIGHT INFRINGEMENT.
# Licensed under a MIT (SEI)-style license, please see license.txt or contact permission@sei.cmu.edu for full terms.
# [DISTRIBUTION STATEMENT A] This material has been approved for public release and unlimited distribution.  Please see Copyright notice for non-US Government use and distribution.
# DM24-0645
#


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
