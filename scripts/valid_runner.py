#! /usr/bin/python -tt

import Queue
import threading
import boto
import time
import logging
import argparse
import yaml
import os
import sys
import sets
import paramiko
import random
import string
import tempfile
import traceback
import BaseHTTPServer
import urlparse
import ssl
import re

from patchwork.connection import Connection
from patchwork.expect import *
from boto import ec2
from boto.ec2.blockdevicemapping import BlockDeviceType
from boto.ec2.blockdevicemapping import BlockDeviceMapping

import valid


def csv(value):
    return map(str, value.split(","))

argparser = argparse.ArgumentParser(description='Run cloud image validation')
argparser.add_argument('--data', help='data file for validation')
argparser.add_argument('--config',
                       default="/etc/validation.yaml", help='use supplied yaml config file')
argparser.add_argument('--debug', action='store_const', const=True,
                       default=False, help='debug mode')
argparser.add_argument('--disable-tests', type=csv, help='disable specified tests')
argparser.add_argument('--enable-tests', type=csv, help='enable specified tests only (overrides --disabe-tests)')
argparser.add_argument('--maxtries', type=int,
                       default=30, help='maximum number of tries')
argparser.add_argument('--maxwait', type=int,
                       default=300, help='maximum wait time for instance creation')
argparser.add_argument('--numthreads', type=int,
                       default=10, help='number of worker threads')
argparser.add_argument('--results-dir',
                       default=False, help='put resulting yaml files to specified location')
argparser.add_argument('--server', action='store_const', const=True,
                       default=False, help='run HTTP server')
argparser.add_argument('--settlewait', type=int,
                       default=30, help='wait for instance to settle before testing')

args = argparser.parse_args()
maxtries = args.maxtries
maxwait = args.maxwait
settlewait = args.settlewait
num_worker_threads = args.numthreads
httpserver = args.server

confd = open(args.config, 'r')
yamlconfig = yaml.load(confd)
confd.close()

if args.results_dir:
    resdir = args.results_dir
elif "results_dir" in yamlconfig.keys():
    resdir = yamlconfig["results_dir"]
else:
    resdir = "."

# Check if result directory is writable
try:
    fd = open(resdir + "/.valid.tmp", "w")
    fd.write("temp")
    fd.close()
    os.unlink(resdir + "/.valid.tmp")
except IOError, e:
    sys.stderr.write("Failed to create file in " + resdir + " %s " % e + "\n")
    sys.exit(1)

if httpserver:
    for key in "server_ssl_ca", "server_ssl_cert", "server_ssl_key":
        if not key in yamlconfig.keys():
            sys.stderr.write("You should specify " + key + " in " + args.config + " to run in server mode!\n")
            sys.exit(1)
        elif not os.path.exists(yamlconfig[key]):
            sys.stderr.write(key + "file does not exist but required for server mode. Use valid_cert_creator.py to create it.\n")
            sys.exit(1)

if args.enable_tests:
    enable_tests = set(args.enable_tests)
else:
    enable_tests = None

if args.disable_tests:
    disable_tests = set(args.disable_tests)
else:
    disable_tests = set()

ec2_key = yamlconfig["ec2"]["ec2-key"]
ec2_secret_key = yamlconfig["ec2"]["ec2-secret-key"]

if args.debug:
    loglevel = logging.DEBUG
else:
    loglevel = logging.INFO

logging.basicConfig(level=loglevel, format='%(asctime)s %(levelname)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

if args.debug:
    logging.getLogger("paramiko").setLevel(logging.DEBUG)
else:
    logging.getLogger("paramiko").setLevel(logging.ERROR)

testing_stages = []
for m in sys.modules.keys():
    if m.startswith("valid.testing_modules.testcase"):
        try:
            test_name = m.split('.')[2]
            testcase = getattr(sys.modules[m], test_name)()
            if ((enable_tests and test_name in enable_tests) or (not enable_tests and not test_name in disable_tests)):
                for stage in testcase.stages:
                    if not (stage in testing_stages):
                        testing_stages.append(stage)
        except (AttributeError, TypeError, NameError, IndexError, ValueError, KeyError), e:
            logging.error("bad test, %s %s" % (m, e))
            logging.debug(traceback.format_exc())
            sys.exit(1)
testing_stages.sort()

if testing_stages == []:
    logging.error("no tests to run, exiting")
    sys.exit(1)

logging.info("Testing stages %s discovered" % str(testing_stages))


def add_data(data):
    with resultdic_lock:
        transaction_id = ''.join(random.choice(string.ascii_lowercase) for x in range(10))
        logging.info("Adding validation transaction " + transaction_id)
        resultdic[transaction_id] = {}
        count = 0
        for params in data:
            mandatory_fields = ["product", "arch", "region", "itype", "version", "ami"]
            minimal_set = set(mandatory_fields)
            exact_set = set(params.keys())
            if minimal_set.issubset(exact_set):
                # we have all required keys
                for field in mandatory_fields:
                    if type(params[field]) != str:
                        params[field] = str(params[field])
                if params["ami"] in resultdic[transaction_id].keys():
                    logging.error("Ami %s was already added for transaction %s!" % (params["ami"], transaction_id))
                    continue
                logging.debug("Got valid data line " + str(params))
                hwp_found = False
                for hwpdir in ["hwp", "/usr/share/valid/hwp"]:
                    try:
                        hwpfd = open(hwpdir + "/" + params["arch"] + ".yaml", "r")
                        hwp = yaml.load(hwpfd)
                        hwpfd.close()
                        resultdic[transaction_id][params["ami"]] = {"ninstances": len(hwp) * len(testing_stages), "instances": []}
                        for hwp_item in hwp:
                            params_copy = params.copy()
                            params_copy.update(hwp_item)
                            if not params_copy.has_key("bmap"):
                                params_copy["bmap"] = [{"name": "/dev/sda1", "size": "15", "delete_on_termination": True}]
                            params_copy["transaction_id"] = transaction_id
                            params_copy["iname"] = "Instance" + str(count) + "_" + transaction_id
                            params_copy["stages"] = testing_stages
                            logging.info("Adding " + params_copy["iname"] + ": " + hwp_item["ec2name"] + " instance for " + params_copy["ami"] + " testing in " + params_copy["region"])
                            mainq.put((0, "create", params_copy))
                            count += 1
                        hwp_found = True
                        break
                    except:
                        logging.debug(":" + traceback.format_exc())
                if not hwp_found:
                    logging.error("HWP for " + params["arch"] + " is not found, skipping dataline for " + params["ami"])
            else:
                # we something is missing
                logging.error("Got invalid data line: " + str(params))
        if count > 0:
            logging.info("Validation transaction " + transaction_id + " added")
            return transaction_id
        else:
            logging.info("No data added")
            return None


def remote_command(connection, command, timeout=5):
    status = connection.recv_exit_status(command + " >/dev/null 2>&1", timeout)
    if status != 0:
        raise ExpectFailed("Command " + command + " failed with " + str(status) + " status.")


class ServerThread(threading.Thread):
    def __init__(self, hostname="0.0.0.0", port=8080):
        threading.Thread.__init__(self)
        self.hostname = hostname
        self.port = port

    def run(self):
        server_class = BaseHTTPServer.HTTPServer
        httpd = server_class((self.hostname, self.port), HTTPHandler)
        httpd.socket = ssl.wrap_socket(httpd.socket,
                                       certfile=yamlconfig["server_ssl_cert"],
                                       keyfile=yamlconfig["server_ssl_key"],
                                       server_side=True,
                                       cert_reqs=ssl.CERT_REQUIRED,
                                       ca_certs=yamlconfig["server_ssl_ca"])
        httpd.serve_forever()


class HTTPHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_HEAD(s):
        s.send_response(200)
        s.send_header("Content-type", "text/html")
        s.end_headers()

    def do_GET(s):
        """Respond to a GET request."""
        try:
            path = urlparse.urlparse(s.path).path
            query = urlparse.parse_qs(urlparse.urlparse(s.path).query)
            logging.debug("GET request: " + s.path)
            if path[-1:] == "/":
                path = path[:-1]
            if path == "":
                # info page
                s.send_response(200)
                s.send_header("Content-type", "text/html")
                s.end_headers()
                s.wfile.write("<html><head><title>Validation status page</title></head>")
                s.wfile.write("<body>")
                s.wfile.write("<h1>Worker's queue</h1>")
                for q_item in mainq.queue:
                    s.wfile.write("<p>%s</p>" % str(q_item))
                s.wfile.write("<h1>Ongoing testing</h1>")
                with resultdic_lock:
                    for transaction_id in resultdic.keys():
                        s.wfile.write("<h2>Transaction <a href=/result?transaction_id=%s>%s</a></h2>" % (transaction_id, transaction_id))
                        for ami in resultdic[transaction_id].keys():
                            s.wfile.write("<h3>Ami %s </h3>" % ami)
                            s.wfile.write("<p>%s</p>" % str(resultdic[transaction_id][ami]))
                s.wfile.write("<h1>Finished testing</h1>")
                with resultdic_yaml_lock:
                    for transaction_id in resultdic_yaml.keys():
                        s.wfile.write("<h2>Transaction <a href=/result?transaction_id=%s>%s</a></h2>" % (transaction_id, transaction_id))
                s.wfile.write("</body></html>")
            elif path == "/result":
                # transaction result in yaml
                if not "transaction_id" in query.keys():
                    raise Exception("transaction_id parameter is not set")
                transaction_id = query["transaction_id"][0]
                with resultdic_yaml_lock:
                    if transaction_id in resultdic_yaml.keys():
                        s.send_response(200)
                        s.send_header("Content-type", "text/yaml")
                        s.end_headers()
                        s.wfile.write(resultdic_yaml[transaction_id])
                    else:
                        with resultdic_lock:
                            if transaction_id in resultdic.keys():
                                s.send_response(200)
                                s.send_header("Content-type", "text/yaml")
                                s.end_headers()
                                s.wfile.write(yaml.safe_dump({"result": "In progress"}))
                            else:
                                raise Exception("No such transaction")
            else:
                s.send_response(404)
                s.send_header("Content-type", "text/html")
                s.end_headers()
                s.wfile.write("<html><body>Bad url</body></html>")
        except Exception, e:
            s.send_response(400)
            s.send_header("Content-type", "text/plain")
            s.end_headers()
            s.wfile.write(e.message)
            logging.debug("HTTP Server:" + traceback.format_exc())

    def do_POST(s):
        """Respond to a POST request."""

        # Extract and print the contents of the POST
        length = int(s.headers['Content-Length'])
        try:
            post_data = urlparse.parse_qs(s.rfile.read(length).decode('utf-8'))
            if post_data and ("data" in post_data.keys()):
                data = yaml.load(post_data["data"][0])
                logging.debug("POST DATA:" + str(data))
                transaction_id = add_data(data)
                if not transaction_id:
                    raise Exception("Bad data")
                s.send_response(200)
                s.send_header("Content-type", "text/yaml")
                s.end_headers()
                s.wfile.write(yaml.safe_dump({"transaction_id": transaction_id}))
            else:
                raise Exception("Bad data")
        except Exception, e:
                s.send_response(400)
                s.send_header("Content-type", "text/plain")
                s.end_headers()
                s.wfile.write(e.message)


class ReportingThread(threading.Thread):
    def run(self):
        while True:
            time.sleep(random.randint(2, 10))
            self.report_results()
            with resultdic_lock:
                if resultdic == {} and not httpserver:
                    break

    def report_results(self):
        ''' Looking if we can report some transactions '''
        with resultdic_lock:
            ''' Dictionary is now locked '''
            for transaction_id in resultdic.keys():
                ''' Checking all transactions '''
                report_ready = True
                for ami in resultdic[transaction_id].keys():
                    ''' Checking all amis: they should be finished '''
                    if resultdic[transaction_id][ami]["ninstances"] != len(resultdic[transaction_id][ami]["instances"]):
                        ''' Still have some jobs running ...'''
                        logging.debug("ReportThread: " + transaction_id + ": " + ami + ":  waiting for " + str(resultdic[transaction_id][ami]["ninstances"]) + " results, got " + str(len(resultdic[transaction_id][ami]["instances"])))
                        report_ready = False
                if report_ready:
                    resfile = resdir + "/" + transaction_id + ".yaml"
                    result = []
                    data = resultdic[transaction_id]
                    for ami in data.keys():
                        result_item = {"ami": data[ami]["instances"][0]["ami"],
                                       "product": data[ami]["instances"][0]["product"],
                                       "version": data[ami]["instances"][0]["version"],
                                       "arch": data[ami]["instances"][0]["arch"],
                                       "region": data[ami]["instances"][0]["region"],
                                       "result": {}}
                        for instance in data[ami]["instances"]:
                            if not instance["instance_type"] in result_item["result"].keys():
                                result_item["result"][instance["instance_type"]] = instance["result"].copy()
                            else:
                                result_item["result"][instance["instance_type"]].update(instance["result"])
                        result.append(result_item)
                    result_yaml = yaml.safe_dump(result)
                    with resultdic_yaml_lock:
                        resultdic_yaml[transaction_id] = result_yaml
                    result_fd = open(resfile, "w")
                    result_fd.write(result_yaml)
                    result_fd.close()
                    logging.info("Transaction " + transaction_id + " finished. Result: " + resfile)
                    resultdic.pop(transaction_id)


class InstanceThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        while True:
            with resultdic_lock:
                if resultdic == {} and not httpserver:
                    break
            if mainq.empty():
                time.sleep(random.randint(2, 10))
                continue
            try:
                (ntry, action, params) = mainq.get()
                mainq.task_done()
            except:
                continue
            if ntry > maxtries:
                logging.error(self.getName() + ": " + action + ":" + str(params) + " failed after " + str(maxtries) + " tries")
                if action in ["create", "setup"]:
                    params["result"] = {action: "failure"}
                elif action == "test":
                    params["result"] = {params["stages"][0]: "failure"}
                if action != "terminate":
                    # we need to change expected value in resultdic
                    with resultdic_lock:
                        resultdic[params["transaction_id"]][params["ami"]]["ninstances"] -= (len(params["stages"]) - 1)
                    self.report_results(params)
                    if "id" in params.keys():
                        # Try to terminate the instance
                        mainq.put((0, "terminate", params.copy()))
                continue
            if action == "create":
                # create an instance
                logging.debug(self.getName() + ": picking up " + params["iname"])
                self.do_create(ntry, params)
            elif action == "setup":
                # setup instance for testing
                logging.debug(self.getName() + ": doing setup for " + params["iname"])
                res = self.do_setup(ntry, params)
            elif action == "test":
                # do some testing
                logging.debug(self.getName() + ": doing testing for " + params["iname"])
                res = self.do_testing(ntry, params)
            elif action == "terminate":
                # terminate instance
                logging.debug(self.getName() + ": terminating " + params["iname"])
                self.do_terminate(ntry, params)

    def report_results(self, params):
        with resultdic_lock:
            report_value = {"instance_type": params["ec2name"],
                            "ami": params["ami"],
                            "region": params["region"],
                            "arch": params["arch"],
                            "version": params["version"],
                            "product": params["product"],
                            "result": params["result"]}
            resultdic[params["transaction_id"]][params["ami"]]["instances"].append(report_value)

    def do_setup(self, ntry, params):
        '''
        Setup stage of testing
        '''
        try:
            logging.debug(self.getName() + ": trying to do setup for " + ", ntry " + str(ntry))
            (ssh_key_name, ssh_key) = yamlconfig["ssh"][params["region"]]
            logging.debug(self.getName() + ": ssh-key " + ssh_key)

            for user in ["ec2-user", "cloud-user"]:
                # If we're able to login with one of these users allow root ssh immediately
                try:
                    con = Connection(params["instance"], user, ssh_key)
                    Expect.ping_pong(con, "uname", "Linux")
                    Expect.ping_pong(con, "su -c 'cp -af /home/" + user + "/.ssh/authorized_keys /root/.ssh/authorized_keys; chown root.root /root/.ssh/authorized_keys; restorecon /root/.ssh/authorized_keys' && echo SUCCESS", "\r\nSUCCESS\r\n")
                except:
                    pass

            con = Connection(params["instance"], "root", ssh_key)
            remote_command(con, "[ `uname` = \"Linux\" ]")
            logging.debug(self.getName() + ": sleeping for " + str(settlewait) + " sec. to make sure instance has been settled.")
            time.sleep(settlewait)

            setup_scripts = []
            if "setup" in yamlconfig:
                # upload and execute a setup script as root in /tmp/
                logging.debug(self.getName() + ": executing global setup script: %s" % yamlconfig["setup"])
                local_script_path = os.path.expandvars(os.path.expanduser(yamlconfig["setup"]))
                setup_scripts.append(local_script_path)
            tf = tempfile.NamedTemporaryFile(delete=False)
            if "setup" in params.keys() and params["setup"]:
                if type(params["setup"]) is list:
                    params["setup"] = "\n".join(map(lambda x: str(x), params["setup"]))
                logging.debug(self.getName() + ": executing ami-specific setup script: %s" % params["setup"])
                tf.write(params["setup"])
                setup_scripts.append(tf.name)
            tf.close()
            for script in setup_scripts:
                remote_script_path = "/tmp/" + os.path.basename(script)
                con.sftp.put(script, remote_script_path)
                con.sftp.chmod(remote_script_path, 0700)
                remote_command(con, remote_script_path)
            os.unlink(tf.name)

            mainq.put((0, "test", params.copy()))
        except (socket.error, paramiko.SSHException, paramiko.PasswordRequiredException, paramiko.AuthenticationException, ExpectFailed) as e:
            logging.debug(self.getName() + ": got 'predictable' error during instance setup, %s, ntry: %i" % (e, ntry))
            logging.debug(self.getName() + ":" + traceback.format_exc())
            time.sleep(10)
            mainq.put((ntry + 1, "setup", params.copy()))
        except Exception, e:
            logging.error(self.getName() + ": got error during instance setup, %s %s, ntry: %i" % (type(e), e, ntry))
            logging.debug(self.getName() + ":" + traceback.format_exc())
            time.sleep(10)
            mainq.put((ntry + 1, "setup", params.copy()))

    def do_testing(self, ntry, params):
        '''
        Testing stage of testing
        '''
        try:
            stage = params["stages"][0]
            logging.debug(self.getName() + ": trying to do testing for " + params["iname"] + " " + stage + ", ntry " + str(ntry))

            result = {}

            (ssh_key_name, ssh_key) = yamlconfig["ssh"][params["region"]]
            logging.debug(self.getName() + ": ssh-key " + ssh_key)

            con = Connection(params["instance"], "root", ssh_key)
            Expect.ping_pong(con, "uname", "Linux")

            logging.info(self.getName() + ": doing testing for " + params["iname"] + " " + stage)

            for m in sorted(sys.modules.keys()):
                if m.startswith("valid.testing_modules.testcase"):
                    try:
                        test_name = m.split('.')[2]
                        testcase = getattr(sys.modules[m], test_name)()
                        if (stage in testcase.stages) and ((enable_tests and test_name in enable_tests) or (not enable_tests and not test_name in disable_tests)):
                            applicable_flag = True
                            if hasattr(testcase, "not_applicable"):
                                logging.debug(self.getName() + ": checking not_applicable list for " + test_name)
                                not_applicable = testcase.not_applicable
                                for key in not_applicable.keys():
                                    logging.debug(self.getName() + ": not_applicable key %s %s ... " % (key, not_applicable[key]))
                                    r = re.compile(not_applicable[key])
                                    if r.match(params[key]):
                                        logging.debug(self.getName() + ": got not_applicable for " + test_name + " %s = %s" % (key, params[key]))
                                        result[test_name] = {"result": "skipped", "comment": "not applicable for %s = %s" % (key, params[key])}
                                        applicable_flag = False
                                        break
                            if hasattr(testcase, "applicable"):
                                logging.debug(self.getName() + ": checking applicable list for " + test_name)
                                applicable = testcase.applicable
                                for key in applicable.keys():
                                    logging.debug(self.getName() + ": applicable key %s %s ... " % (key, applicable[key]))
                                    r = re.compile(applicable[key])
                                    if not r.match(params[key]):
                                        logging.debug(self.getName() + ": got 'not applicable' for " + test_name + " %s = %s" % (key, params[key]))
                                        result[test_name] = {"result": "skipped", "comment": "not applicable for %s = %s" % (key, params[key])}
                                        applicable_flag = False
                                        break
                            if not applicable_flag:
                                continue
                            logging.debug(self.getName() + ": doing test " + test_name + " for " + params["iname"] + " " + stage)
                            test_result = testcase.test(con, params)
                            logging.debug(self.getName() + ": " + params["iname"] + ": test " + test_name + " finised with " + str(test_result))
                            result[test_name] = test_result
                        else:
                            logging.debug(self.getName() + ": skipping test " + test_name + " for " + params["iname"] + " " + stage)
                    except (AttributeError, TypeError, NameError, IndexError, ValueError, KeyError), e:
                        logging.error(self.getName() + ": bad test, %s %s" % (m, e))
                        logging.debug(self.getName() + ":" + traceback.format_exc())
                        result[test_name] = "Failure"

            logging.info(self.getName() + ": done testing for " + params["iname"] + " " + stage)

            params_new = params.copy()
            if len(params["stages"]) > 1:
                params_new["stages"] = params["stages"][1:]
                mainq.put((0, "test", params_new))
            else:
                mainq.put((0, "terminate", params_new))
            logging.debug(self.getName() + ": done testing for " + params["iname"] + ", result: " + str(result))
            params["result"] = {params["stages"][0]: result}
            self.report_results(params)
        except (socket.error, paramiko.SSHException, paramiko.PasswordRequiredException, paramiko.AuthenticationException, ExpectFailed) as e:
            # Looks like we've failed to connect to the instance
            logging.debug(self.getName() + ": got 'predictable' error during instance testing, %s, ntry: %i" % (e, ntry))
            logging.debug(self.getName() + ":" + traceback.format_exc())
            time.sleep(10)
            mainq.put((ntry + 1, "test", params.copy()))
        except Exception, e:
            # Got unexpected error
            logging.error(self.getName() + ": got error during instance testing, %s %s, ntry: %i" % (type(e), e, ntry))
            logging.debug(self.getName() + ":" + traceback.format_exc())
            time.sleep(10)
            mainq.put((ntry + 1, "test", params.copy()))

    def do_create(self, ntry, params):
        '''
        Create stage of testing
        '''
        result = None
        logging.debug(self.getName() + ": trying to create instance  " + params["iname"] + ", ntry " + str(ntry))
        ntry += 1
        try:
            bmap = BlockDeviceMapping()
            for device in params["bmap"]:
                if not device.has_key("name"):
                    logging.debug(self.getName() + ": bad device " + str(device))
                    continue
                d = BlockDeviceType()
                if device.has_key("size"):
                    d.size = device["size"]
                if device.has_key("delete_on_termination"):
                    d.delete_on_termination = device["delete_on_termination"]
                if device.has_key("ephemeral_name"):
                    d.ephemeral_name = device["ephemeral_name"]
                bmap[device["name"]] = d

            reg = boto.ec2.get_region(params["region"], aws_access_key_id=ec2_key, aws_secret_access_key=ec2_secret_key)
            connection = reg.connect(aws_access_key_id=ec2_key, aws_secret_access_key=ec2_secret_key)
            (ssh_key_name, ssh_key) = yamlconfig["ssh"][params["region"]]
            # all handled params to be put in here
            boto_params = ["ami", "subnet_id"]
            for param in boto_params:
                params.setdefault(param)
            reservation = connection.run_instances(
                params["ami"],
                instance_type=params["ec2name"],
                key_name=ssh_key_name,
                block_device_map=bmap,
                subnet_id=params["subnet_id"]
            )
            myinstance = reservation.instances[0]
            count = 0
            # Sometimes EC2 failes to return something meaningful without small timeout between run_instances() and update()
            time.sleep(10)
            while myinstance.update() == 'pending' and count < maxwait / 5:
                # Waiting out instance to appear
                logging.debug(params["iname"] + "... waiting..." + str(count))
                time.sleep(5)
                count += 1
            connection.close()
            if myinstance.update() == 'running':
                # Instance appeared - scheduling 'setup' stage
                myinstance.add_tag("Name", params["ami"] + " validation")
                result = myinstance.__dict__
                logging.info(self.getName() + ": created instance " + params["iname"] + ", " + result["id"] + ":" + result["public_dns_name"])
                # packing creation results into params
                params["id"] = result["id"]
                params["instance"] = result.copy()
                mainq.put((0, "setup", params))
                return
            else:
                # maxwait seconds is enough to create an instance. If not -- EC2 failed.
                logging.error("Error during instance creation")

        except boto.exception.EC2ResponseError, e:
            # Boto errors should be handled according to their error Message - there are some well-known ones
            logging.debug(self.getName() + ": got boto error during instance creation: %s" % e)
            if str(e).find("<Code>InstanceLimitExceeded</Code>") != -1:
                # InstanceLimit is temporary problem
                logging.debug(self.getName() + ": got InstanceLimitExceeded - not increasing ntry")
                ntry -= 1
            elif str(e).find("<Code>InvalidParameterValue</Code>") != -1:
                # InvalidParameterValue is really bad
                logging.error(self.getName() + ": got boto error during instance creation: %s" % e)
                # Try to speed up whole testing process, it's hardly possible to recover from this error
                ntry += 9
            else:
                logging.debug(self.getName() + ":" + traceback.format_exc())
        except socket.error, e:
            # Network errors are usual, reschedult silently
            logging.debug(self.getName() + ": got socket error during instance creation: %s" % e)
            logging.debug(self.getName() + ":" + traceback.format_exc())
        except Exception, e:
            # Unexpected error happened
            logging.error(self.getName() + ": got error during instance creation: %s %s" % (type(e), e))
            logging.debug(self.getName() + ":" + traceback.format_exc())
        logging.debug(self.getName() + ": something went wrong with " + params["iname"] + " during creation, ntry: " + str(ntry) + ", rescheduling")
        # reschedule creation
        time.sleep(10)
        mainq.put((ntry, "create", params.copy()))

    def do_terminate(self, ntry, params):
        '''
        Terminate stage of testing
        '''
        try:
            logging.debug(self.getName() + ": trying to terminata instance  " + params["iname"] + ", ntry " + str(ntry))
            reg = boto.ec2.get_region(params["region"], aws_access_key_id=ec2_key, aws_secret_access_key=ec2_secret_key)
            connection = reg.connect(aws_access_key_id=ec2_key, aws_secret_access_key=ec2_secret_key)
            res = connection.terminate_instances([params["id"]])
            logging.info(self.getName() + ": terminated " + params["iname"])
            connection.close()
            return res
        except Exception, e:
            logging.error(self.getName() + ": got error during instance termination, %s %s" % (type(e), e))
            logging.debug(self.getName() + ":" + traceback.format_exc())
            mainq.put((ntry + 1, "terminate", params.copy()))


logging.getLogger('boto').setLevel(logging.CRITICAL)

# main queue for worker threads
mainq = Queue.Queue()

# resulting dictionary
resultdic = {}
resultdic_lock = threading.Lock()

# resulting dictionary
resultdic_yaml = {}
resultdic_yaml_lock = threading.Lock()

if args.data:
    try:
        datafd = open(args.data, "r")
        data = yaml.load(datafd)
        datafd.close()
    except Exception, e:
        logging.error("Failed to read data file %s wit error %s" % (args.data, e))
        sys.exit(1)
    add_data(data)
elif not httpserver:
    logging.error("You need to set --data or --server option!")
    sys.exit(1)

for i in range(num_worker_threads):
    i = InstanceThread()
    i.start()

r = ReportingThread()
r.start()

if httpserver:
    s = ServerThread()
    s.start()

try:
    threads_exist = True
    while threads_exist:
        threads_exist = False
        for thread in threading.enumerate():
            if thread is not threading.currentThread():
                threads_exist = True
                thread.join(2)
except KeyboardInterrupt:
    print "Got CTRL-C, exiting"
    for thread in threading.enumerate():
        if thread is not threading.currentThread() and thread.isAlive():
            try:
                thread._Thread__stop()
            except:
                print(str(thread.getName()) + ' could not be terminated')
    sys.exit(1)
