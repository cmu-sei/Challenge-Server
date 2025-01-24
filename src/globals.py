#
# Challenge Sever
# Copyright 2024 Carnegie Mellon University.
# NO WARRANTY. THIS CARNEGIE MELLON UNIVERSITY AND SOFTWARE ENGINEERING INSTITUTE MATERIAL IS FURNISHED ON AN "AS-IS" BASIS. CARNEGIE MELLON UNIVERSITY MAKES NO WARRANTIES OF ANY KIND, EITHER EXPRESSED OR IMPLIED, AS TO ANY MATTER INCLUDING, BUT NOT LIMITED TO, WARRANTY OF FITNESS FOR PURPOSE OR MERCHANTABILITY, EXCLUSIVITY, OR RESULTS OBTAINED FROM USE OF THE MATERIAL. CARNEGIE MELLON UNIVERSITY DOES NOT MAKE ANY WARRANTY OF ANY KIND WITH RESPECT TO FREEDOM FROM PATENT, TRADEMARK, OR COPYRIGHT INFRINGEMENT.
# Licensed under a MIT (SEI)-style license, please see license.txt or contact permission@sei.cmu.edu for full terms.
# [DISTRIBUTION STATEMENT A] This material has been approved for public release and unlimited distribution.  Please see Copyright notice for non-US Government use and distribution.
# DM24-0645
#

import yaml, logging, subprocess, os
from datetime import timedelta, time
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger("challengeServer")

VALID_CONFIG_MODES = ['button', 'cron', 'text', 'text_single']
VALID_TOKEN_LOCATIONS = ['guestinfo', 'file']
VALID_SUBMISSION_METHODS = ['display', 'grader_post']
VALID_SERVICE_TYPES = ['ping', 'socket', 'web']

def init():
    # important directories
    global custom_script_dir
    global hosted_file_directory
    custom_script_dir = os.path.abspath("../custom_scripts")
    hosted_file_directory = os.path.abspath("../hosted_files")

    # configuration globals
    global conf
    global startup_workspace
    global startup_scripts
    global required_services
    global blocking_services
    global blocking_threadpool
    global grading_enabled
    global hosted_files_enabled
    global grading_mode
    global grading_script
    global grading_rateLimit
    global grading_parts
    global token_location
    global submission_method
    global challenge_id
    challenge_id = subprocess.run(f"vmtoolsd --cmd 'info-get guestinfo.isolationTag'", shell=True, capture_output=True).stdout.decode('utf-8').strip().replace("-", "")
    conf = None
    startup_workspace = False
    startup_scripts = None
    required_services = []
    blocking_services = []
    blocking_threadpool = None
    grading_enabled = None
    hosted_files_enabled = None
    grading_mode = None
    grading_script = None
    grading_rateLimit = timedelta(seconds=0)
    grading_parts = None
    token_location = None
    submission_method = None

    # gameboard submission globals
    global grader_url
    global grader_key
    grader_url = ""
    grader_key = ""

    # cron specific globals
    global cron_limit
    global cron_interval
    global cron_delay
    global cron_at
    cron_limit = None
    cron_interval = None
    cron_delay = None
    cron_at = None

    # submission/grading runtime globals
    global submit_time
    global results
    global tokens
    global grading_verb
    submit_time = time().strftime("%m/%d/%Y %H:%M:%S")
    results = None
    tokens = None
    grading_verb = "POST"

    # other
    global fatal_error
    global in_workspace
    global support_code
    global challenge_code
    global variant_index

    # get challenge support code - the first 8 chars of the full challenge_id
    support_code = challenge_id[:8]

    # get the variant 
    ## If there is no variant transform passed in, assign variant = -1
    ## If the variant index contains ##, assign variant = -1 (probably a workspace VM)
    ## If the variant index is longer than 2 chars long, assign variant = -1 (this is a single-variant infinity challenge)
    ## If a valid variant index is present, add 1 to it to account for 0-indexing  (index 0 = Variant 1 of the challenge)
    variant_index = subprocess.run(f"vmtoolsd --cmd 'info-get guestinfo.variant'", shell=True, capture_output=True).stdout.decode('utf-8').strip()
    variant_index = "-1" if not variant_index or "##" in variant_index or len(variant_index) > 2 else str(int(variant_index) + 1)

    # get the challenge code (e.g., c00)
    ## If there is no code transform passed in, assign code to be "workspace" (probably a workspace VM)
    ## If the code contains ##, assign code to be "workspace" (probably a workspace VM)
    ## Challenge code remains what is passed in if 2 above conditions are false
    challenge_code = subprocess.run(f"vmtoolsd --cmd 'info-get guestinfo.code'", shell=True, capture_output=True).stdout.decode('utf-8').strip()
    challenge_code = "workspace" if not challenge_code or "##" in challenge_code else challenge_code
    fatal_error = False
    in_workspace = True if "workspace" in challenge_code else False

def read_config():
    global conf
    # parse config file
    with open('../config.yml', 'r') as config_file:
        try:
            conf = yaml.safe_load(config_file)
            logger.info(f"Challenge Server Config: {conf}")
        except yaml.YAMLError:
            logger.error("Error Reading YAML in config file")
            exit(1)

    # configure required services. Empty array if setting is not in config
    global required_services
    global blocking_services
    required_services = conf['required_services'] if 'required_services' in conf else []
    blocking_services = []
    for service in required_services:
        # ensure host is defined in required services
        if 'host' not in service:
            logger.error(f"Missing host definition in required service: {service}")
            exit(1)
        # ensure type is defined in required services. If not defined, default to ping type. 
        if 'type' not in service:
            logger.info(f"Missing type definition in required service: {service}. Defaulting to ping.")
            service['type'] = "ping"
        # ensure defined type is valid
        if service['type'] not in VALID_SERVICE_TYPES:
            logger.error(f"Invalid required service type in: {service}. Valid types are {VALID_SERVICE_TYPES}.")
            exit(1)
        # ensure port is defined for socket type
        if service['type'] == 'socket' and 'port' not in service:
            logger.error(f"Missing port definition in required service: {service}. Port definition is required with socket type")
            exit(1)
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
            exit(1)
        # add to blocking services if needed
        if service['block_startup_scripts']:
            blocking_services.append(service)

    logger.info(f"Required services: {required_services}")
    logger.info(f"Blocking services: {blocking_services}")
    global blocking_threadpool
    blocking_threadpool = ThreadPoolExecutor(thread_name_prefix="BlockingServices")


    # configure startup scripts. Empty array if setting is not in config
    if 'startup' in conf:
        global startup_scripts
        global startup_workspace
        global custom_script_dir
        startup_scripts = conf['startup']['scripts'] if 'scripts' in conf['startup'] else []  
        logger.info(f"Startup scripts: {startup_scripts}")
        startup_workspace = conf['startup']['runInWorkspace'] if 'runInWorkspace' in conf['startup'] else False
        logger.info(f"Run Startup Scripts in Workspace: {startup_workspace}")
        # check to make sure each startup script is executable
        for startup_script in startup_scripts:
            try:
                if not os.path.exists(f"{custom_script_dir}/{startup_script}"):
                    logger.error(f"Startup script {custom_script_dir}/{startup_script} does not exist.")
                    exit(1)
                if not os.access(f"{custom_script_dir}/{startup_script}", os.X_OK):
                    logger.error(f"Startup script {custom_script_dir}/{startup_script} is not executable")
                    exit(1)
            except Exception as e:
                logger.error(f"Got exception {e} while checking if startup script {custom_script_dir}/{startup_script} exists and is executable.")
                exit(1)

    # set hosted files. False if not set in config file
    global hosted_files_enabled
    hosted_files_enabled = conf['hosted_files']['enabled'] if 'hosted_files' in conf and 'enabled' in conf['hosted_files'] else False
    logger.info(f"Hosted files enabled: {hosted_files_enabled}")

    # set grading enabled. False if not set in config file
    global grading_enabled
    grading_enabled = conf['grading']['enabled'] if 'grading' in conf and 'enabled' in conf['grading'] else False
    logger.info(f"Grading enabled: {grading_enabled}")

    # only process grading configs if grading is enabled
    if grading_enabled:

        # set grading mode. Error if mode is not defined/recognized
        if 'mode' not in conf['grading']:
            logger.error(f"Grading mode is not defined. Mode is required when grading is enabled")
            exit(1)
        if conf['grading']['mode'] not in VALID_CONFIG_MODES:
            logger.error(f"Error parsing config file. Mode: {conf['grading']['mode']} is not recognized. Options are: {VALID_CONFIG_MODES}")
            exit(1)
        else: 
            global grading_mode
            grading_mode = conf['grading']['mode']
            logger.info(f"Grading mode: {grading_mode}")

        # set grading script. Error if script is not defined or not executable
        if 'grading_script' not in conf['grading']:
            logger.error(f"Grading script is not defined in config file. Grading script is required when grading is enabled.")
            exit(1)
        
        global grading_script
        grading_script = conf['grading']['grading_script']
        logger.info(f"Grading script: {grading_script}")
        try:
            if not os.access(f"{custom_script_dir}/{grading_script}", os.X_OK):
                logger.error(f"Grading script {grading_script} is not executable")
                exit(1)
        except Exception as e:
            logger.error(f"Got exception {e} while checking if grading script {grading_script} is executable.")
            exit(1)

        # set grading rate limit. 0 if not defined
        global grading_rateLimit
        grading_rateLimit = timedelta(seconds=conf['grading']['rate_limit']) if 'rate_limit' in conf['grading'] else timedelta(seconds=0)
        logger.info(f"Grading Rate limit: {grading_rateLimit.total_seconds().__int__()} seconds")

        # set grading parts. Error if not defined
        if 'parts' not in conf['grading']:
            logger.error(f"Grading parts is not defined in config file. Grading parts is required when grading is enabled.")
            exit(1)

        global grading_parts 
        grading_parts = conf['grading']['parts']

        # set token location. "guestinfo" is default. Error if not recognized.
        global token_location
        token_location = conf['grading']['token_location'] if 'token_location' in conf['grading'] else 'guestinfo'
        if token_location not in VALID_TOKEN_LOCATIONS:
            logger.error(f"Error parsing config file. Token Location: {conf['grading']['token_location']} is not recognized. Options are: {VALID_TOKEN_LOCATIONS}")
            exit(1)
        logger.info(f"Token location: {token_location}")

        # set grading submission method. "display" is default. Error if not recognized
        global submission_method
        submission_method = conf['grading']['submission']['method'] if 'submission' in conf['grading'] and 'method' in conf['grading']['submission'] else 'display'
        if submission_method not in VALID_SUBMISSION_METHODS:
            logger.error(f"Error parsing config file. Submission Method: {conf['grading']['submission']['method']} is not recognized. Options are: {VALID_SUBMISSION_METHODS}")
            exit(1)
        logger.info(f"Submission method: {submission_method}")

        # additional configuration for grader_post
        if submission_method == "grader_post":
            global grader_url
            # use guestinfo variable for grader_url or use the config file setting if there is no guestinfo variable
            get_grader_url_cmd = subprocess.run(f"vmtoolsd --cmd 'info-get guestinfo.grader_url'", shell=True, capture_output=True)
            if 'no value' in get_grader_url_cmd.stderr.decode('utf-8').lower() and 'grader_url' not in conf['grading']['submission']:
                logger.error(f"grader_url is not defined in config file or guestinfo variables. grader_url is required when submission method if grader_post.")
                exit(1)
            else:
                grader_url = get_grader_url_cmd.stdout.decode('utf-8').strip().replace('http:', 'https:') if 'no value' not in get_grader_url_cmd.stderr.decode('utf-8').lower() else conf['grading']['submission']['grader_url']
                logger.info(f"Grader URL: {grader_url}")

            global grader_key
            # use guestinfo variable for grader_url or use the config file setting if there is no guestinfo variable
            get_grader_key_cmd = subprocess.run(f"vmtoolsd --cmd 'info-get guestinfo.grader_key'", shell=True, capture_output=True)
            if 'no value' in get_grader_key_cmd.stderr.decode('utf-8').lower() and 'grader_key' not in conf['grading']['submission']:
                logger.error(f"grader_key is not defined in config file or guestinfo variables. grader_key is required when submission method if grader_post.")
                exit(1)
            else:
                grader_key = get_grader_key_cmd.stdout.decode('utf-8').strip() if 'no value' not in get_grader_url_cmd.stderr.decode('utf-8').lower() else conf['grading']['submission']['grader_key']
                logger.info(f"Grader Key: {grader_key}")
