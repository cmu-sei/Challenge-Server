#!/usr/bin/env python3
#
# Challenge Sever
# Copyright 2024 Carnegie Mellon University.
# NO WARRANTY. THIS CARNEGIE MELLON UNIVERSITY AND SOFTWARE ENGINEERING INSTITUTE MATERIAL IS FURNISHED ON AN "AS-IS" BASIS. CARNEGIE MELLON UNIVERSITY MAKES NO WARRANTIES OF ANY KIND, EITHER EXPRESSED OR IMPLIED, AS TO ANY MATTER INCLUDING, BUT NOT LIMITED TO, WARRANTY OF FITNESS FOR PURPOSE OR MERCHANTABILITY, EXCLUSIVITY, OR RESULTS OBTAINED FROM USE OF THE MATERIAL. CARNEGIE MELLON UNIVERSITY DOES NOT MAKE ANY WARRANTY OF ANY KIND WITH RESPECT TO FREEDOM FROM PATENT, TRADEMARK, OR COPYRIGHT INFRINGEMENT.
# Licensed under a MIT (SEI)-style license, please see license.txt or contact permission@sei.cmu.edu for full terms.
# [DISTRIBUTION STATEMENT A] This material has been approved for public release and unlimited distribution.  Please see Copyright notice for non-US Government use and distribution.
# DM24-0645
#


import subprocess, io, datetime, random, string, copy, os
from flask import Blueprint, render_template, request, Response, current_app, redirect, url_for, abort, send_from_directory, jsonify, flash, g
from app.extensions import logger, globals,db
from app.functions import do_grade, check_questions,read_token
from app.models import QuestionTracking

main = Blueprint("main",__name__, template_folder='templates', static_folder='static')

@main.before_request
def pass_globals():
    g.globs = globals

@main.route('/', methods=['GET'])
def home():
    return render_template('home.html')

@main.route('/tasks', methods=['GET'])
def tasks():
    if globals.grading_enabled == False:
        return render_template("tasks.html")

    parts_org = dict()
    for key, value in globals.grading_parts.items():
        q_mode = value['mode']
        if q_mode not in list(parts_org.keys()):
            parts_org[q_mode] = dict()
        if globals.phases_enabled:
            if key in globals.phases[globals.current_phase]:
                parts_org[q_mode][key] = value
        else:
            parts_org[q_mode][key] = value
    return render_template('tasks.html', questions=parts_org)


@main.route('/grade', methods=['GET', 'POST'])
def grade():
    '''
    This method gets called when a user requests grading (presses grade/submit button)
    The method will create the grading task and render the 'grading page' if the task is still running
    When grading is done, the 'graded page' will be rendered.
    '''

    if not globals.grading_enabled:
        return redirect(url_for("main.tasks"))

    check_questions()
    if globals.challenge_completed == True:
        return redirect(url_for('main.results'))

    if not globals.server_ready:
        logger.info("Tried to perform grading before server was marked as ready.")
        return redirect(url_for("info.main"))

    # if there is no current grading task, then create one
    if not globals.task:
        now_time = datetime.datetime.now()
        now_string = now_time.strftime("%m/%d/%Y %H:%M:%S")
        submit_time_time = datetime.datetime.strptime(globals.manual_submit_time, "%m/%d/%Y %H:%M:%S")

        # rate limiting grading attempts - display graded and let user know how long to wait
        if submit_time_time + globals.grading_rateLimit > now_time:
            try_again = (globals.grading_rateLimit - (now_time - submit_time_time)).total_seconds().__int__()
            logger.info(f"Hit rate limit. Telling user to try again in {try_again} seconds")
            return redirect(url_for("main.tasks"))

        globals.manual_submit_time = now_string
        logger.info(f"Submitting a grading task at {globals.manual_submit_time}. Request method is {request.method}")
        if request.method == "GET":
            # GET requests should call do_grade without any arguments
            globals.task = globals.executor.submit(do_grade)
        if request.method == "POST":
            req_data = request.form.to_dict()
            # POST requests will several form fields to pass to the grading script
            # Arguments to do_grade are the values from the form fields submitted
            logger.info(f"Calling do_grade with data: {req_data}")
            globals.task = globals.executor.submit(do_grade, req_data)

        return render_template('grading.html', submit_time=globals.manual_submit_time)

    # if the current grading task is done, collect and display the results
    if globals.task.done():
        globals.task = None
        logger.info(f"Rendering graded results html page for user. Fatal error is {globals.fatal_error}")
        return redirect(url_for('main.results'))

    # if the current grading task is still running, show the grading page with the last submit time
    if globals.task.running():
        logger.info("Grading task is still running")
        return render_template('grading.html', submit_time=globals.manual_submit_time)


@main.route('/results',methods=['GET'])
def results():
    return render_template('results.html')


@main.route('/update',methods=['GET'])
def updated_results():

    new_cron_results = copy.deepcopy(globals.cron_results) if globals.cron_results != None else dict()
    new_manual_results = copy.deepcopy(globals.manual_results) if globals.manual_results != None else dict()

    break_loop = False
    if globals.phases_enabled:
        ## Grab previous phases if completed & print that they are completed
        for phase in globals.phase_order:
            try:
                for question in globals.phases[phase]:
                    que_chk = QuestionTracking.query.filter_by(label=question).first()

                    if que_chk.q_type == 'cron':
                        if que_chk.solved == True:
                            globals.tokens['cron'][que_chk.label] = read_token(que_chk.label)
                            new_cron_results[que_chk.label] = f"Success -- {que_chk.response}" if (que_chk.response != "" and que_chk.response != "N/A"  ) else "Success"
                        else:
                            new_cron_results[que_chk.label] = f"Failure" if que_chk.response == "N/A" else (f"Failure -- {que_chk.response}" if que_chk.response != "" else "Failure -- Has not been graded yet.")
                        continue
                    if que_chk.q_type in globals.MANUAL_MODE:
                        if que_chk.solved == True:
                            globals.tokens['manual'][que_chk.label] = read_token(que_chk.label)
                            new_manual_results[que_chk.label] = f"Success -- {que_chk.response}" if (que_chk.response != "" and que_chk.response != "N/A"  ) else "Success"
                        else:
                            new_manual_results[que_chk.label] = "Failure" if que_chk.response == "N/A" else (f"Failure -- {que_chk.response}" if que_chk.response != "" else "Failure -- Has not been graded yet.")
                        continue

                if phase == globals.current_phase:
                    break_loop = True
            except Exception as e:
                break_loop = True
                logger.info(f"Exception while querying grading results (may be due to attempting to see results before grading). Exception: {str(e)}")
            if break_loop:
                break
        if "01/01/1900" in globals.manual_submit_time:
            globals.manual_submit_time = datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S")
        if "01/01/1900" in globals.cron_submit_time:
            globals.cron_submit_time = datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S")
        tmp_globals = {
            "manual_enabled": True if 'manual' in globals.grading_mode else False,
            "cron_enabled":True if 'cron' in globals.grading_mode else False,
            "cron_submit_time": globals.cron_submit_time,
            "manual_submit_time": globals.manual_submit_time,
            "cron_results": new_cron_results,
            "manual_results": new_manual_results,
            "grading_parts": globals.grading_parts,
            "tokens":globals.tokens,
            "fatal_error":globals.fatal_error
        }
    else:
        tmp_globals = {
            "cron_submit_time": globals.cron_submit_time,
            "manual_enabled": True if 'manual' in globals.grading_mode else False,
            "manual_submit_time": globals.manual_submit_time,
            "cron_enabled":True if 'cron' in globals.grading_mode else False,
            "cron_results": globals.cron_results,
            "manual_results": globals.manual_results,
            "grading_parts": globals.grading_parts,
            "tokens":globals.tokens,
            "fatal_error":globals.fatal_error
            }
    return jsonify(tmp_globals)


@main.route("/files", defaults={'folder':''})
@main.route("/files/<path:folder>")
def list_files(folder):
    if globals.hosted_files_enabled:
        if not globals.server_ready:
            logger.info("Tried to view files before server was marked as ready.")
            return redirect(url_for("main.home"))
        files = {}
        dirs = {}
        # Directly join the folder path with the base directory
        tmpDir = os.path.join(globals.hosted_file_directory, folder)
        for filename in os.listdir(tmpDir):
            path = os.path.join(tmpDir,filename)
            if os.path.isdir(path):
                dirs[filename] = os.path.join(folder,filename)
            elif os.path.isfile(path):
                files[filename] = os.path.join(folder,filename)
        return render_template('files.html', files=files, folders=dirs)
    return render_template('files.html')


@main.route("/download/<path:path>")
def get_file(path):
    """Download a file."""
    if globals.hosted_files_enabled:
        if path == '':
            flash("File not selected for download")
            return redirect(url_for('main.list_files'))
        filePath = os.path.join(globals.hosted_file_directory, path)
        if not globals.server_ready:
            logger.info("Tried to download files before server was marked as ready.")
            return redirect(url_for("main.home"))
        if os.path.isfile(filePath) :
            logger.info(f"User is downloading file {filePath}")
            return send_from_directory(globals.hosted_file_directory,path,as_attachment=True)
        else:
            flash(f"{filePath} does not exist.")
            return redirect(url_for('main.list_files'))
    return render_template('files.html')
