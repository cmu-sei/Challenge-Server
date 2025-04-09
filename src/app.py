#!/usr/bin/env python3
#
# Challenge Sever
# Copyright 2024 Carnegie Mellon University.
# NO WARRANTY. THIS CARNEGIE MELLON UNIVERSITY AND SOFTWARE ENGINEERING INSTITUTE MATERIAL IS FURNISHED ON AN "AS-IS" BASIS. CARNEGIE MELLON UNIVERSITY MAKES NO WARRANTIES OF ANY KIND, EITHER EXPRESSED OR IMPLIED, AS TO ANY MATTER INCLUDING, BUT NOT LIMITED TO, WARRANTY OF FITNESS FOR PURPOSE OR MERCHANTABILITY, EXCLUSIVITY, OR RESULTS OBTAINED FROM USE OF THE MATERIAL. CARNEGIE MELLON UNIVERSITY DOES NOT MAKE ANY WARRANTY OF ANY KIND WITH RESPECT TO FREEDOM FROM PATENT, TRADEMARK, OR COPYRIGHT INFRINGEMENT.
# Licensed under a MIT (SEI)-style license, please see license.txt or contact permission@sei.cmu.edu for full terms.
# [DISTRIBUTION STATEMENT A] This material has been approved for public release and unlimited distribution.  Please see Copyright notice for non-US Government use and distribution.
# DM24-0645
#


import sys, random, threading, os, signal
from flask_executor import Executor
from flask_cors import CORS
from concurrent.futures import ThreadPoolExecutor
from app import create_app, start_grading_server, run_startup_scripts
from app.functions import read_config, done_grading, get_logs
from app.portServiceChecker import waitForService, checkServiceLoop, checkLocalPortLoop
from app.extensions import logger, globals

# Create flask app obj
app = create_app()
if __name__ == '__main__':
    '''
    This code will start the threads and handle running all aspect of the server
    '''
    if os.geteuid() != 0:
        logger.error("Must be run by root.")
        exit(1)

    CORS(app)
    globals.executor = Executor(app)
    globals.executor.add_default_done_callback(done_grading)

    # Read the configuration
    logger.info(f"Starting up")
    logger.info("Operating in a Workspace" if globals.in_workspace else "Operating in a Gamespace")
    read_config(app)

    # start the website
    grading_server_thread = threading.Thread(target=start_grading_server, name="GradingServer", args=(app,))
    grading_server_thread.start()

    # wait for blocking services to come up
    logger.info(f"Waiting for blocking services to become available")
    globals.blocking_threadpool.map(waitForService, globals.blocking_services)
    globals.blocking_threadpool.shutdown(wait=True)
    logger.info(f"All blocking services are available")

    # run startup scripts
    successes, errors = run_startup_scripts()
    if errors:
        logger.error(f"Startup scripts exited with error(s): {list(errors.keys())}")
        exit(1)
    if successes:
        logger.info(f"All startup scripts exited normally: {list(successes.keys())}")

    globals.server_ready = True # mark server as ready after startup scripts finish

    # run a thread that will periodically list the local open ports
    port_checker_thread = threading.Thread(target=checkLocalPortLoop, name="LocalPortChecker")

    if globals.required_services:
        # run a thread that will periodically check on all required services
        service_check_pool = ThreadPoolExecutor(thread_name_prefix="ServiceCheck")
        service_check_pool.map(checkServiceLoop, globals.required_services)

    if globals.services_list:
        # run a thread that will periodically get logs from required services
        service_logger_pool = ThreadPoolExecutor(thread_name_prefix="Service_Logger")
        service_logger_pool.map(get_logs, globals.services_list)

    port_checker_thread.start()
    grading_server_thread.join()
