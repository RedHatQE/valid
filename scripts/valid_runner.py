#! /usr/bin/python -tt

import Queue
import threading
import boto
import time
import logging
import argparse
import yaml
import sys
import sets
import paramiko
import random
import string
import BaseHTTPServer

from patchwork.connection import Connection
from patchwork.expect import *
from boto import ec2
from boto.ec2.blockdevicemapping import EBSBlockDeviceType
from boto.ec2.blockdevicemapping import BlockDeviceMapping

import valid

def csv(value):
    return map(str, value.split(","))

argparser = argparse.ArgumentParser(description='Create CloudFormation stack and run the testing')
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
                       default=".", help='put resulting yaml files to specified location')
argparser.add_argument('--server', action='store_const', const=True,
                       default=False, help='run HTTP server')
argparser.add_argument('--settlewait', type=int,
                       default=30, help='wait for instance to settle before testing')

args = argparser.parse_args()
maxtries = args.maxtries
maxwait = args.maxwait
settlewait = args.settlewait
resdir = args.results_dir
num_worker_threads = args.numthreads
httpserver = args.server

if args.enable_tests:
    enable_tests = set(args.enable_tests)
else:
    enable_tests = None

if args.disable_tests:
    disable_tests = set(args.disable_tests)
else:
    disable_tests = set()

confd = open(args.config, 'r')
yamlconfig = yaml.load(confd)
confd.close()

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

bmap = BlockDeviceMapping()
t = EBSBlockDeviceType()
t.size = '15'
t.delete_on_termination = True
bmap['/dev/sda1'] = t

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
        except (AttributeError, TypeError, NameError), e:
            logging.error(self.getName() + ": bad test, %s %s" % (m, e))
            sys.exit(1)
testing_stages.sort()

logging.info("Testing stages %s discovered" % str(testing_stages))

def add_data(data):
    with resultdic_lock:
        transaction_id = ''.join(random.choice(string.ascii_lowercase) for x in range(10))
        logging.info("Adding validation transaction " + transaction_id)
        resultdic[transaction_id] = {}
        count = 0
        for params in data:
            minimal_set = set(["product", "arch", "region", "itype", "version", "ami"])
            exact_set = set(params.keys())
            if minimal_set.issubset(exact_set):
                # we have all required keys
                logging.debug("Got valid data line " + str(params))
                hwp_found = False
                for hwpdir in ["hwp", "/usr/share/valid/hwp"]:
                    try:
                        hwpfd = open(hwpdir + "/" + params["arch"] + ".yaml", "r")
                        hwp = yaml.load(hwpfd)
                        hwpfd.close()
                        resultdic[transaction_id][params["ami"]] = {"ninstances": len(hwp) * len(testing_stages), "instances": []}
                        for hwp_item in hwp:
                            params["transaction_id"] = transaction_id
                            params["hwp"] = hwp_item
                            params["iname"] = "Instance" + str(count) + "_" + transaction_id
                            params["stages"] = testing_stages
                            logging.info("Adding " + params["iname"] + ": " + hwp_item["name"] + " instance for " + params["ami"] + " testing in " + params["region"])
                            mainq.put((0, "create", params.copy()))
                            count += 1
                        hwp_found = True
                        break
                    except:
                        pass
                if not hwp_found:
                    logging.error("HWP for " + params["arch"] + " is not found, skipping dataline for " + params["ami"])
            else:
                # we something is missing
                logging.error("Got invalid data line: " + str(params))
        logging.info("Validation transaction " + transaction_id + " added")


class ServerThread(threading.Thread):
    def __init__(self, hostname="0.0.0.0", port=8080):
        threading.Thread.__init__(self)
        self.hostname = hostname
        self.port = port

    def run(self):
        server_class = BaseHTTPServer.HTTPServer
        httpd = server_class((self.hostname, self.port), HTTPHandler)
        httpd.serve_forever()


class HTTPHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_HEAD(s):
        s.send_response(200)
        s.send_header("Content-type", "text/html")
        s.end_headers()
    def do_GET(s):
        """Respond to a GET request."""
        s.send_response(200)
        s.send_header("Content-type", "text/html")
        s.end_headers()
        s.wfile.write("<html><head><title>Validation status page</title></head>")
        s.wfile.write("<body>")
        # If someone went to "http://something.somewhere.net/foo/bar/",
        # then s.path equals "/foo/bar/".
        # s.wfile.write("<p>You accessed path: %s</p>" % s.path)
        try:
            s.wfile.write("<h1>Queue</h1>")
            for q_item in mainq.queue:
                s.wfile.write("<p>%s</p>" % str(q_item))
            s.wfile.write("<h1>Result</h1>")
            with resultdic_lock:
                for transaction_id in resultdic.keys():
                    s.wfile.write("<h2>Transaction %s </h2>" % transaction_id)
                    for ami in resultdic[transaction_id].keys():
                        s.wfile.write("<h3>Ami %s </h3>" % ami)
                        s.wfile.write("<p>%s</p>" % str(resultdic[transaction_id][ami]))
        except:
            pass
        s.wfile.write("</body></html>")


class ReportingThread(threading.Thread):
    def run(self):
        while True:
            time.sleep(random.randint(2,10))
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
                        logging.debug("ReportThread: " + ami + ":  waiting for " + str(resultdic[transaction_id][ami]["ninstances"]) + " results, got " + str(len(resultdic[transaction_id][ami]["instances"])))
                        report_ready = False
                if report_ready:
                    resfile = resdir + "/" + transaction_id + ".yaml"
                    result_fd = open(resfile, "w")
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
                    result_fd.write(yaml.safe_dump(result))
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
                time.sleep(random.randint(2,10))
                continue
            try:
                (ntry, action, params) = mainq.get()
                mainq.task_done()
            except:
                continue
            if ntry > maxtries:
                logging.error(self.getName() + ": " + action + ":" + str(params) + " failed after " + str(maxtries) + " tries")
                if action in ["create", "terminate"]:
                    params["result"] = {action: "failure"}
                else:
                    params["result"] = {params["stages"][0]: "failure"}
                # we need to change expected value in resultdic
                with resultdic_lock:
                    resultdic[params["transaction_id"]][params["ami"]]["ninstances"] -= (len(params["stages"]) - 1)
                self.report_results(params)
                continue
            if action == "create":
                # (iname, hwp, product, arch, region, itype, version, ami) = params
                logging.debug(self.getName() + ": picking up " + params["iname"])
                self.create_instance(ntry, params)
            elif action == "test":
                # (iname, hwp, product, arch, region, itype, version, ami, id, public_dns_name) = params
                # do some testing
                logging.debug(self.getName() + ": doing testing for " + params["iname"])
                res = self.do_testing(ntry, params)
            elif action == "terminate":
                # (iname, hwp, product, arch, region, itype, version, ami, id, public_dns_name, result) = params
                # terminate instance
                logging.debug(self.getName() + ": terminating " + params["iname"])
                self.terminate_instance(ntry, params)

    def report_results(self, params):
        with resultdic_lock:
            report_value = {"instance_type": params["hwp"]["name"],
                            "ami": params["ami"],
                            "region": params["region"],
                            "arch": params["hwp"]["arch"],
                            "version": params["version"],
                            "product": params["product"],
                            "result": params["result"]}
            resultdic[params["transaction_id"]][params["ami"]]["instances"].append(report_value)

    def do_testing(self, ntry, params):
        try:
            result = {}
            logging.debug(self.getName() + ": doing testing for " + params["public_dns_name"])

            instance = {}
            instance["private_hostname"] = params["public_dns_name"]
            instance["public_hostname"] = params["public_dns_name"]
            instance["type"] = params["hwp"]["name"]

            stage = params["stages"][0]

            (ssh_key_name, ssh_key) = yamlconfig["ssh"][params["region"]]
            logging.debug(self.getName() + ": ssh-key " + ssh_key)

            for user in ["ec2-user", "cloud-user"]:
                # If we're able to login with one of these users allow root ssh immediately
                try:
                    con = Connection(instance, user, ssh_key)
                    Expect.ping_pong(con, "uname", "Linux")
                    Expect.ping_pong(con, "su -c 'cp -af /home/" + user + "/.ssh/authorized_keys /root/.ssh/authorized_keys; chown root.root /root/.ssh/authorized_keys; restorecon /root/.ssh/authorized_keys'; echo SUCCESS", "\r\nSUCCESS\r\n")
                except:
                    pass

            con = Connection(instance, "root", ssh_key)
            Expect.ping_pong(con, "uname", "Linux")
            logging.debug(self.getName() + ": sleeping for " + str(settlewait) + " sec. to make sure instance has been settled.")
            time.sleep(settlewait)

            logging.info(self.getName() + ": doing testing for " + params["iname"] + " " + stage)

            for m in sorted(sys.modules.keys()):
                if m.startswith("valid.testing_modules.testcase"):
                    try:
                        test_name = m.split('.')[2]
                        testcase = getattr(sys.modules[m], test_name)()
                        if (stage in testcase.stages) and ((enable_tests and test_name in enable_tests) or (not enable_tests and not test_name in disable_tests)):
                            logging.debug(self.getName() + ": doing test " + test_name + " for " + params["iname"] + " " + stage)
                            test_result = testcase.test(con, params)
                            logging.debug(self.getName() + ": " +params["iname"] + ": test " + test_name + " finised with " + str(test_result))
                            result[test_name] = test_result
                        else:
                            logging.debug(self.getName() + ": skipping test " + test_name + " for " + params["iname"] + " " +stage)
                    except (AttributeError, TypeError, NameError), e:
                        logging.error(self.getName() + ": bad test, %s %s" % (m, e))
                        result[test_name] = "Failure"

            logging.info(self.getName() + ": done testing for " + params["iname"] + " " + stage)

            params_new = params.copy()
            if len(params["stages"])>1:
                params_new["stages"] = params["stages"][1:]
                mainq.put((0, "test", params_new))
            else:
                mainq.put((0, "terminate", params_new))
            logging.debug(self.getName() + ": done testing for " + params["iname"] + ", result: " + str(result))
            params["result"] = {params["stages"][0]: result}
            self.report_results(params)
        except (socket.error, paramiko.PasswordRequiredException, ExpectFailed) as e:
            logging.debug(self.getName() + ": got 'predictable' error during instance testing, %s, ntry: %i" % (e, ntry))
            time.sleep(10)
            mainq.put((ntry + 1, "test", params))
        except Exception, e:
            logging.error(self.getName() + ": got error during instance testing, %s %s, ntry: %i" % (type(e), e, ntry))
            time.sleep(10)
            mainq.put((ntry + 1, "test", params))

    def create_instance(self, ntry, params):
        result = None
        try:
            reg = boto.ec2.get_region(params["region"], aws_access_key_id=ec2_key, aws_secret_access_key=ec2_secret_key)
            connection = reg.connect(aws_access_key_id=ec2_key, aws_secret_access_key=ec2_secret_key)
            (ssh_key_name, ssh_key) = yamlconfig["ssh"][params["region"]]
            reservation = connection.run_instances(params["ami"], instance_type=params["hwp"]["name"], key_name=ssh_key_name, block_device_map=bmap)
            myinstance = reservation.instances[0]
            count = 0
            while myinstance.update() == 'pending' and count < maxwait / 5:
                logging.debug(params["iname"] + "... waiting..." + str(count))
                time.sleep(5)
                count += 1
            connection.close()
            if myinstance.update() == 'running':
                myinstance.add_tag("Name", params["ami"] + " validation")
                result =  myinstance.__dict__
                logging.info(self.getName() + ": created instance " + params["iname"] + ", " + result["id"] + ":" + result["public_dns_name"])
                # packing creation results into params
                params["id"] = result["id"]
                params["public_dns_name"] = result["public_dns_name"]
                mainq.put((0, "test", params))
                return
            else:
                # maxwait seconds is enough to create an instance. If not -- EC2 failed.
                logging.error("Error during instance creation, %s" % e)
        except (socket.error, boto.exception.EC2ResponseError), e:
            logging.debug(self.getName() + ": got socket error during instance creation, %s" % e)
            if e.message.find("<Code>InstanceLimitExceeded</Code>") != -1:
                # InstanceLimit is temporary problem
                ntry -= 1
        except Exception, e:
            logging.error(self.getName() + ": got error during instance creation, %s %s" % (type(e), e))
        logging.debug(self.getName() + ": something went wrong with " + params["iname"] + " during creation, ntry: " + str(ntry) + ", rescheduling")
        # reschedule creation
        time.sleep(10)
        mainq.put((ntry + 1, "create", params))

    def terminate_instance(self, ntry, params):
        try:
            reg = boto.ec2.get_region(params["region"], aws_access_key_id=ec2_key, aws_secret_access_key=ec2_secret_key)
            connection = reg.connect(aws_access_key_id=ec2_key, aws_secret_access_key=ec2_secret_key)
            res = connection.terminate_instances([params["id"]])
            logging.info(self.getName() + ": terminated " + params["iname"])
            logging.debug(self.getName() + ": terminated " + params["id"] + " with result: " + str(res))
            connection.close()
            return res
        except Exception, e:
            logging.error(self.getName() + ": got error during instance termination, %s %s" % (type(e), e))
            mainq.put((ntry + 1, "terminate", params))


logging.getLogger('boto').setLevel(logging.CRITICAL)

# main queue for worker threads
mainq = Queue.Queue()

# resulting dictionary
resultdic = {}
resultdic_lock = threading.Lock()

if args.data:
    try:
        datafd = open(args.data, "r")
        data = yaml.load(datafd)
        datafd.close()
    except Exception, e:
        logging.error("Failed to read data file %s wit error %s" % (args.data, e))
        sys.exit(1)
elif not httpserver:
    logging.error("You need to set --data or --server option!")
    sys.exit(1)

add_data(data)

for i in range(num_worker_threads):
    i = InstanceThread()
    i.start()

r = ReportingThread()
r.start()

if httpserver:
    s = ServerThread()
    s.start()

for thread in threading.enumerate():
    if thread is not threading.currentThread():
        thread.join()
