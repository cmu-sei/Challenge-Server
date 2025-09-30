#!/usr/bin/env python3
#
# Challenge Sever
# Copyright 2024 Carnegie Mellon University.
# NO WARRANTY. THIS CARNEGIE MELLON UNIVERSITY AND SOFTWARE ENGINEERING INSTITUTE MATERIAL IS FURNISHED ON AN "AS-IS" BASIS. CARNEGIE MELLON UNIVERSITY MAKES NO WARRANTIES OF ANY KIND, EITHER EXPRESSED OR IMPLIED, AS TO ANY MATTER INCLUDING, BUT NOT LIMITED TO, WARRANTY OF FITNESS FOR PURPOSE OR MERCHANTABILITY, EXCLUSIVITY, OR RESULTS OBTAINED FROM USE OF THE MATERIAL. CARNEGIE MELLON UNIVERSITY DOES NOT MAKE ANY WARRANTY OF ANY KIND WITH RESPECT TO FREEDOM FROM PATENT, TRADEMARK, OR COPYRIGHT INFRINGEMENT.
# Licensed under a MIT (SEI)-style license, please see license.txt or contact permission@sei.cmu.edu for full terms.
# [DISTRIBUTION STATEMENT A] This material has been approved for public release and unlimited distribution.  Please see Copyright notice for non-US Government use and distribution.
# DM24-0645
#


import threading, subprocess, signal, os, json, datetime, sys
from flask import Flask, url_for, redirect, flash, request, Response
from typing import Tuple
from flaskConfig import FlaskConfig
from app.cron import run_cron_thread
from app.extensions import globals, logger, db
from app.models import EventTracker


def create_app(config_class: FlaskConfig = FlaskConfig) -> Flask:
    """
    Create the Flask application

    Args:
        config_class (Config, optional): Defaults to Config.

    Returns:
        Flask: The Flask application
    """

    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(config_class)
    app.url_map.strict_slashes = False

    from app.main.main import main as main_blueprint
    app.register_blueprint(main_blueprint,url_prefix='/challenge')

    from app.info.info import info as info_blueprint
    app.register_blueprint(info_blueprint,url_prefix='/info')

    db.init_app(app)
    with app.app_context():
        db.create_all()

        def signal_handler(sig,frame) -> None:
            """
            Signal handler for shutting down the application
            """

            logger.info(f"Signal Received -- Shutting down site")
            os._exit(0)
        signal.signal(signal.SIGTSTP, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        @app.errorhandler(404)
        def page_not_found(e) -> Response:
            """
            Handle 404 Not Found errors by redirecting to the home page.

            Args:
                e (HTTPException): The exception raised by the 404 error.

            Returns:
                Response: A redirect response to the home page.
            """
            return redirect(url_for('main.home'))

        @app.before_request
        def check_server_status() -> None:
            """
            Notify the user if the server is not ready by flashing a startup message.
            Called before every request.
            """

            if not globals.server_ready:
                logger.debug(f"Tried to access site before server was marked as ready.")
                flash("Please Note:<br>The challenge is still starting up and some features may not be available. If an issue occurs, please wait a little bit and refresh. The challenge is ready if this message is not present upon refresh.")

        @app.before_request
        def store_req() -> None:
            """
            Log user requests and submissions for analytics/auditing.
            Excludes JS, CSS, and update endpoint requests.
            Stores data in the EventTracker model and tracks submission counts.
            """

            if (not str(request.path).endswith('.js')) and (not str(request.path).endswith('.css')) and (not str(request.path).endswith('update')):
                with app.app_context():
                    event = (
                        "Request" if request.method == 'GET'
                        else "Upload" if "upload" in str(request.path)
                        else "Submission"
                    )
                    form_data = "No Data Submitted"
                    if len(form_data) > 0:
                        form_data = dict(request.form)
                        for k, v in request.form.items():
                            if k != 'submit':
                                form_data[f"{k}_text"] = globals.grading_parts[k]['text']
                    event_data = {
                        "challenge":globals.challenge_name,
                        "support_code":globals.support_code,
                        "event_type":event,
                        "client":str(request.headers.get("X-Real-IP")),
                        "method":str(request.method),
                        "submitted_form_data":form_data,
                        "path":f"{str(request.path)}",
                        "recorded_at": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    new_event = EventTracker(data=json.dumps(event_data))
                    db.session.add(new_event)
                    if event == 'Submission':
                        try:
                            sub_obj = EventTracker.query.filter_by(id=1).first()
                            cur_cnt = json.loads(sub_obj.data)
                            cur_cnt['number_submissions'] = str(int(cur_cnt['number_submissions'])+1)
                            cur_cnt['recorded_at'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            sub_obj.data = json.dumps(cur_cnt)
                        except Exception as e:
                            logger.error(f"Exception trying increment submission counter. Exception: {str(e)}")
                            sys.exit(1)
                    db.session.commit()
    return app


def run_startup_scripts() -> Tuple[dict[str,str], dict[str,str]]:
    """
    Runs the startup scripts

    Returns:
        Tuple[dict[str,str], dict[str,str]]: dictionaries that contain stdout / stderr for successful/failed startup scripts.
    """

    successes = {}
    errors = {}
    if not globals.startup_enabled:
        logger.info("Startup Scripts are disabled.")
        return successes, errors

    if (not globals.startup_workspace) and globals.in_workspace:
        logger.info("Startup scripts are disabled when running in a workspace. Skipping startup scripts")
        return successes, errors

    if (globals.startup_scripts == []) or (globals.startup_scripts == [None]) or (globals.startup_scripts == None):
        logger.error("Startup scripts enabled but no startup script is configured in 'config.yml'.")
        return successes, errors

    for startup_script in globals.startup_scripts:
        logger.debug(f"Calling {startup_script}")
        if not os.path.isfile(f"{globals.custom_script_dir}/{startup_script}"):
            logger.error(f"Starting script {startup_script} not found in 'custom_scripts' directory.")
            errors[startup_script] = f"stdout: \tstderr: Starting script {startup_script} not found in 'custom_scripts' directory."
            continue

        # run the startup script and parse output into a dict
        ## The output variable has properties output.stdout  and  output.stderr
        try:
            output = subprocess.run([f"{globals.custom_script_dir}/{startup_script}"], capture_output=True, check=True).stdout.decode('utf-8').replace("\n", r"\n")
            logger.info(f"Stdout from Startup Script {startup_script}: {output}")
            successes[startup_script] = output
        # Something happened if there was a non-zero exit status. Log this and set fatal_error
        except subprocess.CalledProcessError as e:
            logger.error(f"Startup script {startup_script} returned with non-zero exit status {e.returncode}.\tStdout: {e.stdout}\tStderr: {e.stderr}")
            errors[startup_script] = f"stdout: {e.stdout}\tstderr: {e.stderr}"
    return successes, errors


def start_grading_server(app: Flask):
    """Start the challenge server .

    Args:
        app (Flask): The Flask app
    """

    # exit if server is not enabled
    if not globals.grading_enabled and not globals.hosted_files_enabled:
        logger.info("Website features not enabled. Will serve disabled page from /.")
    else:
        logger.info(f"Starting grading server website with grading modes {globals.grading_mode}")
        # if using the cron mode, we need to set the config variables and start/schedule the grading thread
        if 'cron' in globals.grading_mode:
            logger.info(f"Waiting {globals.cron_delay} seconds until executing cron-style grading")
            cron_thread = threading.Timer(globals.cron_delay, run_cron_thread)
            cron_thread.start()

    # Add first entry to DB to indicate that the server has started
    with app.app_context():
        if not EventTracker.query.filter_by(id=0).first():
            challenge_data = {"challenge":globals.challenge_name, "support_code":globals.support_code, "event_type":f"Challenge Started","recorded_at":datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            new_event = EventTracker(id=0, data=json.dumps(challenge_data))
            db.session.add(new_event)
            db.session.commit()
        if not EventTracker.query.filter_by(id=1).first():
            cnt_data = {"challenge":globals.challenge_name, "support_code":globals.support_code, "event_type":"Submission Counter","number_submissions":"0","recorded_at":datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            sub_counter = EventTracker(id=1, data=json.dumps(cnt_data))
            db.session.add(sub_counter)
            db.session.commit()

    globals.scheduler.init_app(app)
    globals.scheduler.start()

    logger.info(f"Starting the Challenge Server.")
    ssl_context = None
    if globals.app_cert and globals.app_key:
        ssl_context = (globals.app_cert, globals.app_key)

    app.run(
        host=globals.app_host,
        port=globals.app_port,
        debug=False,
        ssl_context=ssl_context
    )
