#!/usr/bin/env python3
#
# Challenge Sever
# Copyright 2024 Carnegie Mellon University.
# NO WARRANTY. THIS CARNEGIE MELLON UNIVERSITY AND SOFTWARE ENGINEERING INSTITUTE MATERIAL IS FURNISHED ON AN "AS-IS" BASIS. CARNEGIE MELLON UNIVERSITY MAKES NO WARRANTIES OF ANY KIND, EITHER EXPRESSED OR IMPLIED, AS TO ANY MATTER INCLUDING, BUT NOT LIMITED TO, WARRANTY OF FITNESS FOR PURPOSE OR MERCHANTABILITY, EXCLUSIVITY, OR RESULTS OBTAINED FROM USE OF THE MATERIAL. CARNEGIE MELLON UNIVERSITY DOES NOT MAKE ANY WARRANTY OF ANY KIND WITH RESPECT TO FREEDOM FROM PATENT, TRADEMARK, OR COPYRIGHT INFRINGEMENT.
# Licensed under a MIT (SEI)-style license, please see license.txt or contact permission@sei.cmu.edu for full terms.
# [DISTRIBUTION STATEMENT A] This material has been approved for public release and unlimited distribution.  Please see Copyright notice for non-US Government use and distribution.
# DM24-0645
#


import yaml, os, subprocess, datetime, sys, ipaddress
from flask import Flask
from concurrent.futures import ThreadPoolExecutor
from time import sleep
from app.extensions import logger, globals, db
from app.env import get_clean_env
from app.models import QuestionTracking,PhaseTracking
from app.cmi5 import cmi5_load_variables
from app.databaseHelpers import get_current_phase
from app.cron import set_cron_vars


####### parse `config.yml` and assign values to globals object
def read_config(app: Flask) -> None:
    """
     Apply app configurations by reading from env vars or the config file.
     Always prefer values present in env vars over the config file.

    Args:
        app (Flask): This Flask app

    Raises:
        ValueError: Raised when configs are expected but not present.
    """

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

    globals.port_checker = get_clean_env('CS_PORT_CHECKER', '').lower() == 'true'or conf.get('port_checker') or False

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

        globals.grading_uploads.update(conf['grading'].get('uploads', {}))
        if 'files' in globals.grading_uploads:
            files = globals.grading_uploads['files']
            max_upload_size = globals.grading_uploads.setdefault('max_upload_size', '1M')
            match max_upload_size[-1]:
                case 'G':
                    multiplier = 1024 * 1024 * 1024
                case 'M':
                    multiplier = 1024 * 1024
                case 'K':
                    multiplier = 1024
                case _:
                    multiplier = 1
            try:
                size_value = int(max_upload_size[:-1])
            except ValueError:
                logger.error(f"Max upload size {max_upload_size} should end with G, M, K, or a numeric value.")
                sys.exit(1)
            app.config['MAX_CONTENT_LENGTH'] = size_value * multiplier

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

    globals.cmi5_enabled = get_clean_env('CS_CMI5_ENABLED', '').lower() == 'true' or (conf.get('cmi5') or {}).get('enabled') or False
    logger.info(f"CMI5 enabled: {globals.cmi5_enabled}")

    if globals.cmi5_enabled:
        globals.cmi5_au_start_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
        cmi5_load_variables(conf)


def get_logs(service: dict) -> None:
    """Get the logs of a logged service by using SSH.

    Args:
        service (dict): Service dictionary
    """

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
