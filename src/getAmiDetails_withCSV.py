#!/usr/bin/python -tt

from pprint import pprint
from boto import ec2
from boto.ec2.blockdevicemapping import EBSBlockDeviceType
from boto.ec2.blockdevicemapping import BlockDeviceMapping
from bugzilla.bugzilla3 import Bugzilla36
import boto
import thread
import sys
import time
import argparse
import os
import csv
import rhui_lib
import ConfigParser
import subprocess
import tempfile


argparser = argparse.ArgumentParser(description='Remotely execute validation testcases')
argparser.add_argument('--skip-tests', metavar='<expr>', nargs="*",
                       help="space-separated expressions describing tests to skip")
argparser.add_argument('--no-bugzilla', action='store_const', const=True,
                       default=False, help='skip adding bug to the bugzilla')
argparser.add_argument('--list-tests', action='store_const', const=True,
                       default=False, help='display available test names and exit')
argparser.add_argument('--csv-file',
                       default="test1.csv", help='use supplied csv file')
argparser.add_argument('--config',
                       default="/etc/validation.cfg", help='use supplied config file')

args = argparser.parse_args()

CSVFILE = args.csv_file

config = ConfigParser.ConfigParser()
config.read(args.config)

if args.skip_tests:
        SKIPLIST = ",".join(args.skip_tests)
else:
        SKIPLIST = ""

if args.list_tests:
        os.system("./image_validation.sh --list-tests")
        sys.exit()

#us-west-2 has been used as SSHKEY_US_O and SSHKEY_NAME_US_O,  O stands for
#Oregon

SSHKEY_NAME_AP_S = config.get('SSH-Info', 'ssh-key-name_apsouth')
SSHKEY_AP_S = config.get('SSH-Info', 'ssh-key-path_apsouth')
SSHKEY_NAME_AP_N = config.get('SSH-Info', 'ssh-key-name_apnorth')
SSHKEY_AP_N = config.get('SSH-Info', 'ssh-key-path_apnorth')
SSHKEY_NAME_EU_W = config.get('SSH-Info', 'ssh-key-name_euwest')
SSHKEY_EU_W = config.get('SSH-Info', 'ssh-key-path_euwest')
SSHKEY_NAME_US_W = config.get('SSH-Info', 'ssh-key-name_uswest')
SSHKEY_US_W = config.get('SSH-Info', 'ssh-key-path_uswest')
SSHKEY_NAME_US_E = config.get('SSH-Info', 'ssh-key-name_useast')
SSHKEY_US_E = config.get('SSH-Info', 'ssh-key-path_useast')
SSHKEY_NAME_US_O = config.get('SSH-Info', 'ssh-key-name_uswest-oregon')
SSHKEY_US_O = config.get('SSH-Info', 'ssh-key-path_uswest-oregon')
SSHKEY_SA_E = config.get('SSH-Info', 'ssh-key-path_saeast')
SSHKEY_NAME_SA_E = config.get('SSH-Info', 'ssh-key-name_saeast')
SSHKEY_AP_S_SYDNEY = config.get('SSH-Info', 'ssh-key-path_apsouth-sydney')
SSHKEY_NAME_AP_S_SYDNEY = config.get('SSH-Info', 'ssh-key-name_apsouth-sydney')

BZUSER = config.get('Bugzilla-Info', 'bugzilla_usr')
BZPASS = config.get('Bugzilla-Info', 'bugzilla_pwd')

AWS_ACCESS_KEY_ID = config.get('EC2-Keys', 'ec2-key')
AWS_SECRET_ACCESS_KEY = config.get('EC2-Keys', 'ec2-secret-key')

CSV = config.get('Misc-Info', 'csv')
NOGIT = config.get('Misc-Info', 'git')
BASEDIR = config.get('Misc-Info', 'basedir')

val1 = {
    'SSHKEY_US_E':           SSHKEY_US_E,
    'SSHKEY_NAME_US_E':      SSHKEY_NAME_US_E,
    'SSHKEY_US_O':           SSHKEY_US_O,
    'SSHKEY_NAME_US_O':      SSHKEY_NAME_US_O,
    'SSHKEY_US_W':           SSHKEY_US_W,
    'SSHKEY_NAME_US_W':      SSHKEY_NAME_US_W,
    'SSHKEY_EU_W':           SSHKEY_EU_W,
    'SSHKEY_NAME_EU_W':      SSHKEY_NAME_EU_W,
    'SSHKEY_AP_N':           SSHKEY_AP_N,
    'SSHKEY_NAME_AP_N':      SSHKEY_NAME_AP_N,
    'SSHKEY_AP_S':           SSHKEY_AP_S,
    'SSHKEY_NAME_AP_S':      SSHKEY_NAME_AP_S,
    'SSHKEY_SA_E':           SSHKEY_SA_E,
    'SSHKEY_NAME_SA_E':      SSHKEY_NAME_SA_E,
    'SSHKEY_AP_S_SYDNEY':    SSHKEY_AP_S_SYDNEY,
    'SSHKEY_NAME_AP_S_SYDNEY': SSHKEY_NAME_AP_S_SYDNEY,
    'BZUSER':                BZUSER,
    'BZPASS':                BZPASS,
    'AWS_ACCESS_KEY_ID':     AWS_ACCESS_KEY_ID,
    'AWS_SECRET_ACCESS_KEY': AWS_SECRET_ACCESS_KEY,
    'CSV':                   CSV,
    'NOGIT':                 NOGIT,
    'BASEDIR':               BASEDIR,
}

for v in val1:
    if not val1[v]:
        print "The value ", v, "is missing in .cfg file."
        sys.exit()


def addBugzilla(BZ, AMI, RHEL, ARCH, REGION):
    mySummary = AMI + " " + RHEL + " " + ARCH + " " + REGION
    if BZ is None:
        print "**** No bugzilla # was passed, will open one here ****"
        bugzilla = Bugzilla36(url='https://bugzilla.redhat.com/xmlrpc.cgi', user=BZUSER, password=BZPASS)
        RHV = "RHEL" + RHEL
        BZ_Object = bugzilla.createbug(product="Cloud Image Validation",\
                    component="images", version=RHV, rep_platform=ARCH,\
                    summary=mySummary)
        BZ = str(BZ_Object.bug_id)
        print "Buzilla # = https://bugzilla.redhat.com/show_bug.cgi?id=" + BZ
        return BZ
    else:
        print "Already opened Buzilla # = https://bugzilla.redhat.com/show_bug.cgi?id=" + BZ
        return BZ


def getConnection(key, secret, region):
    """establish a connection with ec2"""
    reg = boto.ec2.get_region(region, aws_access_key_id=key, aws_secret_access_key=secret)
    return reg.connect(aws_access_key_id=key, aws_secret_access_key=secret)

#east# reservation = ec2conn.run_instances('ami-8c8a7de5', instance_type='t1.micro', key_name='cloude-key')
#block_device_map
#'/dev/sda=:20'


def startInstance(ec2connection, hardwareProfile, ARCH, RHEL, AMI, SSHKEYNAME):
    conn_region = ec2connection
    map = BlockDeviceMapping()
    t = EBSBlockDeviceType()
    t.size = '15'
    t.delete_on_termination = True

    #map = {'DeviceName':'/dev/sda','VolumeSize':'15'}
    map['/dev/sda1'] = t

    #blockDeviceMap = []
    #blockDeviceMap.append( {'DeviceName':'/dev/sda', 'Ebs':{'VolumeSize' : '100'} })

    reservation = conn_region.run_instances(AMI, instance_type=hardwareProfile,\
                                            key_name=SSHKEYNAME, block_device_map=map)

    myinstance = reservation.instances[0]

    time.sleep(5)
    while(not myinstance.update() == 'running'):
        time.sleep(5)
        print myinstance.update()

    instanceDetails = myinstance.__dict__
    pprint(instanceDetails)
    #region = instanceDetails['placement']
    #print 'region =' + region
    publicDNS = instanceDetails['public_dns_name']
    print 'public hostname = ' + publicDNS
    # check for console output here to make sure ssh is up
    return publicDNS


def executeValidScript(SSHKEY, publicDNS, hwp, BZ, ARCH, AMI, REGION, RHEL, SKIPLIST=""):
    filepath = BASEDIR
    serverpath = "/root/valid"
    commandPath = "/root/valid/src"
    ssh_command = "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i " + SSHKEY + " root@" + publicDNS
    scp_command = "scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i " + SSHKEY + " -r "
    if hwp["name"] == 't1.micro':
        os.system(ssh_command + " touch /root/noswap")
    if NOGIT == 'false':
        os.system(ssh_command + " mkdir -p /root/valid")
        command = scp_command + filepath + " root@" + publicDNS + ":" + serverpath
        print command + "\n"
        os.system(command)
    elif NOGIT == 'true':
        os.system(ssh_command + " yum -y install git")
        os.system(ssh_command + " git clone git://github.com/RedHatQE/valid.git")

    # COPY KERNEL if there
    serverpath = "/root/kernel"
    os.system(ssh_command + " mkdir -p /root/kernel")
    filepath = BASEDIR + "/kernel/" + ARCH + "/*"
    command = scp_command + filepath + " root@" + publicDNS + ":" + serverpath
    print command + "\n"
    os.system(command)

    command = commandPath + "/image_validation.sh --skip-list='" + SKIPLIST + "' --imageID=" + AMI +\
                            "_" + REGION + "_" + hwp["name"] + " --RHEL=" + RHEL + \
                            " --full-yum-suite=yes --skip-questions=yes" + \
                            " --memory=" + hwp["memory"] + " --public-dns=" + publicDNS + \
                            " --ami-id=" + AMI + " --arch-id=" + ARCH

    if args.no_bugzilla:
        command += " --no-bugzilla"
    else:
        command += " --bugzilla-username=" + BZUSER + " --bugzilla-password='" + BZPASS + "' --bugzilla-num=" + BZ

    log = tempfile.NamedTemporaryFile(delete=False)

    if not log:
        print "Failed to create temporary file!"
        return None
    else:
        print "Logging "+ publicDNS +" to " + log.name

    command_popen = ["/usr/bin/ssh", "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null", "-i", SSHKEY, "root@" + publicDNS, command]
    popen = subprocess.Popen(command_popen, stdout=log, stderr=log)
    print str(command_popen) + "\n"
    return popen


def printValues(hwp):
    print "+++++++"
    print AMI
    print REGION
    print SSHKEY
    print RHEL
    print hwp
    print "+++++++\n"

# Define hwp
m1Small = {"name": "m1.small", "memory": "1700000", "cpu": "1", "arch": "i386"}
m1Large = {"name": "m1.large", "memory": "7500000", "cpu": "2", "arch": "x86_64"}
m1Xlarge = {"name": "m1.xlarge", "memory": "15000000", "cpu": "4", "arch": "x86_64"}
t1Micro = {"name": "t1.micro", "memory": "600000", "cpu": "1", "arch": "both"}
m2Xlarge = {"name": "m2.xlarge", "memory": "17100000", "cpu": "2", "arch": "x86_64"}
m22Xlarge = {"name": "m2.2xlarge", "memory": "34200000", "cpu": "4", "arch": "x86_64"}
m24Xlarge = {"name": "m2.4xlarge", "memory": "68400000", "cpu": "8", "arch": "x86_64"}
c1Medium = {"name": "c1.medium", "memory": "1700000", "cpu": "2", "arch": "i386"}
c1Xlarge = {"name": "c1.xlarge", "memory": "7000000", "cpu": "8", "arch": "x86_64"}

#Use all hwp types for ec2 memory tests, other hwp tests
hwp_i386 = [c1Medium, t1Micro, m1Small]
#hwp_i386 = [c1Medium]
hwp_x86_64 = [m1Xlarge, t1Micro, m1Large, m2Xlarge, m22Xlarge, m24Xlarge, c1Xlarge]
#hwp_x86_64 = [m24Xlarge]

#Use just one hwp for os tests
#hwp_i386 = [c1Medium]
#hwp_x86_64 = [m1Xlarge,m22Xlarge]
BZ = None
if CSV == 'true':
    reader = csv.reader(open(CSVFILE, "rb"))
    fields = reader.next()
    ami = [(row[0], row[1], row[2], row[3], row[4], row[5]) for row in reader]
    for x in range(len(ami)):
        myRow = ami[x]
        print myRow
        ARCH = myRow[0]
        REGION = myRow[1]
        RHEL = myRow[4]
        BZ = myRow[3]
        if BZ == '??':
            BZ = None
        AMI = myRow[5]

        if REGION == "us-east-1":
            SSHKEY = SSHKEY_US_E
            SSHKEYNAME = SSHKEY_NAME_US_E
        elif REGION == "us-west-2":
            SSHKEY = SSHKEY_US_O
            SSHKEYNAME = SSHKEY_NAME_US_O
        elif REGION == "us-west-1":
            SSHKEY = SSHKEY_US_W
            SSHKEYNAME = SSHKEY_NAME_US_W
        elif REGION == "eu-west-1":
            SSHKEY = SSHKEY_EU_W
            SSHKEYNAME = SSHKEY_NAME_EU_W
        elif REGION == "ap-southeast-1":
            SSHKEY = SSHKEY_AP_S
            SSHKEYNAME = SSHKEY_NAME_AP_S
        elif REGION == "ap-northeast-1":
            SSHKEY = SSHKEY_AP_N
            SSHKEYNAME = SSHKEY_NAME_AP_N
        elif REGION == "sa-east-1":
            SSHKEY = SSHKEY_SA_E
            SSHKEYNAME = SSHKEY_NAME_SA_E
        elif REGION == "ap-southeast-2":
            SSHKEY = SSHKEY_AP_S_SYDNEY
            SSHKEYNAME = SSHKEY_NAME_AP_S_SYDNEY

if not args.no_bugzilla:
    BID = addBugzilla(BZ, AMI, RHEL, ARCH, REGION)
else:
    BID = None

publicDNS = []
if ARCH == 'i386':
    hwp_items = hwp_i386
elif ARCH == 'x86_64':
    hwp_items = hwp_x86_64
else:
    print "Arch type is neither i386 nor x86_64. Exiting..."
    exit(1)

for hwp in hwp_items:
    printValues(hwp)
    myConn = getConnection(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, REGION)
    this_hostname = startInstance(myConn, hwp["name"], ARCH, RHEL, AMI, SSHKEYNAME)
    map = {"hostname": this_hostname, "hwp": hwp}
    publicDNS.append(map)

#print "sleep for 130 seconds"
#time.sleep(130)
print "Trying to fetch a file to make sure the SSH works, before proceeding ahead."
f_path = "/tmp/network"
l_path = "/etc/init.d/network"
popens = []
for host in publicDNS:
    #keystat = rhui_lib.putfile(host["hostname"], SSHKEY, l_path, f_path)
    time.sleep(30)
    keystat = False
    if not keystat:
        popen = executeValidScript(SSHKEY, host["hostname"], \
                                   host["hwp"], BID, ARCH, AMI,\
                                   REGION, RHEL, SKIPLIST)
        if popen:
            popens.append({"hostname": host["hostname"],"popen": popen})   
        else:
            print "Failed to execute ssh to "+AMI 
    else:
        print "The Amazon node : " + \
              host["hostname"] + \
              " is not accessible, waited for 210 sec. \
              Skipping and proceeding with the next Profile"

print "Now waiting for all ssh processes to finish..."
while True:
    to_wait = False
    for i in range(len(popens)):
        if popens[i]["popen"]:
            res = popens[i]["popen"].poll()
            if res!=None:
                print str(popens[i]["hostname"])+" terminated with exit code "+str(res)
                popens[i]["popen"]=None
            else:
                to_wait = True
    if to_wait:
        time.sleep(5)
    else:
        break

