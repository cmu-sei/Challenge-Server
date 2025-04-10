#!/usr/bin/env python3
#
# Challenge Sever
# Copyright 2024 Carnegie Mellon University.
# NO WARRANTY. THIS CARNEGIE MELLON UNIVERSITY AND SOFTWARE ENGINEERING INSTITUTE MATERIAL IS FURNISHED ON AN "AS-IS" BASIS. CARNEGIE MELLON UNIVERSITY MAKES NO WARRANTIES OF ANY KIND, EITHER EXPRESSED OR IMPLIED, AS TO ANY MATTER INCLUDING, BUT NOT LIMITED TO, WARRANTY OF FITNESS FOR PURPOSE OR MERCHANTABILITY, EXCLUSIVITY, OR RESULTS OBTAINED FROM USE OF THE MATERIAL. CARNEGIE MELLON UNIVERSITY DOES NOT MAKE ANY WARRANTY OF ANY KIND WITH RESPECT TO FREEDOM FROM PATENT, TRADEMARK, OR COPYRIGHT INFRINGEMENT.
# Licensed under a MIT (SEI)-style license, please see license.txt or contact permission@sei.cmu.edu for full terms.
# [DISTRIBUTION STATEMENT A] This material has been approved for public release and unlimited distribution.  Please see Copyright notice for non-US Government use and distribution.
# DM24-0645
#


from flask import Blueprint, render_template, redirect, url_for, g
from app.extensions import globals

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
