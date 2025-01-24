#!/usr/bin/python3

import os, sys, time, subprocess,datetime, yaml, logging
from multiprocessing import Pool

challenge_id = subprocess.run(f"vmtoolsd --cmd 'info-get guestinfo.isolationTag'", shell=True, capture_output=True).stdout.decode('utf-8').strip().replace("-", "")
support_code = challenge_id[:8]
variant_index = subprocess.run(f"vmtoolsd --cmd 'info-get guestinfo.variant'", shell=True, capture_output=True).stdout.decode('utf-8').strip()
variant_index = "-1" if not variant_index or "##" in variant_index or len(variant_index) > 2 else str(int(variant_index) + 1)
challenge_code = subprocess.run(f"vmtoolsd --cmd 'info-get guestinfo.code'", shell=True, capture_output=True).stdout.decode('utf-8').strip()
challenge_code = "workspace" if not challenge_code or "##" in challenge_code else challenge_code


logging.basicConfig(format=f" CHALLENGE-SERVER | %(host)s | MonitoredServices | %(levelname)s | {support_code} | {challenge_code} | %(service)s | %(message)s",level=logging.INFO)
logger = logging.getLogger("monitoredservices")

def get_logs(service):
    log_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    host_info = {"host":service['host'],"service":service['service']}
    while True:
        time.sleep(10)
        # `er` variable is intended to track if a service is 'fve' and log messages with `.error` rather than `.info`
        er = False
        
        ## below SSH cmd uses `is-active` option with `systemctl` where the response should be either `active`, `failed`, or `inactive` and then Log info accordingly.
        try:
            get_status_cmd = f"sshpass -p {service['password']} ssh -o StrictHostKeyChecking=no {service['user']}@{service['host']} 'systemctl is-active {service['service']}'"
            status_response = subprocess.run(get_status_cmd, shell=True,capture_output=True, timeout=10)
        except subprocess.TimeoutExpired:
            logger.error(f"SSH connection to host timed out.",extra=host_info)
            continue
        except Exception as e:
            logger.error(f"Exception has occurred when attempting to retrieve service status.",extra=host_info)
            logger.error(f"Exception: {e}",extra=host_info)
            continue
        if status_response.stdout.decode('utf-8') == '':
            logger.error(f"Error has occurred when attempting to get service status.",extra=host_info)
            logger.error(f"Error: {status_response.stderr.decode('utf-8')}",extra=host_info)
            continue
        if status_response.stdout.decode('utf-8').strip('\n') == 'failed':
            er = "SERVICE FAILED: "
            logger.error(f"{er} {service['service']} is in failed state.",extra=host_info)
        elif status_response.stdout.decode('utf-8').strip('\n') == 'inactive':
            er = "SERVICE INACTIVE: "
            logger.error(f"{er} {service['service']} is in inactive state.",extra=host_info)
        
        ## grab logs
        try:
            get_log_cmd = f"sshpass -p {service['password']} ssh -o StrictHostKeyChecking=no {service['user']}@{service['host']} 'journalctl --since \"{log_time}\" -u {service['service']}'"
            log_response = subprocess.run(get_log_cmd, shell=True,capture_output=True,timeout=10)
            cur_logs = log_response.stdout.decode('utf-8')
        except subprocess.TimeoutExpired:
            logger.error(f"SSH connection to host timed out.",extra=host_info)
            continue
        except Exception as e:
            logger.error(f"Exception has occurred when attempting to retrieve logs.",extra=host_info)
            logger.error(f"Exception: {e}")
            continue
        if log_response.stdout.decode('utf-8') == '':
            logger.error(f"Error has occurred when attempting to collect logs.",extra=host_info)
            logger.error(f"Error: {log_response.stderr.decode('utf-8')}",extra=host_info)
            continue
        if "No entries" in cur_logs:
            if er != False:
                logger.error(f"{er} No new logs found at this time.",extra=host_info)
            else:
                logger.info(f"No new logs found at this time.",extra=host_info)
            continue
        output = cur_logs.split("\n")
        output.remove("")
        
        for line in output:
            if er == False:
                logger.info(line,extra=host_info)
            else:
                logger.error(er + line,extra=host_info)
        log_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def handle_threads(services):
    host_info = {"host":"Challenge Server","service":"monitoredServices"}
    while True:
        try:
            mp_pool = Pool(processes=int(len(services)))
            mp_pool.map(get_logs, services)
            mp_pool.close()
            mp_pool.join()
        except Exception as e:
            logger.error(f"Exception has been raised and service logging threads have exited. Attempting restart.",extra=host_info)
            logger.error(f"Exception:\t{e}",extra=host_info)
            mp_pool.terminate()
        else:
            logger.error(f"Service logging threads closed unexpectedly. Attempting restart.",extra=host_info)
            mp_pool.terminate()


def check_yaml():
    ## configured to work as long as services_config.yml is in the same directory as the script. 
    host_info = {"host":"Challenge Server","service":"monitoredServices"}
    basedir = os.path.abspath(os.path.dirname(__file__))
    with open(f"{basedir}/services_config.yml",'r') as config_file:
        try:
            conf = yaml.safe_load(config_file)
        except yaml.YAMLError:
            logger.error("Error reading services_config.yml file.",extra=host_info)
            sys.exit(1)
    if conf['startup']['runInWorkspace'] == False:
        challenge_code = subprocess.run(f"vmtoolsd --cmd 'info-get guestinfo.code'", shell=True, capture_output=True).stdout.decode('utf-8').strip()
        challenge_code = "workspace" if not challenge_code or "##" in challenge_code else challenge_code
        if challenge_code == 'workspace':
            logger.info("Not running in workspace",extra=host_info)
            sys.exit(1)
    services_list = conf['services_to_log'] if 'services_to_log' in conf else []
    if services_list == []:
        logger.info("No services entered in services_config.yml.",extra=host_info)
        sys.exit(1)
    for index,entry in enumerate(services_list):
        if ('host' not in entry) or ('password' not in entry) or ('service' not in entry):
            logger.info("services_config.yml missing data, please ensure all required parts are entered. (host, password, or service data).Exiting.",extra=host_info)
            sys.exit(1)
        if ('user' not in entry) or (entry['user'] == None):
            services_list[index]['user'] = 'user'
    return services_list

if __name__ == "__main__":
    services = check_yaml()
    handle_threads(services)
