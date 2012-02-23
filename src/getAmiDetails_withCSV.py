#!/usr/bin/python -tt

from pprint import pprint
from boto import ec2
import boto, thread
import sys, time, argparse, os
import csv
#from boto.ec2.blockdevicemapping import BlockDeviceMapping
from boto.ec2.blockdevicemapping import EBSBlockDeviceType, BlockDeviceMapping
from bugzilla.bugzilla3 import Bugzilla36
import rhui_lib
import ConfigParser


argparser = argparse.ArgumentParser(description=\
		'Remotely execute validation testcases')
argparser.add_argument('--skip-tests', metavar='<expr>',nargs="*",
		help="space-separated expressions describing tests to skip")
argparser.add_argument('--list-tests', action='store_const', const=True,
		default=False, help='display available test names and exit')
argparser.add_argument('--staging', action='store_const', const=True,
		default=False, help='Test in staging env; implies no bugzilla reports; requires "/etc/validation-staging.cfg"')
args = argparser.parse_args()

if args.skip_tests:
	SKIPLIST=",".join(args.skip_tests)
else:
	SKIPLIST=""

if args.list_tests:
	os.system("./image_validation.sh --list-tests")
	sys.exit()

config = ConfigParser.ConfigParser()
if args.staging:
	STAGING=True
	config.read('/etc/validation-staging.cfg')
else:
	STAGING=False
	config.read('/etc/validation.cfg')

#us-west-2 has been used as SSHKEY_US_O and SSHKEY_NAME_US_O,  O stands for
#Oregon

SSHKEY_NAME_AP_S = config.get('SSH-Info', 'ssh-key-name_apsouth')
SSHKEY_AP_S  = config.get('SSH-Info', 'ssh-key-path_apsouth')
SSHKEY_NAME_AP_N = config.get('SSH-Info', 'ssh-key-name_apnorth')
SSHKEY_AP_N  = config.get('SSH-Info', 'ssh-key-path_apnorth')
SSHKEY_NAME_EU_W = config.get('SSH-Info', 'ssh-key-name_euwest')
SSHKEY_EU_W  = config.get('SSH-Info', 'ssh-key-path_euwest')
SSHKEY_NAME_US_W = config.get('SSH-Info', 'ssh-key-name_uswest')
SSHKEY_US_W  = config.get('SSH-Info', 'ssh-key-path_uswest')
SSHKEY_NAME_US_E = config.get('SSH-Info', 'ssh-key-name_useast')
SSHKEY_US_E = config.get('SSH-Info', 'ssh-key-path_useast')
SSHKEY_NAME_US_O = config.get('SSH-Info', 'ssh-key-name_uswest-oregon')
SSHKEY_US_O = config.get('SSH-Info', 'ssh-key-path_uswest-oregon')
SSHKEY_SA_E = config.get('SSH-Info', 'ssh-key-path_saeast')
SSHKEY_NAME_SA_E = config.get('SSH-Info', 'ssh-key-name_saeast')

if not STAGING:
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
    'AWS_ACCESS_KEY_ID':     AWS_ACCESS_KEY_ID,
    'AWS_SECRET_ACCESS_KEY': AWS_SECRET_ACCESS_KEY,
    'CSV':                   CSV,
    'NOGIT':                 NOGIT,
    'BASEDIR':               BASEDIR,
}

if not STAGING:
	# not required in staging env
	val1['BZUSER'] = BZUSER
	val1['BZPASS'] = BZPASS


for v in val1:
    if not val1[v]:
        print "The value ", v, "is missing in .cfg file."
        sys.exit()

CSVFILE = "test1.csv"

def addBugzilla(BZ, AMI, RHEL, ARCH, REGION):
    if STAGING:
        # bugzilla not supported in staging env
        return
    if BZ is None:
        print "**** No bugzilla # was passed, will open one here ****"
        bugzilla=Bugzilla36(url='https://bugzilla.redhat.com/xmlrpc.cgi',user=BZUSER,password=BZPASS)
        mySummary=AMI+" "+RHEL+" "+ARCH+" "+REGION
        RHV = "RHEL"+RHEL
        BZ_Object=bugzilla.createbug(product="Cloud Image Validation",component="images",version=RHV,rep_platform=ARCH,summary=mySummary)
        BZ = str(BZ_Object.bug_id)
        print "Buzilla # = https://bugzilla.redhat.com/show_bug.cgi?id="+ BZ
        return BZ
    else:
        mySummary=AMI+" "+RHEL+" "+ARCH+" "+REGION
        print "Already opened Buzilla # = https://bugzilla.redhat.com/show_bug.cgi?id="+ BZ
        return BZ

    file = open('/tmp/bugzilla',"a")
    file.write("\n")
    file.write(BZ)
    file.write("\t")
    file.write(mySummary)
    file.close()
    os.system("cp "+BASEDIR+"/nohup.out "+BASEDIR+"/nohup_"+AMI+".out ; cat /dev/null > "+BASEDIR+"/nohup.out")

if CSV == 'false':
    BID = addBugzilla(BZ, AMI, RHEL, ARCH, REGION)


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
    #map = {'DeviceName':'/dev/sda','VolumeSize':'15'}
    map['/dev/sda1'] = t

    #blockDeviceMap = []
    #blockDeviceMap.append( {'DeviceName':'/dev/sda', 'Ebs':{'VolumeSize' : '100'} })

    if STAGING:
        subnet_id = VPC_SUBNET_ID[conn_region.region.name]
    else:
        subnet_id = None

    if ARCH == 'i386' and RHEL == '6.1':
        reservation = conn_region.run_instances(AMI, instance_type=hardwareProfile, key_name=SSHKEYNAME, block_device_map=map, subnet_id=subnet_id)
    elif ARCH == 'x86_64' and RHEL == '6.1':
        reservation = conn_region.run_instances(AMI, instance_type=hardwareProfile, key_name=SSHKEYNAME, block_device_map=map, subnet_id=subnet_id)
    elif ARCH == 'i386':
        reservation = conn_region.run_instances(AMI, instance_type=hardwareProfile, key_name=SSHKEYNAME, block_device_map=map, subnet_id=subnet_id)
    elif ARCH == 'x86_64':
        reservation = conn_region.run_instances(AMI, instance_type=hardwareProfile, key_name=SSHKEYNAME, block_device_map=map, subnet_id=subnet_id)
    else:
        print "arch type is neither i386 or x86_64.. will exit"
        exit(1)

    myinstance = reservation.instances[0]

    time.sleep(5)
    while(not myinstance.update() == 'running'):
        time.sleep(5)
        print myinstance.update()

    instanceDetails = myinstance.__dict__
    pprint(instanceDetails)
    #region = instanceDetails['placement']
    #print 'region =' + region

    if STAGING:
        # well, not particularly proud of this line ;)
        publicDNS = instanceDetails['private_ip_address']
        # note that staging is in VPC, therefore the ip address is required
    else:
        publicDNS = instanceDetails['public_dns_name']
    print 'public hostname = ' + publicDNS

    # check for console output here to make sure ssh is up
    return publicDNS

# retry a command up to limit times
def retryCommand(command='true', retries=20, sleeptime=3):
    print ">> %s" % command
    while not os.system(command) == 0 and retries > 0:
        print ".. %s" % retries
        retries -= 1
        time.sleep(sleeptime)
    if retries <= 0:
        raise RuntimeError('Too many retries: %s' % command)
    print "<<"

def sshCommand(host, key, command='true', retries=20, sleeptime=3, nohup=False):
    if nohup:
        cmd = "nohup ssh -n -f -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o User=root -i %s %s '%s' " % (key, host, command)
    else:
        cmd = "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o User=root -i %s %s '%s' " % (key, host, command)
    retryCommand(cmd, retries, sleeptime)

def scpCommand(host, key, local, remote, retries=20, sleeptime=3):
    cmd = "scp -r -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o User=root -i %s %s %s:%s" % (key, local, host, remote)
    retryCommand(cmd, retries, sleeptime)

def executeValidScript(SSHKEY, publicDNS, hwp, BZ, ARCH, AMI, REGION, RHEL, SKIPLIST=""):
    filepath = BASEDIR
    serverpath = "/root/valid"
    commandPath = "/root/valid/src"

    sshCommand(publicDNS, SSHKEY)
    if NOGIT == 'false':
        sshCommand(publicDNS, SSHKEY, 'mkdir -p /root/valid')
        if hwp["name"] == 't1.micro':
            sshCommand(publicDNS, SSHKEY, 'touch /root/noswap')
        scpCommand(publicDNS, SSHKEY, filepath, serverpath)
    elif NOGIT == 'true':
        if hwp["name"] == 't1.micro':
             sshCommand(publicDNS, SSHKEY, 'touch /root/noswap')
        sshCommand(publicDNS, SSHKEY, 'yum -y install git')
        sshCommand(publicDNS, SSHKEY, 'git clone git://github.com/RedHatQE/valid.git')


    # COPY KERNEL if there
    #serverpath = "/root/kernel"
    #os.system("ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i "+SSHKEY+ " root@"+publicDNS+" mkdir -p /root/kernel")
    #if ARCH == 'i386':
    #    filepath = BASEDIR+"/kernel/i386/*"
    #    print "scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i "+SSHKEY+ " -r " + filepath + " root@"+publicDNS+":"+serverpath+"\n"
    #    os.system("scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i "+SSHKEY+ " -r " + filepath + " root@"+publicDNS+":"+serverpath)
    #if ARCH == 'x86_64':
    #    filepath = BASEDIR+"/kernel/x86_64/*"
    #    print "scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i "+SSHKEY+ " -r " + filepath + " root@"+publicDNS+":"+serverpath+"\n"
    #    os.system("scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i "+SSHKEY+ " -r " + filepath + " root@"+publicDNS+":"+serverpath)


    if STAGING:
        # implies no bugzilla
        command = commandPath+"/image_validation.sh --skip-list='"+SKIPLIST+"' --imageID="+AMI+"_"+REGION+"_"+hwp["name"]+" --RHEL="+RHEL+" --full-yum-suite=yes --skip-questions=yes --memory="+hwp["memory"]+" --public-dns="+publicDNS+" --ami-id="+AMI+" --arch-id="+ARCH + " --no-bugzilla --staging"
    else:
        command = commandPath+"/image_validation.sh --skip-list='"+SKIPLIST+"' --imageID="+AMI+"_"+REGION+"_"+hwp["name"]+" --RHEL="+RHEL+" --full-yum-suite=yes --skip-questions=yes --bugzilla-username="+BZUSER+" --bugzilla-password='"+BZPASS+"' --bugzilla-num="+BZ+ " --memory="+hwp["memory"]+" --public-dns="+publicDNS+" --ami-id="+AMI+" --arch-id="+ARCH

    sshCommand(publicDNS, SSHKEY, command=command, nohup=True)


def printValues(hwp):
    print "+++++++"
    print AMI
    print REGION
    print SSHKEY
    print RHEL
    print hwp
    print "+++++++\n"

def myfunction(string, sleeptime,lock,SSHKEY,publicDNS):
        #entering critical section
        lock.acquire()
        print string," Now Sleeping after Lock acquired for ",sleeptime
        time.sleep(sleeptime)

        print string," Now releasing lock and then sleeping again"
        lock.release()

        #exiting critical section
        time.sleep(sleeptime) # why?

# Define hwp
m1Small = {"name":"m1.small","memory":"1700000","cpu":"1","arch":"i386"}
m1Large = {"name":"m1.large","memory":"7500000","cpu":"2","arch":"x86_64"}
m1Xlarge = {"name":"m1.xlarge","memory":"15000000","cpu":"4","arch":"x86_64"}
t1Micro = {"name":"t1.micro","memory":"600000","cpu":"1","arch":"both"}
m2Xlarge = {"name":"m2.xlarge","memory":"17100000","cpu":"2","arch":"x86_64"}
m22Xlarge = {"name":"m2.2xlarge","memory":"34200000","cpu":"4","arch":"x86_64"}
m24Xlarge = {"name":"m2.4xlarge","memory":"68400000","cpu":"8","arch":"x86_64"}
c1Medium = {"name":"c1.medium","memory":"1700000","cpu":"2","arch":"i386"}
c1Xlarge = {"name":"c1.xlarge","memory":"7000000","cpu":"8","arch":"x86_64"}

# Define VPC subnets per region
VPC_SUBNET_ID = {
        'us-east-1':'subnet-87d15cee'
}


#Use all hwp types for ec2 memory tests, other hwp tests
# STAGING isn't supported for t1.micro types...
if STAGING:
    hwp_i386 = [c1Medium,  m1Small ]
else:
    hwp_i386 = [c1Medium, t1Micro , m1Small ]
#hwp_i386 = [c1Medium]
if STAGING:
    hwp_x86_64 = [m1Xlarge, m1Large , m2Xlarge, m22Xlarge, m24Xlarge , c1Xlarge]
else:
    hwp_x86_64 = [m1Xlarge, t1Micro , m1Large , m2Xlarge, m22Xlarge, m24Xlarge , c1Xlarge]
#hwp_x86_64 = [m24Xlarge]

#Use just one hwp for os tests
#hwp_i386 = [c1Medium]
#hwp_x86_64 = [m1Xlarge,m22Xlarge]
if CSV == 'true':
    reader = csv.reader(open(CSVFILE,"rb"))
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

        BID = addBugzilla(BZ, AMI, RHEL, ARCH, REGION)

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

        if STAGING and not REGION == 'us-east-1':
           print "region %s not supported; currently staging supported onlyin us-east-1" % REGION
           sys.exit()

        publicDNS = []
        if ARCH == 'i386':
            for hwp in hwp_i386:
                printValues(hwp)
                myConn = getConnection(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, REGION)
                this_hostname = startInstance(myConn, hwp["name"], ARCH, RHEL, AMI, SSHKEYNAME)
                map = {"hostname":this_hostname,"hwp":hwp}
                publicDNS.append(map)
        elif ARCH == 'x86_64':
            for hwp in hwp_x86_64:
                printValues(hwp)
                myConn = getConnection(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, REGION)
                this_hostname = startInstance(myConn, hwp["name"], ARCH, RHEL, AMI, SSHKEYNAME)
                map = {"hostname":this_hostname,"hwp":hwp}
                publicDNS.append(map)

        lock = thread.allocate_lock()
#        print "sleep for 130 seconds"
#        time.sleep(130)
        if not STAGING:
            print "Trying to fetch a file to make sure the SSH works, before proceeding ahead."
            f_path = "/tmp/network"
            l_path = "/etc/init.d/network"
            for host in publicDNS:
                keystat = rhui_lib.putfile(host["hostname"], SSHKEY, l_path, f_path)
                if not keystat:
                    executeValidScript(SSHKEY, host["hostname"], host["hwp"], BID, ARCH, AMI, REGION, RHEL, SKIPLIST)
                else:
                    print "The Amazon node : "+host["hostname"]+" is not accessible, waited for 210 sec. Skipping and proceeding with the next Profile"
        else:
            for host in publicDNS:
                executeValidScript(SSHKEY, host["hostname"],host["hwp"], BID, ARCH, AMI, REGION, RHEL, SKIPLIST)
else:
    publicDNS = []
    if ARCH == 'i386':
        for hwp in hwp_i386:
            printValues(hwp)
            myConn = getConnection(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, REGION)
            this_hostname = startInstance(myConn, hwp["name"], ARCH, RHEL, AMI, SSHKEYNAME)
            map = {"hostname":this_hostname,"hwp":hwp}
            publicDNS.append(map)
    elif ARCH == 'x86_64':
        for hwp in hwp_x86_64:
            printValues(hwp)
            myConn = getConnection(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, REGION)
            this_hostname = startInstance(myConn, hwp["name"], ARCH, RHEL, AMI, SSHKEYNAME)
            map = {"hostname":this_hostname,"hwp":hwp}
            publicDNS.append(map)

    lock = thread.allocate_lock()
#    print "sleep for 130 seconds"
#    time.sleep(130)
    if not STAGING:
        print "Trying to fetch a file and make sure the SSH works, before proceeding ahead."
        f_path = "/tmp/network"
        l_path = "/etc/init.d/network"
        for host in publicDNS:
            keystat = rhui_lib.putfile(host["hostname"], SSHKEY, l_path, f_path)
            if not keystat:
                executeValidScript(SSHKEY, host["hostname"],host["hwp"], BID, ARCH, AMI, REGION, RHEL, SKIPLIST)
            else:
                print "The Amazon node : "+host["hostname"]+" is not accessible, waited for 210 sec. Skipping and proceeding with the next Profile"
    else:
        for host in publicDNS:
            executeValidScript(SSHKEY, host["hostname"],host["hwp"], BID, ARCH, AMI, REGION, RHEL, SKIPLIST)
