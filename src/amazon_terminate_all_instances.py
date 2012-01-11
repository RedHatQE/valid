#!/usr/bin/python -tt
################################################################################
# Authors: Kedar Bidarkar <kbidarka@redhat.com>
# ################################################################################

#Please refer the accounts page (http://aws.amazon.com/account/ under security credentials) 
#of amazon site for your access details (Access Keys :- access_key_id and secret_access_key). 

#Please configure boto.cfg under /etc/  as below
#[Credentials]
#aws_access_key_id = xxxx 
#aws_secret_access_key = xxxx


#Script for shutting down all the instances in a particular REGION and
#Deletion of volumes which are in the AVAILABLE state.

import boto.ec2
import time


region_name = None
user_ans1 = None

def chek_null(var, prompt):
    while True:
        if var:
            return var
            break
        else:
            var = raw_input(prompt)
            continue

print "Fetching the regions :\n"
list_regions = boto.ec2.regions()
print "Following are the regions available :\n"
for j in list_regions:
    print j.name

region_name = chek_null(region_name, "\nPlease specify the Region name to connect : ")
connect_ec2 = boto.ec2.connect_to_region(region_name)


def delete_ebs_volumes():
    vol_ids = connect_ec2.get_all_volumes()
    for vol in vol_ids:
        if vol.status == 'available':
            connect_ec2.delete_volume(vol.id)
            print "\nDeleted the EBS volume with id", vol.id, "successfully"
        else:
            print "\nThe below disk has not been deleted as it's current status is : ", vol.status
            print vol.id

def terminate_all_instances():
    reservation_ids = connect_ec2.get_all_instances()
    for res1 in reservation_ids:
        inst=res1.instances
        for v in inst:
            print "\nShutting down the instance :", v.id
            connect_ec2.terminate_instances(str(v.id))
            v.update()
            print "\nShutdown successful, Instance status:", v.state


print "\nTerminating all the instances for the region", region_name
terminate_all_instances()

print "\n\nWill delete all EBS volumes for the above selected REGION, which are in the state AVAILABLE only"
user_ans1 = chek_null(user_ans1, "\nDo you wish to proceed (y/n) :")
if user_ans1 == 'y':
    print "\nSleeping for 90 secs, for the ami's to get terminated."
    time.sleep(90)
    delete_ebs_volumes()
else:
    print "\nYou have canceled, None of the EBS volumes deleted\n"
