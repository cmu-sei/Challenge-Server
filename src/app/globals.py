#!/usr/bin/env python3

import subprocess, os, logging
from flask_apscheduler import APScheduler
from datetime import timedelta, time
# from concurrent.futures import ThreadPoolExecutor

class Globals():
    def __init__(self):
        # Information from config.yml
        self.VALID_CONFIG_MODES = ['button', 'cron', 'text', 'text_single']
        self.MANUAL_MODE = ['button', 'text', 'text_single']
        self.VALID_TOKEN_LOCATIONS = ['guestinfo', 'file']
        self.VALID_SUBMISSION_METHODS = ['display', 'grader_post']
        self.VALID_SERVICE_TYPES = ['ping', 'socket', 'web']
        # important directories and files
        self.basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.custom_script_dir = f"{self.basedir}/custom_scripts"
        self.hosted_file_directory = f"{self.basedir}/hosted_files"
        self.yaml_path =  f"{self.basedir}/config.yml"
        self.ssl_dir = f"{self.basedir}/app/ssl"
        #####self.img_dir = f"{self.basedir}/"
        # configuration globals
        challenge_id = subprocess.run(f"vmtoolsd --cmd 'info-get guestinfo.isolationTag'", shell=True, capture_output=True).stdout.decode('utf-8').strip().replace("-", "")
        self.challenge_id = challenge_id
        self.startup_workspace = False
        self.startup_scripts = None
        self.required_services = []
        self.blocking_services = []
        self.blocking_threadpool = None
        self.grading_enabled = None
        self.hosted_files_enabled = None
        self.grading_mode = list()
        self.manual_grading_script = None
        self.cron_grading_script = None
        self.grading_rateLimit = timedelta(seconds=0)
        self.grading_parts = None
        self.question_order = list()
        self.token_location = None
        self.submission_method = None
        self.grader_post = False
        self.services_list= None
        self.services_status = dict()
        self.q_modes = set()
        self.question_order = []
        self.lab_completed = False
        self.lab_completion_time = ""
        self.info_home_enabled = False
        self.services_home_enabled = False
        # gameboad submission globals
        self.grader_url = ""
        self.grader_key = ""
        # cron specific globals
        self.cron_limit = None
        self.cron_interval = None
        self.cron_delay = None
        self.cron_at = None
        self.cron_type = None
        # submission/grading runtime globals
        self.manual_submit_time = time().strftime("%m/%d/%Y %H:%M:%S")
        self.cron_submit_time = time().strftime("%m/%d/%Y %H:%M:%S")
        self.manual_results = None
        self.cron_results = None
        self.tokens = {
            "manual":dict(),
            "cron":dict()
            }
        self.grading_verb = "POST"
        self.phases_enabled = False
        self.phases = None
        self.phase_order = []
        self.current_phase = None
        # other
        self.support_code = challenge_id[:8]
        variant_index = subprocess.run(f"vmtoolsd --cmd 'info-get guestinfo.variant'", shell=True, capture_output=True).stdout.decode('utf-8').strip()
        variant_index = "-1" if not variant_index or "##" in variant_index or len(variant_index) > 2 else str(int(variant_index) + 1)
        self.variant_index = variant_index
        challenge_code = subprocess.run(f"vmtoolsd --cmd 'info-get guestinfo.code'", shell=True, capture_output=True).stdout.decode('utf-8').strip()
        challenge_code = "workspace" if not challenge_code or "##" in challenge_code else challenge_code
        self.challenge_code = challenge_code
        self.fatal_error = False
        self.in_workspace = True if "workspace" in challenge_code else False
        # attributes to track current status of server
        self.task = None
        self.server_ready = False
        self.executor = None
        ## scheduler contains scheduler object that is referenced when add/pausing/deleting jobs. 
        self.scheduler = APScheduler()
        self.lab_name = ""