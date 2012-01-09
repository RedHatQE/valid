#!/usr/bin/python -tt
#AUTHOR : KEDAR BIDARKAR
#Script for shutting down all the instances in a particular REGION and
#Deletion of volumes which are in the AVAILABLE state.

import boto.ec2
import boto.ec2.instance
import re
import pprint

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

region_name = None
region_name = chek_null(region_name, "\nPlease specify the Region name to connect : ")
connect_ec2 = boto.ec2.connect_to_region(region_name)

print "Terminating all the instances for the region", region_name
reservation_ids = connect_ec2.get_all_instances()
print reservation_ids
for res1 in reservation_ids:
    inst=res1.instances
    for v in inst:
        mat=re.match(r'([\w.]+):([\w.-]+)', str(v))
        ins_id=mat.group(2)
        print "Shutting down the instance :", mat.group(2)
        connect_ec2.terminate_instances(ins_id)

print "Deletion of volumes which are in the state AVAILABLE only"
vol_ids = connect_ec2.get_all_volumes()
for vol in vol_ids:
    if vol.status == 'available':
        connect_ec2.delete_volume(vol.id)
    else:
        print "The following disks have not been deleted as it's current status is : ", vol.status
        print vol.id
