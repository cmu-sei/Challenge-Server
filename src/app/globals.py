#!/usr/bin/env python3
#
# Challenge Sever
# Copyright 2024 Carnegie Mellon University.
# NO WARRANTY. THIS CARNEGIE MELLON UNIVERSITY AND SOFTWARE ENGINEERING INSTITUTE MATERIAL IS FURNISHED ON AN "AS-IS" BASIS. CARNEGIE MELLON UNIVERSITY MAKES NO WARRANTIES OF ANY KIND, EITHER EXPRESSED OR IMPLIED, AS TO ANY MATTER INCLUDING, BUT NOT LIMITED TO, WARRANTY OF FITNESS FOR PURPOSE OR MERCHANTABILITY, EXCLUSIVITY, OR RESULTS OBTAINED FROM USE OF THE MATERIAL. CARNEGIE MELLON UNIVERSITY DOES NOT MAKE ANY WARRANTY OF ANY KIND WITH RESPECT TO FREEDOM FROM PATENT, TRADEMARK, OR COPYRIGHT INFRINGEMENT.
# Licensed under a MIT (SEI)-style license, please see license.txt or contact permission@sei.cmu.edu for full terms.
# [DISTRIBUTION STATEMENT A] This material has been approved for public release and unlimited distribution.  Please see Copyright notice for non-US Government use and distribution.
# DM24-0645
#


import os
from flask_apscheduler import APScheduler
from datetime import timedelta, time
from app.env import get_clean_env

class Globals():
    def __init__(self):
        # app config
        self.app_host = None
        self.app_port = None
        self.app_cert = None
        self.app_key = None

        # From config.yml
        self.VALID_CONFIG_MODES = ['button', 'cron', 'text', 'text_single', 'mc']
        self.MANUAL_MODE = ['button', 'text', 'text_single', 'mc']
        self.VALID_TOKEN_LOCATIONS = ['env', 'guestinfo', 'file']
        self.VALID_SUBMISSION_METHODS = ['display', 'grader_post']
        self.VALID_SERVICE_TYPES = ['ping', 'socket', 'web']
        # files/directories
        self.basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.custom_script_dir = f"{self.basedir}/custom_scripts"
        self.hosted_file_directory = f"{self.basedir}/hosted_files"
        self.yaml_path =  f"{self.basedir}/config.yml"
        # configuration globals
        challenge_id = get_clean_env('CS_ISOLATION_TAG', '')
        self.challenge_id = challenge_id
        self.startup_workspace = False
        self.startup_scripts = None
        self.required_services = []
        self.blocking_services = []
        self.blocking_threadpool = None
        self.grading_enabled = None
        self.hosted_files_enabled = False
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
        self.challenge_completed = False
        self.challenge_completion_time = ""
        self.info_home_enabled = False
        self.services_home_enabled = False
        # submission globals
        self.grader_url = ""
        self.grader_key = ""
        # cron globals
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
        variant_index = get_clean_env('CS_VARIANT')
        self.variant_index = "-1" if not variant_index or "##" in variant_index or len(variant_index) > 2 else variant_index
        challenge_code = get_clean_env('CS_CODE', '')
        self.challenge_code = "workspace" if not challenge_code or "##" in challenge_code else challenge_code
        self.fatal_error = False
        self.in_workspace = True if "workspace" in challenge_code else False
        # current status
        self.task = None
        self.server_ready = False
        self.executor = None
        ## Scheduler is referenced when add/pausing/deleting jobs.
        self.scheduler = APScheduler()
        self.challenge_name = ""
