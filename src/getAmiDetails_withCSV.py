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

config = ConfigParser.ConfigParser()
config.read('/etc/validation.cfg')

argparser = argparse.ArgumentParser(description=\
		'Remotely execute validation testcases')
argparser.add_argument('--skip-tests', metavar='<expr>',nargs="*",
		help="space-separated expressions describing tests to skip")
argparser.add_argument('--list-tests', action='store_const', const=True,
		default=False, help='display available test names and exit')
args = argparser.parse_args()

if args.skip_tests:
	SKIPLIST=",".join(args.skip_tests)
else:
	SKIPLIST=""

if args.list_tests:
	os.system("./image_validation.sh --list-tests")
	sys.exit()

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

CSVFILE = "test1.csv"

def addBugzilla(BZ, AMI, RHEL, ARCH, REGION):
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

    if ARCH == 'i386' and RHEL == '6.1':
        reservation = conn_region.run_instances(AMI, instance_type=hardwareProfile, key_name=SSHKEYNAME, block_device_map=map )
    elif ARCH == 'x86_64' and RHEL == '6.1':
        reservation = conn_region.run_instances(AMI, instance_type=hardwareProfile, key_name=SSHKEYNAME, block_device_map=map )
    elif ARCH == 'i386':
        reservation = conn_region.run_instances(AMI, instance_type=hardwareProfile, key_name=SSHKEYNAME, block_device_map=map )
    elif ARCH == 'x86_64':
        reservation = conn_region.run_instances(AMI, instance_type=hardwareProfile, key_name=SSHKEYNAME, block_device_map=map)
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
    publicDNS = instanceDetails['public_dns_name']
    print 'public hostname = ' + publicDNS
    # check for console output here to make sure ssh is up
    return publicDNS

def executeValidScript(SSHKEY, publicDNS, hwp, BZ, ARCH, AMI, REGION, RHEL, SKIPLIST=""):
    filepath = BASEDIR
    serverpath = "/root/valid"
    commandPath = "/root/valid/src"

    if NOGIT == 'false':
        if hwp["name"] == 't1.micro':
            os.system("ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i "+SSHKEY+ " root@"+publicDNS+" mkdir -p /root/valid")
            os.system("ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i "+SSHKEY+ " root@"+publicDNS+" touch /root/noswap")
        else:
            os.system("ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i "+SSHKEY+ " root@"+publicDNS+" mkdir -p /root/valid")
        print "scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i "+SSHKEY+ " -r " + filepath + " root@"+publicDNS+":"+serverpath+"\n"
        os.system("scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i "+SSHKEY+ " -r " + filepath + " root@"+publicDNS+":"+serverpath)
    elif NOGIT == 'true':
        if hwp["name"] == 't1.micro':
            os.system("ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i "+SSHKEY+ " root@"+publicDNS+" touch /root/noswap")
        os.system("ssh  -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i "+SSHKEY+ " root@"+publicDNS+" yum -y install git")
        os.system("ssh  -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i "+SSHKEY+ " root@"+publicDNS+" git clone git://github.com/RedHatQE/valid.git")


    # COPY KERNEL if there
    serverpath = "/root/kernel"
    os.system("ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i "+SSHKEY+ " root@"+publicDNS+" mkdir -p /root/kernel")
    if ARCH == 'i386':
        filepath = BASEDIR+"/kernel/i386/*"
        print "scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i "+SSHKEY+ " -r " + filepath + " root@"+publicDNS+":"+serverpath+"\n"
        os.system("scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i "+SSHKEY+ " -r " + filepath + " root@"+publicDNS+":"+serverpath)
    if ARCH == 'x86_64':
        filepath = BASEDIR+"/kernel/x86_64/*"
        print "scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i "+SSHKEY+ " -r " + filepath + " root@"+publicDNS+":"+serverpath+"\n"
        os.system("scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i "+SSHKEY+ " -r " + filepath + " root@"+publicDNS+":"+serverpath)



#    command = commandPath+"/image_validation.sh --imageID="+IGNORE+AMI+"_"+REGION+"_"+hwp["name"]+" --RHEL="+RHEL+" --full-yum-suite=yes --skip-questions=yes --bugzilla-username="+BZUSER+" --bugzilla-password="+BZPASS+" --bugzilla-num="+BZ+ " --memory="+hwp["memory"]
    command = commandPath+"/image_validation.sh --skip-list='"+SKIPLIST+"' --imageID="+AMI+"_"+REGION+"_"+hwp["name"]+" --RHEL="+RHEL+" --full-yum-suite=yes --skip-questions=yes --bugzilla-username="+BZUSER+" --bugzilla-password='"+BZPASS+"' --bugzilla-num="+BZ+ " --memory="+hwp["memory"]+" --public-dns="+publicDNS+" --ami-id="+AMI+" --arch-id="+ARCH

    print "nohup ssh -n -f -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i "+SSHKEY+ " root@"+publicDNS+" "+command
    print ""
    os.system("nohup ssh -n -f -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i "+SSHKEY+ " root@"+publicDNS+" "+command)


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


#Use all hwp types for ec2 memory tests, other hwp tests
hwp_i386 = [c1Medium, t1Micro , m1Small ]
#hwp_i386 = [c1Medium]
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
    print "Trying to fetch a file and make sure the SSH works, before proceeding ahead."
    f_path = "/tmp/network"
    l_path = "/etc/init.d/network"
    for host in publicDNS:
        keystat = rhui_lib.putfile(host["hostname"], SSHKEY, l_path, f_path)
        if not keystat:
            executeValidScript(SSHKEY, host["hostname"],host["hwp"], BID, ARCH, AMI, REGION, RHEL, SKIPLIST)
        else:
	        print "The Amazon node : "+host["hostname"]+" is not accessible, waited for 210 sec. Skipping and proceeding with the next Profile"
