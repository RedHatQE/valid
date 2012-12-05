#! /usr/bin/python -tt

import random
import Queue
import threading
import boto
import time
import logging
import argparse
import yaml
import sys

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
argparser.add_argument('--numthreads', type=int,
                       default=10, help='number of worker threads')

args = argparser.parse_args()
maxtries = args.maxtries

confd = open(args.config, 'r')
yamlconfig = yaml.load(confd)
confd.close()

ec2_key = yamlconfig["ec2"]["ec2-key"]
ec2_secret_key = yamlconfig["ec2"]["ec2-secret-key"]

(ssh_key_name, ssh_key) = yamlconfig["ssh"][region]

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
        self.reg = boto.ec2.get_region(region, aws_access_key_id=ec2_key, aws_secret_access_key=ec2_secret_key)
        self.connection = self.reg.connect(aws_access_key_id=ec2_key, aws_secret_access_key=ec2_secret_key)

    def run(self):
        while not mainq.empty():
            (ntry, action, params) = mainq.get()
            if action == "create":
                (iname, itype) = params
                if ntry > maxtries:
                    logging.error(self.getName() + ": " + action + ":" + str(params) + "failed after " + str(maxtries) + " tries")
                    resultq.put({"iname": iname, "itype": itype, "result": "failure"})
                    mainq.task_done()
                    continue
                logging.info(self.getName() + ": picking up " + iname)
                details = self.create_instance(iname, itype)
                mainq.task_done()
                if details:
                    logging.info(self.getName() + ": created instance, " + details["id"] + ":" + details["public_dns_name"])
                    mainq.put((0, "test", (iname, itype, details["id"], details["public_dns_name"], [])))
                else:
                    logging.error(self.getName() + ": something went wrong with " + iname + " during creation, ntry: " + str(ntry) + ", rescheduling")
                    # reschedule creation
                    time.sleep(5)
                    mainq.put((ntry + 1, "create", (iname, itype)))
            elif action == "test":
                (iname, itype, instanceid, dns, testlist) = params
                if ntry > maxtries:
                    logging.error(self.getName() + ": " + action + ":" + str(params) + "failed after " + str(maxtries) + " tries")
                    resultq.put({"iname": iname, "itype": itype, "result": "failure"})
                    mainq.task_done()
                    continue
                # do some testing
                logging.info(self.getName() + ": doing testing for " + iname)
                res = self.do_testing(dns, itype, instanceid, iname, ntry)
                mainq.task_done()
                if res:
                    logging.info(self.getName() + ": done testing for " + iname + ", result: " + str(res))
                    resultsq.put({"iname": iname, "itype": itype, "result": res})
                else:
                    logging.error(self.getName() + ": something went wrong with " + iname + " during testing, ntry: " + str(ntry) + ", rescheduled")
            elif action == "terminate":
                (instanceid) = params
                logging.debug(self.getName() + ": terminating " + iname)
                terminate_res = self.connection.terminate_instances([instanceid])
                mainq.task_done()

    def do_testing(self, dns, itype, instanceid, iname, ntry):
        try:
            result = {}
            logging.info(self.getName() + ": doing testing for " + dns)
            instance = {}
            instance["private_hostname"] = dns
            instance["public_hostname"] = dns
            instance["type"] = itype
            logging.debug(self.getName() + ": ssh-key " + ssh_key)
            con = Connection(instance, "root", ssh_key)
            Expect.ping_pong(con, "uname", "Linux")
            for m in sys.modules.keys():
                if m.startswith("valid.testing_modules.testcase"):
                    try:
                        test_name = m.split('.')[2]
                        test_result = getattr(sys.modules[m], test_name)(con)
                        logging.info(self.getName() + ": test " + test_name + " finised with " + str(test_result))
                        result[test_name] = test_result
                    except AttributeError, e:
                        logging.error(self.getName() + ": bad test, %s" % e)
                        result[test_name] = "Failure"
            mainq.put((0, "terminate", (instanceid)))
            return result
        except Exception, e:
            logging.error(self.getName() + ": got error during instance testing, %s" % e)
            time.sleep(5)
            mainq.put((ntry + 1, "test", (iname, itype, instanceid, dns, [])))
            return None

    def create_instance(self, iname, itype):
        try:
            reservation = self.connection.run_instances(ami, instance_type=itype, key_name=ssh_key_name, block_device_map=bmap)
            myinstance = reservation.instances[0]
            count = 0
            while myinstance.update() == 'pending' and count < 20:
                logging.debug(iname + "... waiting..." + str(count))
                time.sleep(5)
            if count == 20:
                # 100 seconds is enough to create an instance. If not -- EC2 failed.
                logging.error("Timeout during instance creation, %s" % e)
                return None
            else:
                return myinstance.__dict__
        except Exception, e:
            logging.error(self.getName() + ": got error during instance creation, %s" % e)
            return None


# main queue for worker threads
mainq = Queue.Queue()
resultsq = Queue.Queue()

try:
    fd = open(args.data, "r")
    yamlconfig = yaml.load(confd)
    confd.close()
except Exception, e:
    logging.debug("Failed to read data file %s wit error %s" % (args.data, e))
    sys.exit(1)

mainq.put((0, "create", ("Instance1", "t1.micro")))
mainq.put((0, "create", ("Instance2", "m1.small")))

num_worker_threads = args.numthreads

for i in range(num_worker_threads):
    i = InstanceThread()
    i.start()

for thread in threading.enumerate():
    if thread is not threading.currentThread():
        thread.join()

result = {}
while not resultsq.empty():
    result_item = resultsq.get()
    result[result_item["itype"]] = result_item["result"]
    resultsq.task_done()

logging.info("RESULT: " + str(result))
