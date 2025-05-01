#!/usr/bin/env python3
#
# Challenge Sever
# Copyright 2024 Carnegie Mellon University.
# NO WARRANTY. THIS CARNEGIE MELLON UNIVERSITY AND SOFTWARE ENGINEERING INSTITUTE MATERIAL IS FURNISHED ON AN "AS-IS" BASIS. CARNEGIE MELLON UNIVERSITY MAKES NO WARRANTIES OF ANY KIND, EITHER EXPRESSED OR IMPLIED, AS TO ANY MATTER INCLUDING, BUT NOT LIMITED TO, WARRANTY OF FITNESS FOR PURPOSE OR MERCHANTABILITY, EXCLUSIVITY, OR RESULTS OBTAINED FROM USE OF THE MATERIAL. CARNEGIE MELLON UNIVERSITY DOES NOT MAKE ANY WARRANTY OF ANY KIND WITH RESPECT TO FREEDOM FROM PATENT, TRADEMARK, OR COPYRIGHT INFRINGEMENT.
# Licensed under a MIT (SEI)-style license, please see license.txt or contact permission@sei.cmu.edu for full terms.
# [DISTRIBUTION STATEMENT A] This material has been approved for public release and unlimited distribution.  Please see Copyright notice for non-US Government use and distribution.
# DM24-0645
#


import subprocess, re, socket, requests
from datetime import datetime
from time import sleep
from app.extensions import globals, logger


def checkLocalPorts() -> str:
    """
    Runs a subprocess to list open TCP and UDP ports

    Returns:
        str: Stdout from the subprocess command
    """

    stdout = subprocess.run("ss -nltup", shell=True, capture_output=True).stdout.decode("UTF-8")
    return stdout


def checkLocalPortLoop(interval: int = 30) -> None:
    """
    Checks open ports forever in a loop. Default time between checks is 30s.
    Logs results to the same logger as the rest of the Challenge Server.
    Logs in a more readable format written to /var/log/open-ports

    Args:
        interval (int, optional): Seconds to wait between checks. Defaults to 30.
    """

    logger.info(f"Checking local open ports every {interval} seconds")
    while True:
        date = datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
        open_ports = checkLocalPorts()
        stripped = re.sub(r"\s+", " ", open_ports).replace("\n", "\\n")
        logger.info(f"Open ports: {stripped}")

        with open("/var/log/open-ports", "a") as f:
            f.write(f"""
########
{date}
{open_ports}""")
        sleep(interval)


def isIPv4(host: str) -> bool:
    """
    Checks the IP version of a given address
    Returns True if the address is IPv4
    Returns False if the address is IPv6
    If host is a hostname/FQDN, attempts to resolve as IPv4
    If unsuccessful, assumes address is IPv6

    Args:
        host (str): Hostname or IP Address

    Returns:
        bool: True if address is IPv4. False if address is IPv6
    """

    if isValidIPv4(host):
        logger.info(f"Regex matched {host} as a valid IPv4 address")
        return True
    elif isValidIPv6(host):
        logger.info(f"Regex matched {host} as a valid IPv6 address")
        return False
    else:
        try:
            ipAddr = socket.gethostbyname(str(host))
            logger.info(f"Resolved IPv4 address is {ipAddr}")
            return True
        except socket.gaierror as e:
            errNum = e.errno
            if errNum == int(-5):
                logger.info(f"Treating {host} as an IPv6 address")
                return False
            elif errNum == int(-3):
                logger.error(f"Failed to resolve {host} - Check DNS Entry. Assuming IPv4 in the meantime")
                return True
            else:
                logger.error(f"Socket Error in isIPv4 Function - {e}. Assuming IPv4 in the meantime")
                return True
        except Exception as e:
            logger.error(f"Exception in isIPv4 Function - {e}. Assuming IPv4 in the meantime")
            return True


def isValidIPv4(host: str) -> bool:
    """
    Returns True if the given host is a valid IPv4 address.

    Args:
        host (str): IP Address

    Returns:
        bool: Returns True if the given host is a valid IPv4 address.
    """

    ipv4_re = re.compile(
        (r'((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.)'
         r'{3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])'))
    return bool(ipv4_re.match(host))


def isValidIPv6(host: str) -> bool:
    """
    Returns True if the given host is a valid IPv6 address.

    Args:
        host (str): IP Address

    Returns:
        bool: Returns True if the given host is a valid IPv6 address.
    """

    ipv6_re = re.compile(
        (r'([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|'
         r'([0-9a-fA-F]{1,4}:){1,7}:|'
         r'([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|'
         r'([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|'
         r'([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|'
         r'([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|'
         r'([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|'
         r'[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|'
         r':((:[0-9a-fA-F]{1,4}){1,7}|:)|'
         r'fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|'
         r'::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|'
         r'(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|'
         r'(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|'
         r'([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|'
         r'(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|'
         r'(2[0-4]|1{0,1}[0-9]){0,1}[0-9])'))
    return bool(ipv6_re.match(host))


def checkPing(host: str, count: int = 1) -> bool:
    """
    Checks to see if a host is able to be reached via ping

    Args:
        host (str): Hostname/IP address to ping
        count (int, optional): Number of pings to attempt. Defaults to 1.

    Returns:
        bool:     Returns True if the host can be pinged. Returns False if the host cannot be pinged.
    """

    logger.info(f"Pinging host {host}")
    try:
        results = subprocess.run(f"ping {host} -W 1 -c {count}", shell=True, capture_output=True)
        exit_code = results.returncode
        stdout_string = " \\n ".join(line.strip() for line in results.stdout.decode("UTF-8").splitlines())
        stderr_string = " \\n ".join(line.strip() for line in results.stderr.decode("UTF-8").splitlines())
        logger.info(f"Exit code {exit_code} from pinging {host}")
        if exit_code == 0:
            logger.info(f"Successful ping to host {host} - {stdout_string}")
            return True
        logger.error(f"Failed to ping host {host} - {stderr_string}")
        return False
    except Exception as e:
        logger.error(f"Failed to ping host {host}. Got exception {str(e)}")
        return False


def checkSocket(host: str, port: str|int) -> bool:
    """
    Checks to see if a remote socket (host/port pair) is reachable

    Args:
        host (str): Hostname or IP Address
        port (str|int): Port number

    Returns:
        bool: Returns True if socket connection is successful (port is reachable)
              Returns False if socket connection failed (port is not reachable)

    """

    logger.info(f"Attempting to connect to socket {host}:{port}")
    success = False
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) if isIPv4(host) else socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((host, int(port)))
        s.shutdown(socket.SHUT_RDWR)
        logger.info(f"Successful connection to socket {host}:{port}")
        success = True
    except socket.gaierror as e:
        logger.error(f"Failed connection to socket {host}:{port}. Get Address Info (DNS) error prevented socket connection. Exception: {e}")
    except TimeoutError as e:
        logger.error(f"Failed connection to socket {host}:{port}. Connection timeout.")
    except Exception as e:
        logger.error(f"Failed connection to connect to socket {host}:{port}. Exception {e}")
    finally:
        s.close()
    return success


def checkWeb(host: str, port: str|int = 80, path:str = '/') -> bool:
    """
    Checks connection to a web URL

    Args:
        host (str): Hostname or IP Address of web server
        port (str, optional): Website port. Defaults to 80.
        path (str, optional): URI path. Defaults to '/'.

    Returns:
        bool: Returns True if the web request returns a 200
              Returns False if the web request returns anything but a 200
    """

    fqdn = re.compile(r'(?=^.{4,253}$)(^((?!-)[a-zA-Z0-9-]{1,63}(?<!-)\.)+[a-zA-Z]{2,63}\.?$)')
    if fqdn.search(host):  # Check if host is FQDN. If True, IP version does not matter.
        url = f"http://{host}:{port}{path}"
        logger.info("checkWeb is using FQDN")

    #  If host is an IP address, IP version is checked as IPv6 requires [ ] brackets
    elif isIPv4(host):
        url = f"http://{host}:{port}{path}"
        logger.info("checkWeb is using IPv4")
    else:
        url = f"http://[{host}]:{port}{path}"
        logger.info("checkWeb is using IPv6")

    logger.info(f"Attempting to reach {url}")
    try:
        result = requests.get(url=url)
        logger.info(f"Web request returned {result.status_code}: {result.content}")
        return result.status_code == 200
    except requests.exceptions.Timeout as e:
        logger.error(f"Failed connection to {url}. Connection Timeout Exception: {e}")
    except requests.exceptions.InvalidURL as e:
        logger.error(f"Failed connection to {url}. Invalid URL Exception: {e}")
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Failed connection to {url}. Connection Error: {e}")
    except Exception as e:
        logger.error(f"Failed connection to {url}. Got Exception: {e}")

    return False


def checkService(service: dict) -> bool:
    """
    Check if a given service is reachable.

    Args:
        service (dict): Service dict with keys expected according to
                        the standard required_service config

    Returns:
        bool: Returns True if the service is reachable.
              Returns False if the service is unreachable.
    """

    logger.info(f"Checking availability of service: {service}")
    reachable = False
    service_type = service['type']
    if service_type == 'ping':
        reachable = checkPing(service['host'])
    elif service_type == 'socket':
        reachable = checkSocket(service['host'], service['port'])
    elif service_type == 'web':
        reachable = checkWeb(service['host'], service['port'], service['path'])

    if reachable:
        logger.info(f"Service available: {service}")
        return True
    else:
        logger.error(f"Service unavailable: {service}")
        return False


def waitForService(service: dict, interval: int = 2, max_attempts: int = 0) -> bool:
    """
    Checks the service in a loop until it becomes available or max_attempts is reached.
    Returns once the service is available or max_attempts is reached.

    Args:
        service (dict): Service dict with keys expected according to
                        the standard required_service config
        interval (int, optional): Seconds between re-checking service. Defaults to 2.
        max_attempts (int, optional): Maximum number of times to check. Defaults to 0.

    Returns:
        bool: Returns True is the service is available.
              Returns False if the service is not available before max_attempts is reached.
    """

    service_available = False
    attempts = 0
    while True:
        attempts += 1
        logger.info(f"Waiting for service to become available (attempt number {attempts}): {service}")
        service_available = checkService(service)
        if service_available:
            return service_available
        if max_attempts and attempts == max_attempts:
            logger.error(f"Service unavailable after max attempts ({attempts}): {service}")
            return False
        sleep(interval)


def checkServiceLoop(service: dict, interval: int = 30, max_checks: int = 0) -> bool:
    """
    Checks the availability of a service forever in a loop (or until max_checks is reached).

    Args:
        service (dict): Service dict with keys expected according to
                        the standard required_service config
        interval (int, optional): Seconds between re-checking service. Defaults to 30.
        max_checks (int, optional): Maximum number of times to check. Defaults to 0.

    Returns:
        bool: Returns True only when the maximum number of checks have completed.
    """

    logger.info(f"Checking service {service} every {interval} seconds")
    attempts = 0
    while True:
        attempts += 1
        logger.info(f"Service check number {attempts} for {service}")
        checkService(service)
        if max_checks and attempts == max_checks:
            logger.info(f"Reached the maximum number of service checks ({max_checks}).. Will no longer check on service {service}.")
            return True
        sleep(interval)


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
