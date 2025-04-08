#!/usr/bin/env python3

import subprocess, io, datetime, random, string
from flask import Blueprint, render_template, request, Response, current_app, redirect, url_for, abort, send_from_directory, g
from app.extensions import logger, globals
from app.functions import do_grade

info = Blueprint("info",__name__, template_folder=f'templates', static_folder=f'static')     # add path to templates/static if error

@info.before_request
def pass_globals():
    g.globs = globals

@info.route('/', methods=['GET'])
def home():
    if not globals.info_home_enabled:
        return redirect(url_for("main.home"))
    return render_template('starting.html')


@info.route('/services', methods=['GET'])
def services():
    if not globals.services_home_enabled:
        return redirect(url_for("main.home"))
    elif globals.services_list == None:
        return render_template('services.html',services=None)
    return render_template('services.html',services=len(globals.services_list),status=globals.services_status, num_status = len(globals.services_status))
