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

from patchwork.connection import Connection
from patchwork.expect import *
from boto import ec2
from boto.ec2.blockdevicemapping import EBSBlockDeviceType
from boto.ec2.blockdevicemapping import BlockDeviceMapping

import valid

argparser = argparse.ArgumentParser(description='Create CloudFormation stack and run the testing')
argparser.add_argument('--data', required=True,
                       help='data file for validation')
argparser.add_argument('--config',
                       default="/etc/validation.yaml", help='use supplied yaml config file')
argparser.add_argument('--debug', action='store_const', const=True,
                       default=False, help='debug mode')
argparser.add_argument('--maxtries', type=int,
                       default=100, help='maximum number of tries')
argparser.add_argument('--maxwait', type=int,
                       default=300, help='maximum wait time for instance creation')
argparser.add_argument('--numthreads', type=int,
                       default=10, help='number of worker threads')

args = argparser.parse_args()
maxtries = args.maxtries
maxwait = args.maxwait

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


class InstanceThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        while not mainq.empty():
            (ntry, action, params) = mainq.get()
            if ntry > maxtries:
                logging.error(self.getName() + ": " + action + ":" + str(params) + " failed after " + str(maxtries) + " tries")
                params["result"] = "failure"
                resultsq.put(params)
                mainq.task_done()
                continue
            if action == "create":
                # (iname, hwp, product, arch, region, itype, version, ami) = params
                logging.debug(self.getName() + ": picking up " + params["iname"])
                details = self.create_instance(params)
                mainq.task_done()
                if details:
                    logging.info(self.getName() + ": created instance " + params["iname"] + ", " + details["id"] + ":" + details["public_dns_name"])
                    # packing creation results into params
                    params["id"] = details["id"]
                    params["public_dns_name"] = details["public_dns_name"]
                    mainq.put((0, "test", params))
                else:
                    logging.debug(self.getName() + ": something went wrong with " + params["iname"] + " during creation, ntry: " + str(ntry) + ", rescheduling")
                    # reschedule creation
                    time.sleep(5)
                    mainq.put((ntry + 1, "create", params))
            elif action == "test":
                # (iname, hwp, product, arch, region, itype, version, ami, id, public_dns_name) = params
                # do some testing
                logging.debug(self.getName() + ": doing testing for " + params["iname"])
                res = self.do_testing(ntry, params)
                mainq.task_done()
                if res:
                    logging.info(self.getName() + ": done testing for " + params["iname"])
                    logging.debug(self.getName() + ": done testing for " + params["iname"] + ", result: " + str(res))
                    params["result"] = res
                    resultsq.put(params)
                else:
                    logging.debug(self.getName() + ": something went wrong with " + params["iname"] + " during testing, ntry: " + str(ntry) + ", rescheduled")
            elif action == "terminate":
                # (iname, hwp, product, arch, region, itype, version, ami, id, public_dns_name, result) = params
                # terminate instance
                logging.debug(self.getName() + ": terminating " + params["iname"])
                if not self.terminate_instance(params):
                    mainq.put((ntry + 1, "terminate", params))
                mainq.task_done()

    def do_testing(self, ntry, params):
        try:
            result = {}
            logging.debug(self.getName() + ": doing testing for " + params["public_dns_name"])

            instance = {}
            instance["private_hostname"] = params["public_dns_name"]
            instance["public_hostname"] = params["public_dns_name"]
            instance["type"] = params["hwp"]["name"]

            (ssh_key_name, ssh_key) = yamlconfig["ssh"][params["region"]]
            logging.debug(self.getName() + ": ssh-key " + ssh_key)

            con = Connection(instance, "root", ssh_key)

            Expect.ping_pong(con, "uname", "Linux")
            for m in sys.modules.keys():
                if m.startswith("valid.testing_modules.testcase"):
                    try:
                        test_name = m.split('.')[2]
                        testcase = getattr(sys.modules[m], test_name)()
                        test_result = testcase.test(con)
                        logging.debug(self.getName() + params["iname"] + ": test " + test_name + " finised with " + str(test_result))
                        result[test_name] = test_result
                    except AttributeError, e:
                        logging.error(self.getName() + ": bad test, %s" % e)
                        result[test_name] = "Failure"
            mainq.put((0, "terminate", params))
            return result
        except (socket.error, paramiko.PasswordRequiredException) as e:
            logging.debug(self.getName() + ": got socket error during instance creation, %s" % e)
            time.sleep(5)
            mainq.put((ntry + 1, "test", params))
            return None
        except Exception, e:
            logging.error(self.getName() + ": got error during instance testing, %s %s" % (type(e), e))
            time.sleep(5)
            mainq.put((ntry + 1, "test", params))
            return None

    def create_instance(self, params):
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
            connection.close()
            if count == maxwait / 5:
                # maxwait seconds is enough to create an instance. If not -- EC2 failed.
                logging.error("Timeout during instance creation, %s" % e)
                return None
            else:
                return myinstance.__dict__
        except socket.error, e:
            logging.debug(self.getName() + ": got socket error during instance creation, %s" % e)
            return None
        except Exception, e:
            logging.error(self.getName() + ": got error during instance creation, %s %s" % (type(e), e))
            return None

    def terminate_instance(self, params):
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
            return None


# main queue for worker threads
mainq = Queue.Queue()
resultsq = Queue.Queue()

try:
    datafd = open(args.data, "r")
    data = yaml.load(datafd)
    datafd.close()
except Exception, e:
    logging.error("Failed to read data file %s wit error %s" % (args.data, e))
    sys.exit(1)

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
                for hwp_item in hwp:
                    params["hwp"] = hwp_item
                    params["iname"] = "Instance" + str(count)
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

num_worker_threads = args.numthreads

for i in range(num_worker_threads):
    i = InstanceThread()
    i.start()

for thread in threading.enumerate():
    if thread is not threading.currentThread():
        thread.join()

outres = {}
while not resultsq.empty():
    result_item = resultsq.get()
    ami = result_item["ami"]
    itype = result_item["hwp"]["name"]

    if not ami in outres.keys():
        outres[ami] = {}

    if itype in outres[ami].keys():
        logging.error("Second result for " + ami + "," + itype + ", ignoring")

    outres[ami][itype] = result_item["result"]
    resultsq.task_done()

logging.info("RESULT: " + str(outres))
