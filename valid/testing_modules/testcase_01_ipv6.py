from patchwork.expect import *

def testcase_01_ipv6(connection):
    try:
        Expect.ping_pong(connection, "grep NETWORKING_IPV6=no /etc/sysconfig/network && echo SUCCESS", "[^ ]SUCCESS")
        return "passed"
    except ExpectFailed:
        return "failed"
