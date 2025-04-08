#!/usr/bin/env python3

import subprocess, io, datetime, random, string, copy, os
from flask import Blueprint, render_template, request, Response, current_app, redirect, url_for, abort, send_from_directory, jsonify, flash, g
# local imports
from app.extensions import logger, globals,db
from app.functions import do_grade, check_questions,read_token
from app.models import QuestionTracking

main = Blueprint("main",__name__, template_folder=f'templates', static_folder=f'static')     # add path to templates/static if error

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
    if globals.lab_completed == True:
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
        logger.info(f"Submitting a grading task at {globals.manual_submit_time}")
        if request.method == "GET":
            # GET requests should call do_grade without any arguments
            globals.task = globals.executor.submit(do_grade)
        if request.method == "POST":
            req_data = request.form.to_dict()
            # POST requests will several form fields to pass to the grading script
            # Arguments to do_grade are the values from the form fields submitted
            #globals.task = globals.executor.submit(do_grade, *request.form.to_dict().values())
            globals.task = globals.executor.submit(do_grade, req_data)

        return render_template('grading.html', submit_time=globals.manual_submit_time)

    # if the current grading task is done, collect and display the results
    # the task is then nulled out
    if globals.task.done():
        # globals.results, globals.tokens = task.result()
        globals.task = None
        #if globals.submission_method == 'display':
        logger.info(f"Rendering graded results html page for user. Fatal error is {globals.fatal_error}")
        return redirect(url_for('main.results'))
        #else:
        #    return render_template("auto_submit.html", submit_time=globals.manual_submit_time)
    
    # if the current grading task is still running, show the grading page with the last submit time
    if globals.task.running():
        logger.info("Grading task is still running")
        return render_template('grading.html', submit_time=globals.manual_submit_time)


@main.route('/results',methods=['GET'])
def results():
    return render_template('results.html')


@main.route('/update',methods=['GET'])
def updated_results():
    if request.referrer != "https://skills.hub/lab/results":
        return jsonify({"NOTICE":"Unauthorized access attempted."})
    
    new_cron_results = copy.deepcopy(globals.cron_results) if globals.cron_results != None else dict()
    new_manual_results = copy.deepcopy(globals.manual_results) if globals.manual_results != None else dict()

    break_loop = False
    if globals.phases_enabled:
        ## Below loops intend to grab previous phases if completed & print that they are completed
        for ph in globals.phase_order:
            try:
                for q in globals.phases[ph]:
                    que_chk = QuestionTracking.query.filter_by(label=q).first()
                    
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
                    
                if ph == globals.current_phase:
                    break_loop = True
                    #break
            except Exception as e:
                break_loop = True
                logger.info(f"Exception occurred during query of results (may be due to attempting to see results before grading). Exception: {str(e)}")
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
        #logger.info(f"-----tmp---{tmpDir}---")
        for filename in os.listdir(tmpDir):
            path = os.path.join(tmpDir,filename)
            if os.path.isdir(path):
                #logger.info(f"--------{path}---{folder}---{filename}")
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
            flash("That file does not exist.")
            return redirect(url_for('main.list_files'))
    return render_template('files.html')




"""
Endpoint to list files on the server.
    if globals.hosted_files_enabled:
        if not globals.server_ready:
            logger.info("Tried to view files before server was marked as ready.")
            return redirect(url_for("info.main"))
        return render_template('files.html', files=get_file_list())
    return render_template('files.html')
"""