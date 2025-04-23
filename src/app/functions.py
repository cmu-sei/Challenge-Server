#!/usr/bin/env python3
#
# Challenge Sever
# Copyright 2024 Carnegie Mellon University.
# NO WARRANTY. THIS CARNEGIE MELLON UNIVERSITY AND SOFTWARE ENGINEERING INSTITUTE MATERIAL IS FURNISHED ON AN "AS-IS" BASIS. CARNEGIE MELLON UNIVERSITY MAKES NO WARRANTIES OF ANY KIND, EITHER EXPRESSED OR IMPLIED, AS TO ANY MATTER INCLUDING, BUT NOT LIMITED TO, WARRANTY OF FITNESS FOR PURPOSE OR MERCHANTABILITY, EXCLUSIVITY, OR RESULTS OBTAINED FROM USE OF THE MATERIAL. CARNEGIE MELLON UNIVERSITY DOES NOT MAKE ANY WARRANTY OF ANY KIND WITH RESPECT TO FREEDOM FROM PATENT, TRADEMARK, OR COPYRIGHT INFRINGEMENT.
# Licensed under a MIT (SEI)-style license, please see license.txt or contact permission@sei.cmu.edu for full terms.
# [DISTRIBUTION STATEMENT A] This material has been approved for public release and unlimited distribution.  Please see Copyright notice for non-US Government use and distribution.
# DM24-0645
#


import yaml, os, subprocess, requests, datetime, json, sys, ipaddress, uuid, copy, base64, isodate
from flask import current_app
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import Future
from time import sleep
from app.extensions import logger, globals, db
from app.env import get_clean_env
from app.models import QuestionTracking,PhaseTracking, EventTracker

####### parse `config.yml` and assign values to globals object
def read_config(app):
    conf = None
    if not os.path.isfile(globals.yaml_path):
        logger.error("Could not find config.yml file.")
        sys.exit(1)
    with open(globals.yaml_path, 'r') as config_file:
        try:
            conf = yaml.safe_load(config_file)
        except yaml.YAMLError:
            logger.error("Error Reading YAML in config file")
            sys.exit(1)

    globals.challenge_name = get_clean_env('CS_CHALLENGE_NAME') or conf.get('challenge_name') or ""

    # Error on invalid IP address/port
    host = (
        get_clean_env('CS_APP_HOST') or
        (conf.get('app') or {}).get('host') or
        '0.0.0.0'
    )
    try:
        ipaddress.ip_address(host)
    except ValueError:
        print(f"Error: Invalid IP address: {host}")
        sys.exit(1)
    globals.app_host = host

    port = (
        get_clean_env('CS_APP_PORT') or
        (conf.get('app') or {}).get('port') or
        8888
    )
    try:
        port = int(port)
        if not (1 <= port <= 65535):
            raise ValueError
    except (ValueError, TypeError):
        print(f"Error: Invalid TCP port: {port}")
        sys.exit(1)
    globals.app_port = port

    # Error on Certificate/Key not found
    cert_path = (
        get_clean_env('CS_APP_CERT') or
        (conf.get('app') or {}).get('tls_cert')
    )
    print(cert_path)
    if cert_path and not os.path.isfile(cert_path):
        print(f"Error: Certificate file not found at path: {cert_path}")
        sys.exit(1)
    globals.app_cert = cert_path

    key_path = (
        get_clean_env('CS_APP_KEY') or
        (conf.get('app') or {}).get('tls_key')
    )

    if key_path and not os.path.isfile(key_path):
        print(f"Error: Key file not found at path: {key_path}")
        sys.exit(1)
    globals.app_key = key_path


    # set grading enabled. False if not set in env vars or config file
    globals.grading_enabled = get_clean_env('CS_GRADING_ENABLED', '').lower() == 'true' or (conf.get('grading') or {}).get('enabled') or False
    logger.info(f"Grading enabled: {globals.grading_enabled}")

    ##########  Process Grading Config
    if globals.grading_enabled:
        # set grading parts. Error if not defined
        if not conf['grading'].get('parts'):
            logger.error(f"Grading parts is not defined in config file. Grading parts is required when grading is enabled.")
            sys.exit(1)

        if (not conf['grading'].get('manual_grading')) and (not conf['grading'].get('cron_grading')):
            logger.error(f"At least one grading type must be enabled if grading is enabled.")
            sys.exit(1)

        globals.grading_parts = conf['grading']['parts']
        globals.grader_post = get_clean_env('CS_GRADER_POST', '').lower() == 'true' or conf['grading'].get('grader_post') or False

        # Initialize phases & add to DB
        with app.app_context():
            if conf['grading'].get('phases'):
                globals.phases_enabled = True
                if ( not conf['grading'].get('phase_info') or (len(conf['grading']['phase_info']) == 0)):
                    logger.error("Phases enabled but no phases are configured in 'config.yml. Exiting.")
                    sys.exit(1)
                globals.phases = conf['grading']['phase_info']
                globals.phase_order = sorted(list(globals.phases.keys()),key=str.casefold)
                if 'mini_challenge' in globals.phase_order:
                    tmp = globals.phase_order.pop(0)
                    globals.phase_order.append(tmp)
                try:
                    globals.current_phase = get_current_phase()
                except KeyError as e:
                    globals.current_phase = globals.phase_order[0]

                p_restart = False
                try:
                    p_chk = PhaseTracking.query.all()
                    if len(p_chk) == len(globals.phases):
                        p_restart = True
                except Exception as e:
                    ...
                if not p_restart:
                    try:

                        for ind,phase in enumerate(globals.phase_order):
                            new_phase = PhaseTracking(id=ind, label=phase, tasks=','.join(globals.phases[phase]), solved=False,time_solved="---")
                            db.session.add(new_phase)
                            db.session.commit()
                    except Exception as e:
                        logger.error(f"Unable to add phase {phase} to DB. Exception:{e}.\nExiting.")
                        sys.exit(1)

            ## Add questions to DB for tracking
            globals.question_order = sorted(list(globals.grading_parts.keys()),key=str.casefold)
            q_restart = False
            try:
                q_chk = QuestionTracking.query.all()
                if len(q_chk) == len(globals.grading_parts):
                    q_restart = True
            except Exception as e:
                print(e)
            if not q_restart:
                try:
                    for index,key in enumerate(globals.question_order,start=1):
                        new_question = QuestionTracking(id=index,label=key,task=globals.grading_parts[key]['text'],response="",q_type=globals.grading_parts[key]['mode'],solved=False,time_solved="---")
                        db.session.add(new_question)
                        db.session.commit()
                except Exception as e:
                    logger.error(', '.join(globals.question_order))
                    logger.error(f"Unable to add question {key} to DB. Exception:{e}.\nExiting.")
                    sys.exit(1)

        manual_grading = get_clean_env('CS_MANUAL_GRADING', '').lower() =='true' or conf['grading']['manual_grading'] or False
        if manual_grading:
        # set manual grading script. Error if script is not defined or not executable
            globals.grading_mode.append('manual')
            globals.manual_grading_script = get_clean_env('CS_MANUAL_GRADING_SCRIPT') or conf['grading'].get('manual_grading_script')
            if not globals.manual_grading_script:
                logger.error(f"Manual Grading not script defined in env vars or config file.")
                sys.exit(1)
            logger.info(f"Manual Grading script: {globals.manual_grading_script}")
            try:
                if not os.access(f"{globals.custom_script_dir}/{globals.manual_grading_script}", os.X_OK):
                    logger.error(f"Manual grading script {globals.custom_script_dir}/{globals.manual_grading_script} missing or is not executable")
                    sys.exit(1)
            except Exception as e:
                logger.error(f"Got exception {e} while checking if grading script {globals.manual_grading_script} is executable.")
                sys.exit(1)

        if get_clean_env('CS_CRON_GRADING') == 'true' or conf['grading'].get('cron_grading'):
            set_cron_vars(conf)

        # set grading rate limit. 0 if not defined
        rate_limit_env = get_clean_env('CS_GRADING_RATE_LIMIT')
        rate_limit_conf = conf['grading'].get('rate_limit')
        rate_limit_seconds = int(rate_limit_env) if rate_limit_env is not None else (
            int(rate_limit_conf) if rate_limit_conf is not None else 0
            )
        globals.grading_rateLimit = datetime.timedelta(seconds=rate_limit_seconds)
        logger.info(f"Grading Rate limit: {globals.grading_rateLimit.total_seconds().__int__()} seconds")

        # set token location. "env" is default. Error if not recognized.
        globals.token_location =  get_clean_env('CS_TOKEN_LOCATION') or conf['grading'].get('token_location') or 'env'
        if globals.token_location not in globals.VALID_TOKEN_LOCATIONS:
            logger.error(f"Token Location: {conf['grading']['token_location']} is not recognized. Options are: {globals.VALID_TOKEN_LOCATIONS}")
            sys.exit(1)
        logger.info(f"Token location: {globals.token_location}")

        # set grading submission method. "display" is default. Error if not recognized
        globals.submission_method = get_clean_env('CS_SUBMISSION_METHOD') or conf['grading'].get('submission').get('method') or 'display'
        if globals.submission_method not in globals.VALID_SUBMISSION_METHODS:
            logger.error(f"Submission Method: {conf['grading']['submission']['method']} is not recognized. Options are: {globals.VALID_SUBMISSION_METHODS}")
            sys.exit(1)
        logger.info(f"Submission method: {globals.submission_method}")

        # additional configuration for grader_post
        globals.grader_url = get_clean_env('CS_GRADER_URL') or conf['grading']['submission'].get('grader_url')
        if globals.submission_method == 'grader_post' and not globals.grader_url:
            logger.error(f"grader_url is not defined in environment variable CS_GRADER_URL or config file. grader_url is required when submission method if grader_post.")
            sys.exit(1)
        logger.info(f"Grader URL: {globals.grader_url}")

        # use environment variable for grader_url or fall back to the config file
        globals.grader_key =  get_clean_env('CS_GRADER_KEY') or conf['grading']['submission'].get('grader_key')
        if globals.submission_method == 'grader_post' and not globals.grader_key:
            logger.error(f"grader_key is not defined in environment variable CS_GRADER_KEY or config file. grader_key is required when submission method if grader_post.")
            sys.exit(1)
        logger.info(f"Grader Key: {globals.grader_key}")

    # configure required services. Empty array if setting is not in config
    globals.required_services = conf['required_services'] if 'required_services' in conf else []
    globals.blocking_services = []
    for service in globals.required_services:
        # ensure host is defined in required services
        if 'host' not in service:
            logger.error(f"Missing host definition in required service: {service}")
            sys.exit(1)
        # ensure type is defined in required services. If not defined, default to ping type.
        if 'type' not in service:
            logger.info(f"Missing type definition in required service: {service}. Defaulting to ping.")
            service['type'] = "ping"
        # ensure defined type is valid
        if service['type'] not in globals.VALID_SERVICE_TYPES:
            logger.error(f"Invalid required service type in: {service}. Valid types are {globals.VALID_SERVICE_TYPES}.")
            sys.exit(1)
        # ensure port is defined for socket type
        if service['type'] == 'socket' and 'port' not in service:
            logger.error(f"Missing port definition in required service: {service}. Port definition is required with socket type")
            sys.exit(1)
        # ensure web options are set/defaulted
        if service['type'] == 'web':
            if 'port' not in service:
                logger.info(f"Missing web port definition in required service: {service}. Defaulting to 80")
                service['port'] = 80
            if 'path' not in service:
                logger.info(f"Missing web path definition in required service: {service}. Defaulting to /")
                service['path'] = '/'
        # ensure block startup scripts is defined. Default to False if not
        if 'block_startup_scripts' not in service:
            logger.info(f"Missing block startup script definition in service: {service}. Defaulting to False")
            service['block_startup_scripts'] = False
        if not isinstance(service['block_startup_scripts'], bool):
            logger.error(f"Invalid type for block_startup_scripts. Must be true/false.")
            sys.exit(1)
        # add to blocking services if needed
        if service['block_startup_scripts']:
            globals.blocking_services.append(service)

    logger.info(f"Required services: {globals.required_services}")
    logger.info(f"Blocking services: {globals.blocking_services}")
    globals.blocking_threadpool = ThreadPoolExecutor(thread_name_prefix="BlockingServices")

    # Check for service logger config in yml & assign if enabled
    services_list = conf.get('services_to_log')
    if not services_list:
        globals.services_list = services_list
        logger.info("No services configured for logging.")
    else:
        for index,entry in enumerate(services_list):
            if ('host' not in entry) or ('password' not in entry) or ('service' not in entry):
                logger.error("services_to_log missing data in yaml, please ensure all required parts are entered. (host, password, or service data).Exiting.")
                sys.exit(1)
            if ('user' not in entry) or (entry['user'] == None):
                services_list[index]['user'] = 'user'
        globals.services_list = services_list

    # configure startup scripts. Empty array if setting is not in config
    startup = conf.get('startup')
    if startup:
        globals.startup_scripts = startup.get('scripts') or []
        logger.info(f"Startup scripts: {globals.startup_scripts}")
        globals.startup_workspace = startup.get('runInWorkspace') or False
        logger.info(f"Run Startup Scripts in Workspace: {globals.startup_workspace}")
        # check to make sure each startup script is executable
        for startup_script in globals.startup_scripts:
            try:
                if not os.path.exists(f"{globals.custom_script_dir}/{startup_script}"):
                    logger.error(f"Startup script {globals.custom_script_dir}/{startup_script} does not exist.")
                    sys.exit(1)
                if not os.access(f"{globals.custom_script_dir}/{startup_script}", os.X_OK):
                    logger.error(f"Startup script {globals.custom_script_dir}/{startup_script} is not executable")
                    sys.exit(1)
            except Exception as e:
                logger.error(f"Got exception {e} while checking if startup script {globals.custom_script_dir}/{startup_script} exists and is executable.")
                sys.exit(1)

    # set hosted files. False if not set in config file
    globals.hosted_files_enabled = get_clean_env('CS_HOSTED_FILES', '').lower() =='true' or (conf.get('hosted_files') or {}).get('enabled') or False
    logger.info(f"Hosted files enabled: {globals.hosted_files_enabled}")

    # check status of `info` pages
    if get_clean_env('CS_INFO_HOME_ENABLED', '').lower() == 'true' or (conf.get('info_and_services') or {}).get('info_home_enabled'):
        globals.info_home_enabled = True

    if get_clean_env('CS_SERVICES_HOME_ENABLED', '').lower() == 'true' or (conf.get('info_and_services') or {}).get('services_home_enabled'):
        globals.services_home_enabled = True

    globals.xapi_enabled = get_clean_env('CS_XAPI_ENABLED', '').lower() == 'true' or (conf.get('xapi') or {}).get('enabled') or False
    logger.info(f"xAPI enabled: {globals.xapi_enabled}")

    globals.xapi_variables_location = get_clean_env('CS_XAPI_VARIABLES_LOCATION') or (conf.get('xapi') or {}).get('variables_location') or 'env'
    if globals.xapi_variables_location not in ['env', 'guestinfo']:
        logger.error(f"xAPI variable location: {globals.xapi_variables_location} is not valid. Must be 'env' or 'guestinfo'.")
        sys.exit(1)
    logger.info(f"xAPI variable source: {globals.xapi_variables_location}")

    if globals.xapi_enabled:
        globals.xapi_au_start_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
        # Load xAPI vars if xAPI is enabled
        load_xapi_variables()

def check_questions():
    with current_app.app_context():
        solved_tracker = 0
        questions = QuestionTracking.query.all()
        expected = len(questions)
        for q in questions:
            if q.solved == True:
                solved_tracker+= 1
        if solved_tracker == expected:
            globals.challenge_completed == True
            globals.challenge_completion_time = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            new_event = EventTracker(data=json.dumps({"challenge":globals.challenge_name, "support_code":globals.support_code, "event_type":"Challenge Completed","recorded_at":globals.challenge_completion_time}))
            db.session.add(new_event)
            db.session.commit()
            send_completed_xapi()


def get_current_phase():
    with current_app.app_context():
        if not PhaseTracking.query.filter_by().all():
            logger.info(f"PhaseTracking table is empty.")
            raise KeyError
        for phase in globals.phase_order:
            cur_phase = PhaseTracking.query.filter_by(label=phase).first()
            if cur_phase == None:
                logger.error(f"Queried for phase key that does not exist. key: {phase}.")
                raise KeyError
            if cur_phase.solved == False:
                globals.current_phase = cur_phase.label
                return cur_phase.label
        globals.challenge_completed == True
        globals.challenge_completion_time = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        return "completed"


def update_db(type_q,label=None, val=None):
    with current_app.app_context():
        if type_q == 'q':
            try:
                cur_question = QuestionTracking.query.filter_by(label=label).first()
                if cur_question == None:
                    logger.error("Update Database: No entry found in DB while attempting to mark question completed. Exiting")
                    sys.exit(1)
                if (val != None) and ('--' in val):
                    cur_question.response = val.split('--',1)[1]
                if ('--' not in val) and (cur_question.response == ''):
                    cur_question.response = "N/A"
                was_solved = cur_question.solved
                if "success" in val.lower():
                    cur_question.solved = True
                    cur_question.time_solved = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                    # xAPI: If newly solved, send question-level 'passed' statement
                    if not was_solved:
                        part_info = globals.grading_parts.get(label, {})
                        question_text = part_info.get('text', '')
                        user_response = cur_question.response
                        send_question_statement(label, question_text, True)
                else:
                    # xAPI: If newly failed, send question-level 'failed' statement
                    if not was_solved:
                        part_info = globals.grading_parts.get(label, {})
                        question_text = part_info.get('text', '')
                        user_response = cur_question.response
                        send_question_statement(label, question_text, False)
                db.session.commit()
            except Exception as e:
                logger.error(f"Exception updating DB with completed question. Exception: {e}. Exiting.")
                sys.exit(1)

        else:
            for p in globals.phase_order:
                phase = PhaseTracking.query.filter_by(label=p).first()
                if phase == None:
                    logger.error("No entry found in DB while attempting to find current phase during DB update. Exiting")
                    sys.exit(1)
                if phase.solved == False:
                    q_list = phase.tasks.split(',')
                    num_q = len(q_list)
                    for q in q_list:
                        cur_q = QuestionTracking.query.filter_by(label=q).first()
                        if cur_q == None:
                            logger.error("No entry found in DB while attempting to update phase DB. Exiting")
                            sys.exit(1)
                        if cur_q.solved == True:
                            num_q -= 1
                    if num_q == 0:
                        phase.solved = True
                        phase.time_solved = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                        db.session.commit()
                    else:
                        globals.current_phase = phase.label
                        return


#######
# Grading Functions
#######
def do_grade(args):
    '''
    This method is the grading and token reading for all manual questions
    The method gets called from the Jinja template rendering (inside { } in the graded.html file)
    '''

    globals.fatal_error = False
    manual_grading_list = list()
    for ques,ans in args.items():
        if (ques not in globals.grading_parts.keys()) or (globals.grading_parts[ques]['mode'] not in globals.VALID_CONFIG_MODES):
            logger.debug(f"The key {ques} is not a a grading key/mode. Skipping")
            continue
        if (globals.grading_parts[ques]['mode'] in globals.MANUAL_MODE) and (globals.grading_parts[ques]['mode'] != "button"):
            index = int(ques[-1])
            manual_grading_list.insert(index,{ques:ans})

    script_path = os.path.join(globals.custom_script_dir, globals.manual_grading_script)
    _, ext = os.path.splitext(script_path)
    # Start building the command
    if ext == ".py":
        grade_cmd = [sys.executable, script_path]  # Use venv's Python if python script
    else:
        grade_cmd = [script_path]

    # Add JSON-encoded arguments if present
    grade_args = {}
    if manual_grading_list:
        for entry in manual_grading_list:
            grade_args[list(entry.keys())[0]] = list(entry.values())[0]
        grade_cmd.append(json.dumps(grade_args))

    # Handle phase logic
    if globals.phases_enabled:
        current_phase = get_current_phase()
        if current_phase != 'completed':
            grade_cmd.append(current_phase)
        else:
            tmp = [f'{grade_key} : Success' for grade_key in globals.grading_parts.keys()]
            results = dict(tmp)
            return get_results(results)

    try:
        out = subprocess.run(grade_cmd, capture_output=True, check=True)
        logger.info(f"Grading script finished: {out}")
        output = out.stdout.decode('utf-8')
        if (output == "") or (output == None):
            logger.error("Grading script finished without returning any output.")
            globals.fatal_error = True
    # Something happened if there was a non-zero exit status. Log this and set fatal_error
    except subprocess.CalledProcessError as e:
        logger.error(f"Grading script {globals.manual_grading_script} returned with non-zero exit status {e.returncode}.\tStdout: {e.stdout}\tStderr: {e.stderr}")
        globals.fatal_error = True
        output = ""

    results = []
    for sub in output.split('\n'):
        if ':' in sub:
            results.append(map(str.strip, sub.split(':', 1)))
    results = dict(results)

    with current_app.app_context():
        event_data = {
            "challenge":globals.challenge_name,
            "support_code":globals.support_code,
            "event_type":"Grading Result",
            "output":results,
            "recorded_at": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        new_event = EventTracker(data=json.dumps(event_data))
        db.session.add(new_event)
        db.session.commit()

    # ensure all grading parts have a result
    for grading_key in globals.grading_parts.keys():
        if globals.grading_parts[grading_key]['mode'] not in globals.MANUAL_MODE:
            continue
        if not globals.phases_enabled:
            if grading_key not in results:
                logger.info(f"Grading script, {globals.manual_grading_script}, did not yield a result for grading part {grading_key}. Assigning value of 'Failed'")
                results[grading_key] = "Failed"

    for k,v in results.items():
        update_db('q',k,v)

    return get_results(results)


def check_db(label):
    with current_app.app_context():
        cur_question = QuestionTracking.query.filter_by(label=label).first()
        if cur_question == None:
            logger.error("Check Database: No entry found in DB while attempting to mark question completed. Exiting")
            sys.exit(1)
        return cur_question.solved


def get_results(results):
    # for each result that is returned, check if success is in the message.
    # If success is in the message, then read and store the token for that check
    end_results = results.copy()
    tokens = {}
    for key, value in results.items():
        if key not in globals.grading_parts.keys():
            logger.info(f"Found key in results that is not a grading part. Removing {key} from results dict. ")
            del end_results[key]
        if "success" in value.lower():
            tokens[key] = read_token(key)
        elif check_db(key):             ### check DB to see if failed question was passed previously & update results accordingly
            results[key] = "Success"
            tokens[key] = read_token(key)
        else:
            tokens[key] = "You did not earn a token for this part"
    if globals.phases_enabled == True:
        update_db('p')
    return end_results, tokens


def done_grading(future: Future):
    '''
    Callback function for do_grade.
    Checks to see if the results need to be PUT to the grading server
    '''
    results, tokens = future.result()
    logger.info(f"Server sees {globals.manual_grading_script} results as: {results}")
    logger.info(f"Server sees tokens as: {tokens}")

    # save results and tokens so they can be accessed globally
    globals.manual_results = results
    globals.tokens['manual'] = tokens

    if globals.grader_post:
        post_submission(tokens)


def post_submission(tokens: dict):
    '''
    This method will send a POST to the grader for automatic grading.
    All POST attempts are logged.
    Method will try 4 times (sleep 1 second between each failed attempt).
    After 4 failures, the method will log an error and return.
    '''
    token_values = tokens.values()


    # build the request headers and payload to send to the grader
    headers = {
        "accept": "text/plain",
        "Content-Type": "application/json",
        "x-api-key": f"{globals.grader_key}"
    }
    payload = f'{{"id":"{globals.challenge_id}","sectionIndex":0,"questions":['
    for token in token_values:
        payload = payload + f'{{"answer":"{token}"}},'
    payload = payload[:-1] + "]}"


    # Try to POST results to the grader 4 times
    ## return immediately on success
    ## log error if still failure after 4 tries
    attempts = 0
    while attempts < 4:
        logger.info(f"Attempting {globals.grading_verb} submission to URL: {globals.grader_url}\tHeaders: {headers}\tPayload: {payload}")
        attempts = attempts + 1
        try:
            if globals.grading_verb == "POST":
                r = requests.post(globals.grader_url, data=payload, headers=headers)
                if r.status_code == 200:
                    logger.info(f"Got 200 from {globals.grader_url} after POST")
                    globals.fatal_error = False
                    return
                elif r.status_code == 405:
                    logger.info(f"Got 405 from {globals.grader_url} after POST. Changing to PUT.")
                    globals.grading_verb = "POST"
                else:
                    logger.error(f"Got {r.status_code} from {globals.grader_url} attempting to POST. Message: {r.content}")
            if globals.grading_verb == "PUT":
                r = requests.put(globals.grader_url, data=payload, headers=headers)
                if r.status_code == 200:
                    logger.info(f"Got 200 from {globals.grader_url} after PUT")
                    globals.fatal_error = False
                    return
                else:
                    logger.error(f"Got {r.status_code} from {globals.grader_url} attempting to PUT. Message: {r.content}")
        except Exception as e:
            logger.error(f"Got exception {e} while trying to PUT/POST data to {globals.grader_url}")

        sleep(1)
        logger.info("Trying grader submission again after failure on previous attempt.")


    logger.error(f"All attempts to submit results to grader failed.\tURL: {globals.grader_url}\tVerb: {globals.grading_verb}\tHeaders: {headers}\tPayload: {payload}")
    globals.fatal_error = True


#######
# Cron grading
#######
def set_cron_vars(conf):
    '''
    Set the value of the cron global vars
    Try reading values from environment variables. Fall back to config file, then defaults or error.
    '''

    # set cron grading script. Error if script is not defined or not executable
    globals.grading_mode.append('cron')
    globals.cron_grading_script = get_clean_env('CS_CRON_GRADING_SCRIPT') or conf['grading'].get('cron_grading_script')
    if not globals.cron_grading_script:
        logger.error(f"Cron grading not script defined.")
        sys.exit(1)
    logger.info(f"Cron grading script: {globals.custom_script_dir}/{globals.cron_grading_script}")
    try:
        if not os.access(f"{globals.custom_script_dir}/{globals.cron_grading_script}", os.X_OK):
            logger.error(f"Cron grading script {globals.custom_script_dir}/{globals.cron_grading_script} is not executable")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Got exception {e} while checking if grading script {globals.custom_script_dir}/{globals.cron_grading_script} is executable.")
        sys.exit(1)

    globals.cron_interval = int(get_clean_env('CS_CRON_INTERVAL') or conf['grading'].get('cron_interval') or 60)
    logger.info(f"cron_interval: {globals.cron_interval}")

    globals.cron_limit = int(get_clean_env('CS_CRON_LIMIT') or conf['grading'].get('cron_limit') or -1)
    logger.info(f"cron_limit: {globals.cron_limit}")

    globals.cron_delay = int(get_clean_env('CS_CRON_DELAY') or conf['grading'].get('cron_delay') or 0)
    logger.info(f"cron_delay: {globals.cron_delay}")

    globals.cron_at = get_clean_env('CS_CRON_AT') or conf['grading'].get('cron_at') or None
    logger.info(f"cron_at: {globals.cron_at}")

    # calculates the total delay by using the cron_at setting and adding it to the cron_delay
    if globals.cron_at is not None:
        globals.cron_type = "at"
        time = globals.cron_at.split(':')
        current_time = datetime.datetime.now()

        start_time = datetime.datetime(current_time.year, current_time.month, current_time.day, hour=int(time[0]), minute=int(time[1]))
        logger.info(f"Cron style grading should begin at {start_time}")

        time_diff = (start_time - current_time).total_seconds()
    else:
        globals.cron_type = "every"
        time_diff = 0

    globals.cron_delay = globals.cron_delay + time_diff


def do_cron_grade():
    '''
    Grading and token reading for cron
    The method gets called from the Jinja template rendering (inside { } in the graded.html file)
    '''
    globals.fatal_error = False

    try:
        out = subprocess.run([f"{globals.custom_script_dir}/{globals.cron_grading_script}"], capture_output=True, check=True)
        logger.info(f"Grading script finished: {out}")
        output = out.stdout.decode('utf-8')

    # Something happened if there was a non-zero exit status. Log this and set fatal_error
    except subprocess.CalledProcessError as e:
        logger.error(f"Grading script {globals.manual_grading_script} returned with non-zero exit status {e.returncode}.\tStdout: {e.stdout}\tStderr: {e.stderr}")
        globals.fatal_error = True
        output = ""

    results = []
    for sub in output.split('\n'):
        if ':' in sub:
            results.append(map(str.strip, sub.split(':', 1)))

    results = dict(results)

    # ensure all grading parts have a result
    for grading_key in globals.grading_parts.keys():
        if globals.grading_parts[grading_key]['mode'] != 'cron':
            continue
        if grading_key not in results:
            logger.info(f"Grading script, {globals.cron_grading_script}, did not yield a result for grading part {grading_key}. Assigning value of 'Failed'")
            results[grading_key] = "Failed"

    # for each result that is returned, check if success is in the message.
    # If success is in the message, then read and store the token for that check
    end_results = results.copy()
    tokens = {}
    for key, value in results.items():
        if key not in globals.grading_parts.keys():
            logger.info(f"Found key in results that is not a grading part. Removing {key} from results dict. ")
            del end_results[key]
        if "success" in value.lower():
            tokens[key] = read_token(key)
        else:
            tokens[key] = "You did not earn a token for this part"

    logger.info(f"Grading Results: {end_results}")
    logger.info(f"Grading tokens: {tokens}")
    return end_results, tokens

def run_cron_thread():
    '''
    Run do_grade on a timer via a thread (similar to a cron job)
    '''
    limit = globals.cron_limit
    logger.info(f"Starting cron thread with interval {globals.cron_interval}. Grading is limited to running {limit} times.")

    cron_attempts = 0
    while globals.cron_limit != 0:
        cron_attempts += 1
        globals.cron_limit = globals.cron_limit - 1
        globals.cron_submit_time = datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S")
        logger.info(f"Starting cron grading attempt number {cron_attempts}")
        globals.cron_results, tokens = do_cron_grade()
        globals.tokens['cron'] = tokens
        if globals.grader_post:
            post_submission(tokens)
        logger.info(f"Results of cron grading attempt number {cron_attempts}: {globals.cron_results}")
        sleep(globals.cron_interval)
    logger.info(f"The number of grading attempts ({limit}) has been exhausted. No more grading will take place.")



#######
# Token functions
#######
def read_token(part_name):
    '''
    This method takes a Check name as an argument. Examples can be "Check1", "Check2", etc.
    '''

    # get the token name for this part
    try:
        value = globals.grading_parts[part_name]['token_name']
    except KeyError:
        logger.error(f"There is no match for {part_name} in the config file. Valid part names from config file are: {globals.grading_parts.keys()}")
        if globals.grader_post:
            globals.fatal_error = True
        return "Unexpected error encountered. Contact an administrator."

    # read tokens from env var
    if globals.token_location == 'env':
        token = get_clean_env(value)
        if not token:
            logger.error(f"Environment variable for token {value} is empty.")
            if globals.grader_post:
                globals.fatal_error = True
            return "Unexpected error encountered. Contact an administrator."
        else:
            return token

    # read tokens from guestinfo
    elif globals.token_location == 'guestinfo':
        try:
            output = subprocess.run(f"vmtoolsd --cmd 'info-get guestinfo.{value}'", shell=True, capture_output=True)
            if 'no value' in output.stderr.decode('utf-8').lower():
                logger.error(f"No value found when querying guestinfo variables for guestinfo.{value}")
                if globals.grader_post:
                    globals.fatal_error = True
                return "Unexpected error encountered. Contact an administrator."
            return output.stdout.decode('utf-8').strip()
        except:
            logger.error("Error when trying to get token from guestinfo vars")
            if globals.grader_post:
                globals.fatal_error = True
            return "Unexpected error encountered. Contact an administrator."

    # read token from file
    elif globals.token_location == 'file':
        try:
            with open(f"{globals.basedir}/app/tokens/{value}", 'r') as f:
                return f.readline()
        except:
            logger.error(f"Error opening file {value} when trying to read token for check {part_name}")
            if globals.grader_post:
                globals.fatal_error = True
            return "Unexpected error encountered. Contact an administrator."


def get_logs(service):
    log_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    while True:
        sleep(10)
        error = ''
        try:
            ## `systemctl is-active` to get/log service info
            get_status_cmd = f"sshpass -p {service['password']} ssh -o StrictHostKeyChecking=no {service['user']}@{service['host']} 'systemctl is-active {service['service']}'"
            status_response = subprocess.run(get_status_cmd, shell=True,capture_output=True, timeout=10)
        except subprocess.TimeoutExpired:
            logger.error(f"SERVICE_LOGGER: request to host timed out.")
            globals.services_status[service['service']] = [service['host'],f"request to host timed out. Trying again shortly"]
            continue
        except Exception as e:
            logger.error(f"SERVICE_LOGGER: Exception attempting to retrieve service status: {e}")
            globals.services_status[service['service']] = [service['host'],f"Exception attempting to retrieve service status."]
            continue
        if status_response.stdout.decode('utf-8') == '':
            logger.error(f"SERVICE_LOGGER: Failed to get service status. Error: {status_response.stderr.decode('utf-8')}")
            globals.services_status[service['service']] = [service['host'],f"Error has occurred when attempting to get service status."]
            continue
        if status_response.stdout.decode('utf-8').strip('\n') == 'failed':
            error = "SERVICE FAILED: "
            logger.error(f"SERVICE_LOGGER: {error} {service['service']}")
            globals.services_status[service['service']] = [service['host'],f"Service is in failed state."]
        elif status_response.stdout.decode('utf-8').strip('\n') == 'inactive':
            error = "SERVICE INACTIVE: "
            logger.error(f"SERVICE_LOGGER: {error} {service['service']}")
            globals.services_status[service['service']] = [service['host'],f"Service is in inactive state."]
        else:
            globals.services_status[service['service']] = [service['host'],f"Service is in active state."]
        ## grab logs
        try:
            get_log_cmd = f"sshpass -p {service['password']} ssh -o StrictHostKeyChecking=no {service['user']}@{service['host']} 'journalctl --since \"{log_time}\" -u {service['service']}'"
            log_response = subprocess.run(get_log_cmd, shell=True,capture_output=True,timeout=10)
            cur_logs = log_response.stdout.decode('utf-8')
        except subprocess.TimeoutExpired:
            logger.error(f"SERVICE_LOGGER: SSH connection to {service['user']}@{service['host']} timed out.")
            continue
        except Exception as e:
            logger.error(f"SERVICE_LOGGER: Exception attempting to retrieve logs: {e}")
            continue
        if log_response.stdout.decode('utf-8') == '':
            logger.error(f"SERVICE_LOGGER: Failed to collect logs. Error: {log_response.stderr.decode('utf-8')}")
            continue
        if "No entries" in cur_logs:
            if error:
                logger.error(f"SERVICE_LOGGER: {error} No new logs fe.")
            else:
                logger.info(f"SERVICE_LOGGER: No new logs found at this time.")
            continue
        output = cur_logs.split("\n")
        output.remove("")
        for line in output:
            if error == False:
                logger.info(f"SERVICE_LOGGER: {line}")
            else:
                logger.error("SERVICE_LOGGER: "+ error + line)
        log_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def record_solves():
    with globals.scheduler.app.app_context():
        objs = {
            "Question Solved": QuestionTracking.query.all(),
            "Phase Solved":PhaseTracking.query.all()
        }
        for k,v in objs.items():
            for q in v:
                if q.solved == True:
                    cur_data = {
                        "challenge":globals.challenge_name,
                        "support_code":globals.support_code,
                        "event_type":k,
                        k: q.label,
                        "solved_at": q.time_solved,
                        "recorded_at": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    new_event = EventTracker(data=json.dumps(cur_data))
                    db.session.add(new_event)
                    db.session.commit()


#######
# xAPI/CMI5 Functions
#######
def load_xapi_variables():
    """
    Loads xAPI values into globals
    """
    globals.xapi_endpoint     = read_xapi_value('CS_CMI5_ENDPOINT')
    globals.xapi_registration = read_xapi_value('CS_CMI5_REGISTRATION')
    globals.xapi_fetch        = read_xapi_value('CS_CMI5_FETCH')
    globals.xapi_session_id   = read_xapi_value('CS_CMI5_SESSIONID')
    globals.xapi_activity_id  = read_xapi_value('CS_CMI5_ACTIVITYID')
    globals.xapi_auth_token   = read_xapi_value('CS_CMI5_AUTH')

    # JSON values
    globals.xapi_actor = read_xapi_value('CS_CMI5_ACTOR', decode_json=True) or {}
    
    context = read_xapi_value('CS_CMI5_CONTEXT', decode_json=True) or {}
    context["registration"] = globals.xapi_registration
    globals.xapi_context = context

def read_xapi_value(key, decode_json=False):
    """
    Reads xAPI-related variables based on location config (env, guestinfo).
    """
    location = globals.xapi_variables_location

    value = None

    if location == "env":
        value = get_clean_env(key)

    elif location == "guestinfo":
        try:
            output = subprocess.run(
                f"vmtoolsd --cmd 'info-get guestinfo.{key}'",
                shell=True,
                capture_output=True
            )
            if 'no value' not in output.stderr.decode('utf-8').lower():
                value = output.stdout.decode('utf-8').strip()
            else:
                logger.warning(f"[guestinfo] No value found for guestinfo.{key}")
        except Exception as e:
            logger.warning(f"[guestinfo] Failed to read guestinfo.{key}: {e}")

    if not value:
        logger.warning(f"[xAPI] No value found for key: {key} using method: {location}")
        return None

    if decode_json:
        try:
            return json.loads(value)
        except Exception as e:
            logger.error(f"[xAPI] Failed to decode JSON for {key}: {e}")
            return None

    return value


def send_xapi_statement(statement: dict, statement_id: str):
    """
    Sends a single xAPI statement
    """
    
    # Uses the same UUID generated in the statement
    statement["id"] = statement_id

    endpoint = f"{globals.xapi_endpoint}/statements?statementId={statement_id}"
    
    headers = {
        "Content-Type": "application/json",
        "X-Experience-API-Version": "1.0.3",
        "Authorization": f"{globals.xapi_auth_token}"
    }

    try:
        resp = requests.put(endpoint, json=statement, headers=headers, timeout=5)
        if resp.status_code not in (204,):
            logger.error(f"[xAPI] Failed to PUT statement: {resp.status_code} {resp.text}")
        else:
            verb_id = statement.get("verb", {}).get("id", "")
            logger.info(f"[xAPI] Statement PUT successfully (verb={verb_id}, id={statement_id}).")
    except Exception as e:
        logger.error(f"[xAPI] Exception sending statement: {e}")

def send_completed_xapi():
    """
    Send a CMI5-compliant 'completed' statement at the AU level.
    """
    if not globals.xapi_enabled:
        return

    now = datetime.datetime.now(datetime.timezone.utc)
    statement_id = str(uuid.uuid4())
    au_id = f"{globals.xapi_activity_id}"

    session_start = globals.xapi_au_start_time
    if isinstance(session_start, str):
        session_start = datetime.datetime.fromisoformat(session_start)

    duration_seconds = (now - session_start).total_seconds()
    duration = datetime.timedelta(seconds=duration_seconds)
    iso_duration = isodate.duration_isoformat(duration)

    statement = {
        "id": statement_id,
        "actor": globals.xapi_actor,
        "verb": {
            "id": "http://adlnet.gov/expapi/verbs/completed",
            "display": {"en-US": "completed"}
        },
        "object": {
            "id": au_id,
            "objectType": "Activity",
            "definition": {
                "name": {"en-US": globals.challenge_name},
                "description": {"en-US": "All questions solved"},
                "type": "http://adlnet.gov/expapi/activities/lesson"
            }
        },
        "result": {
            "completion": True,
            "duration": iso_duration
        },
        "context": get_cmi5_defined_context([
            "https://w3id.org/xapi/cmi5/context/categories/cmi5",
            "https://w3id.org/xapi/cmi5/context/categories/moveon"
        ]),
        "timestamp": now.isoformat()
    }
    send_xapi_statement(statement, statement_id)
    send_terminated_xapi()


def send_terminated_xapi():
    """
    Send a CMI5-compliant 'terminated' statement at the AU level when session ends.
    """
    if not globals.xapi_enabled:
        return

    now = datetime.datetime.now(datetime.timezone.utc)
    statement_id = str(uuid.uuid4())
    au_id = f"{globals.xapi_activity_id}"

    session_start = globals.xapi_au_start_time
    if isinstance(session_start, str):
        session_start = datetime.datetime.fromisoformat(session_start)

    duration_seconds = (now - session_start).total_seconds()
    duration = datetime.timedelta(seconds=duration_seconds)
    iso_duration = isodate.duration_isoformat(duration)

    statement = {
        "id": statement_id,
        "actor": globals.xapi_actor,
        "verb": {
            "id": "http://adlnet.gov/expapi/verbs/terminated",
            "display": {"en-US": "terminated"}
        },
        "object": {
            "id": au_id,
            "objectType": "Activity",
            "definition": {
                "name": {"en-US": globals.challenge_name},
                "type": "http://adlnet.gov/expapi/activities/lesson"
            }
        },
        "result": {
            "duration": iso_duration
        },
        "context": get_cmi5_defined_context([
            "https://w3id.org/xapi/cmi5/context/categories/cmi5"
        ]),
        "timestamp": now.isoformat()
    }
    send_xapi_statement(statement, statement_id)


def send_question_statement(question_label: str, question_text: str, success: bool):
    """
    Send a question-level 'answered' statement with result.
    """
    if not globals.xapi_enabled:
        return

    statement_id = str(uuid.uuid4())
    now = datetime.datetime.now(datetime.timezone.utc)
    au_id = f"{globals.xapi_activity_id}"

    statement = {
        "id": statement_id,
        "actor": globals.xapi_actor,
        "verb": {
            "id": "http://adlnet.gov/expapi/verbs/answered",
            "display": {"en-US": "answered"}
        },
        "object": {
            "objectType": "Activity",
            "id": au_id,
            "definition": {
                "name": {"en-US": question_label},
                "description": {"en-US": question_text}
            }
        },
        "result": {
            "success": success
        },
        "context": globals.xapi_context,
        "timestamp": now.isoformat()
    }

    send_xapi_statement(statement, statement_id)

def get_cmi5_defined_context(categories=None):
    """
    Appends required categories activities to the context 
    """
    context = copy.deepcopy(globals.xapi_context)

    if categories is None:
        categories = []

    if "contextActivities" not in context:
        context["contextActivities"] = {}

    existing_category = context["contextActivities"].get("category", [])
    existing_ids = {act.get("id") for act in existing_category}

    for category_id in categories:
        if category_id not in existing_ids:
            existing_category.append({
                "id": category_id,
                "objectType": "Activity"
            })

    context["contextActivities"]["category"] = existing_category
    return context
