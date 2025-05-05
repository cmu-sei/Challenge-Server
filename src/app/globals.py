#!/usr/bin/env python3
#
# Challenge Sever
# Copyright 2024 Carnegie Mellon University.
# NO WARRANTY. THIS CARNEGIE MELLON UNIVERSITY AND SOFTWARE ENGINEERING INSTITUTE MATERIAL IS FURNISHED ON AN "AS-IS" BASIS. CARNEGIE MELLON UNIVERSITY MAKES NO WARRANTIES OF ANY KIND, EITHER EXPRESSED OR IMPLIED, AS TO ANY MATTER INCLUDING, BUT NOT LIMITED TO, WARRANTY OF FITNESS FOR PURPOSE OR MERCHANTABILITY, EXCLUSIVITY, OR RESULTS OBTAINED FROM USE OF THE MATERIAL. CARNEGIE MELLON UNIVERSITY DOES NOT MAKE ANY WARRANTY OF ANY KIND WITH RESPECT TO FREEDOM FROM PATENT, TRADEMARK, OR COPYRIGHT INFRINGEMENT.
# Licensed under a MIT (SEI)-style license, please see license.txt or contact permission@sei.cmu.edu for full terms.
# [DISTRIBUTION STATEMENT A] This material has been approved for public release and unlimited distribution.  Please see Copyright notice for non-US Government use and distribution.
# DM24-0645
#


import os, sys, yaml, socket, logging
from flask_apscheduler import APScheduler
from datetime import timedelta, time
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, List, Dict, Set, Union
from app.env import get_clean_env

class Globals:
    """
    Defines globally accessible variables and resolves them via environment -> config -> default.
    """

    def __init__(self) -> None:
        # Static defaults (non-configurable)
        self.VALID_CONFIG_MODES: List[str] = ['button', 'cron', 'text', 'text_single', 'mc', 'upload']
        self.MANUAL_MODE: List[str] = ['button', 'text', 'text_single', 'mc', 'upload']
        self.VALID_TOKEN_LOCATIONS: List[str] = ['env', 'guestinfo', 'file']
        self.VALID_SUBMISSION_METHODS: List[str] = ['display', 'grader_post']
        self.VALID_SERVICE_TYPES: List[str] = ['ping', 'socket', 'web']

        # Directories
        self.basedir: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.custom_script_dir: str = f"{self.basedir}/custom_scripts"
        self.hosted_file_directory: str = f"{self.basedir}/hosted_files"
        self.uploaded_file_directory: str = f"{self.basedir}/uploaded_files"
        self.yaml_path: str = f"{self.basedir}/config.yml"

        # Initialize overridable vars
        self.app_host: str = "0.0.0.0"
        self.app_port: int = 8888
        self.app_cert: Optional[str] = None
        self.app_key: Optional[str] = None
        self.challenge_name: str = ""
        self.port_checker: bool = False
        self.grading_enabled: bool = False
        self.hosted_files_enabled: bool = False
        self.info_home_enabled: bool = False
        self.services_home_enabled: bool = False

        # Configuration globals
        self.conf: dict = {}
        self.challenge_id: str = get_clean_env('CS_ISOLATION_TAG', 'NO_TAG')
        self.support_code: str = self.challenge_id[:8]
        self.variant_index: int = self._init_variant_index()
        self.challenge_code: str = self._init_challenge_code()
        self.in_workspace: bool = "workspace" in self.challenge_code

        self.startup_workspace: bool = False
        self.startup_scripts: List[str] = []
        self.required_services: List[dict] = []
        self.blocking_services: List[dict] = []
        self.blocking_threadpool = ThreadPoolExecutor(thread_name_prefix="BlockingServices")

        self.grading_mode: List[str] = []
        self.manual_grading_script: Optional[str] = None
        self.cron_grading_script: Optional[str] = None
        self.grading_rateLimit: timedelta = timedelta(seconds=0)
        self.grading_parts: Optional[dict] = None
        self.question_order: List[str] = []
        self.token_location: str = "env"
        self.submission_method: str = "display"
        self.grader_post: bool = False
        self.services_list: Optional[List[dict]] = None
        self.services_status: Dict[str, List[str]] = {}
        self.q_modes: Set[str] = set()
        self.challenge_completed: bool = False
        self.challenge_completion_time: str = ""
        self.grader_url: Optional[str] = ""
        self.grader_key: Optional[str] = ""

        # Cron
        self.cron_limit: Optional[int] = None
        self.cron_interval: Optional[int] = None
        self.cron_delay: Optional[int] = None
        self.cron_at: Optional[str] = None
        self.cron_type: Optional[str] = None

        # Runtime values
        now = time().strftime("%m/%d/%Y %H:%M:%S")
        self.manual_submit_time: str = now
        self.cron_submit_time: str = now
        self.manual_results: Optional[dict] = None
        self.cron_results: Optional[dict] = None
        self.tokens: Dict[str, Dict] = { "manual": {}, "cron": {} }
        self.grading_verb: str = "POST"

        # Phases
        self.phases_enabled: bool = False
        self.phases: Optional[dict] = None
        self.phase_order: List[str] = []
        self.current_phase: Optional[str] = None

        # Server state
        self.fatal_error: bool = False
        self.task: Optional[str] = None
        self.server_ready: bool = False
        self.executor = None
        self.scheduler: APScheduler = APScheduler()

        # CMI5
        self.cmi5_enabled: bool = False
        self.cmi5_au_start_time: str = ""
        self.cmi5_endpoint: str = ""
        self.cmi5_registration: str = ""
        self.cmi5_auth_token: str = ""
        self.cmi5_actor: Dict = {}
        self.cmi5_sessionid: str = ""
        self.cmi5_context: Dict = {}
        self.cmi5_activityid: str = ""
        self.grading_uploads: Dict = {}


    def __repr__(self) -> str:
        """
        Return a string representation of the object.

        Returns:
            str: String with each attribute/value listed on a new line
        """

        attrs = vars(self)
        lines = [f"{k}={v!r}" for k, v in sorted(attrs.items())]
        return f"<Globals:\n  " + "\n  ".join(lines) + "\n>"


    def _init_variant_index(self) -> int:
        """
        Return the variant index if it exists in env var. Default to -1.

        Returns:
            int: The variant index
        """

        variant = get_clean_env('CS_VARIANT')
        if variant and "##" not in variant and len(variant) <= 2:
            return int(variant)
        return -1


    def _init_challenge_code(self) -> str:
        """
        Return the challenge code if it exists in env var. Default to 'workspace'.

        Returns:
            str: The Challenge Code. Default is 'workspace'.
        """

        code = get_clean_env('CS_CODE', '')
        return "workspace" if not code or "##" in code else code


    def resolve(self, key: str, conf: dict, default: str = '') -> str:
        """
        Resolves a configuration value.
        Read from env var first. Then fallback to the configuration dictionary.
        If value does not exist in env var or config, use the provided default.

        Args:
            key (str): Config to lookup
            conf (dict): Configuration dictionary value.
            default (str, optional): Default value. Defaults to ''.

        Returns:
            str: The configuration value.
        """

        env_val = get_clean_env(key)
        if env_val is not None and env_val != "":
            return env_val
        return conf or default


    def resolve_bool(self, key: str, conf: Union[dict, bool], default: bool = False) -> bool:
        """
        Resolves a configuration boolean value.
        Read from env var first. Then fallback to the configuration dictionary.
        If value does not exist in env var or config, use the provided default.

        Args:
            key (str): Config to lookup
            conf (dict): Configuration dictionary value.
            default (str, optional): Default value. Defaults to ''.

        Returns:
            bool: The configuration value.
        """

        env_val = get_clean_env(key)
        if env_val:
            return env_val.lower() == 'true'
        if isinstance(conf, dict):
            return conf.get('enabled', default)
        return conf or default


    def resolve_int(self, key: str, conf_val, default: int) -> int:
        """
        Resolves a configuration int value.
        Read from env var first. Then fallback to the configuration dictionary.
        If value does not exist in env var or config, use the provided default.

        Args:
            key (str): Config to lookup
            conf (dict): Configuration dictionary value.
            default (str, optional): Default value. Defaults to ''.

        Returns:
            int: The configuration value.
        """

        val = get_clean_env(key)
        if val:
            try:
                return int(val)
            except ValueError:
                return default
        if isinstance(conf_val, int):
            return conf_val
        return default


    def resolve_ip(self, key: str, conf_val, default: str) -> str:
        """
        Resolves a configuration IP address value by ensuring it is a valid IP address.
        Read from env var first. Then fallback to the configuration dictionary.
        If value does not exist in env var or config, use the provided default.

        Args:
            key (str): Config to lookup
            conf (dict): Configuration dictionary value.
            default (str, optional): Default value. Defaults to ''.

        Returns:
            bool: The configuration value.
        """

        val = get_clean_env(key) or conf_val or default
        try:
            socket.gethostbyname(val)
            return val
        except (socket.gaierror, TypeError):
            logging.warning(f"Invalid IP or hostname '{val}', defaulting to '{default}'")
            return default


    def resolve_port(self, key: str, conf_val, default: int) -> int:
        """
        Resolves a configuration TCP port value by ensuring it is a valid TCP port.
        Read from env var first. Then fallback to the configuration dictionary.
        If value does not exist in env var or config, use the provided default.

        Args:
            key (str): Config to lookup
            conf (dict): Configuration dictionary value.
            default (str, optional): Default value. Defaults to ''.

        Returns:
            bool: The configuration value.
        """

        val = get_clean_env(key)
        if val:
            try:
                port = int(val)
                if 1 <= port <= 65535:
                    return port
            except ValueError:
                pass
        elif isinstance(conf_val, int) and 1 <= conf_val <= 65535:
            return conf_val
        logging.warning(f"Invalid port '{val or conf_val}', defaulting to {default}")
        return default


    def load_config(self, conf: dict):
        logging.info("Loading application config")
        self.conf = conf
        self.app_host = self.resolve_ip('CS_APP_HOST', conf.get('app', {}).get('host'), '0.0.0.0')
        self.app_port = self.resolve_port('CS_APP_PORT', conf.get('app', {}).get('port'), 8888)
        self.app_cert = self.resolve('CS_APP_CERT', conf.get('app', {}).get('tls_cert'))
        self.app_key = self.resolve('CS_APP_KEY', conf.get('app', {}).get('tls_key'))
        self.challenge_name = self.resolve('CS_CHALLENGE_NAME', conf.get('challenge_name'), "Challenge Server")
        self.port_checker = self.resolve_bool('CS_PORT_CHECKER', conf.get('port_checker'), False)
        self.grading_enabled = self.resolve_bool('CS_GRADING_ENABLED', conf.get('grading').get('enabled'), False)
        self.manual_grading_script = self.resolve('CS_MANUAL_GRADING_SCRIPT', conf.get('grading').get('manual_grading_script'))
        self.hosted_files_enabled = self.resolve_bool('CS_HOSTED_FILES', conf.get('hosted_files'), False)
        self.info_home_enabled = self.resolve_bool('CS_INFO_HOME_ENABLED', conf.get('info_and_services'), False)
        self.services_home_enabled = self.resolve_bool('CS_SERVICES_HOME_ENABLED', conf.get('info_and_services'), False)
        self.cmi5_enabled = self.resolve_bool('CS_CMI5_ENABLED', conf.get('cmi5'), False)
        self.grading_parts = conf['grading']['parts']
        manual_grading = self.resolve_bool('CS_MANUAL_GRADING', conf.get('grading').get('manual_grading'), self.grading_enabled)
        if manual_grading:
            self.grading_mode.append('manual')
        logging.debug(f"Final Config: {self}")


    @classmethod
    def from_yaml(cls, instance: Optional["Globals"] = None) -> "Globals":
        instance = instance or cls()
        if not os.path.isfile(instance.yaml_path):
            print("Could not find config.yml file.")
            sys.exit(1)

        with open(instance.yaml_path, 'r') as config_file:
            try:
                conf = yaml.safe_load(config_file)
            except yaml.YAMLError:
                print("Error Reading YAML in config file")
                sys.exit(1)

        instance.load_config(conf or {})
        return instance
