#! /usr/bin/python

import random
import sys

memory = 10000000
if len(sys.argv)>1:
    memory = int(sys.argv[1])

while True:
    l = []
    for i in range(memory):
        l.append(random.randint(0,memory))
    l.sort()
