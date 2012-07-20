from boto.ec2 import get_region
from twisted.internet import threads, defer
from twisted.python import log
from config import ConfiguredObjectParser
from node import Node
from aws import Ec2

class InstanceFactory(object):
    ec2 = None
    node = None
    connection = None
    instance = None
    region = None

    def __init__(self, deferred, ec2, node, cmd_retries = 1000, cmd_sleep =
            1.0):
        self.deferred = deferred
        self.ec2 = ec2
        self.node = node
        self.cmd_retries = cmd_retries
        self.cmd_sleep = cmd_sleep
        log.msg("requested instance of: %r" % node, logLevel=log.logging.DEBUG)
        region_deferred = threads.deferToThread(\
                get_region,
                node.region_name,
                aws_access_key_id = self.ec2.key_id,
                aws_secret_access_key = self.ec2.key)
        region_deferred.addCallback(self.__process_region)

    def __process_region(self, region):
        log.msg("got %r" % region, logLevel=log.logging.DEBUG)
        connect_deferred = threads.deferToThread(\
                region.connect,
                aws_access_key_id = self.ec2.key_id,
                aws_secret_access_key=self.ec2.key)
        connect_deferred.addCallback(self.__process_connection)

    def __process_connection(self, connection):
        log.msg("got %r" % connection, logLevel=log.logging.DEBUG)
        self.connection = connection
        instance_deferred = threads.deferToThread(\
                self.connection.run_instances,
                image_id = self.node.image_id,
                key_name = self.node.key_name,
                instance_type = self.node.instance_type,
                security_groups = [self.node.security_groups])
        instance_deferred.addCallback(self.__process_instance)

    def __process_instance(self, reservation):
        log.msg("got %r" % reservation, logLevel=log.logging.DEBUG)
        self.instance = reservation.instances[0]
        self.instance.factory = self
        ensure_running_deferred = threads.deferToThread(self.__check_running)
        ensure_running_deferred.addCallback(self.__process_running)

    def __process_running(self, running):
        if running:
            log.msg("got a running %r" % self.instance, logLevel=log.logging.DEBUG)
            self.deferred.callback(self.instance)
        else:
            log.error("got a not running %r" % self.instance)
            self.deferred.errback(RunTimeError("Too many retries booting %r" % self.node))

    def __check_running(self):
        import time
        retries = self.cmd_retries
        while self.instance.update() != 'running' and retries > 0:
            log.msg("%r pending" % self.instance, logLevel=log.logging.DEBUG)
            retries -= 1
            time.sleep(self.cmd_sleep)
        if retries <= 0:
            return False
        return True

class InstanceToNodeFactory(object):
    def __init__(self, deferred, instance):
        from node import Node
        self.deferred = deferred
        self.instance = instance
        log.msg("requested node from %r" % self.instance, logLevel=log.logging.DEBUG)
        d = threads.deferToThread(self.__process_attributes)
        d.addCallback(self.__process_node)

    def __process_attributes(self):
        try:
            node = self.instance.factory.node
            log.msg("updating %r based on %r" % (node, self.instance), logLevel=log.logging.DEBUG)
        except AttributeError:
            node = Node()
        node.factory = self
        for attr_name in node.attribute_names:
            if hasattr(self.instance, attr_name):
                setattr(node, attr_name, getattr(self.instance, attr_name))
                log.msg("set node:%s.%s: %r" % (node.id, attr_name, getattr(node, attr_name)), logLevel=log.logging.DEBUG)
        return node

    def __process_node(self, node):
        self.node = node
        log.msg("processed %r" % self.node, logLevel=log.logging.DEBUG)
        self.deferred.callback(self.node)

class NodeInstantiator(object):
    aws_cfg_path = 'aws.cfg'
    nodes_cfg_path = 'nodes.cfg'
    nodes = []
    instances = []

    def __init__(self, deferred):
        self.deferred = deferred
        acp = ConfiguredObjectParser(Ec2)
        acp.read(self.aws_cfg_path)
        for ec2 in acp.objects():
            pass # :D
        ncp = ConfiguredObjectParser(Node)
        ncp.read(self.nodes_cfg_path)
        self._pending = 0
        for node in ncp.objects():
            self._pending += 1
            d = defer.Deferred()
            d.addCallback(self.__process_instance)
            InstanceFactory(d, ec2, node)

    def __process_instance(self, instance):
        d = defer.Deferred()
        d.addCallback(self.__add_node)
        InstanceToNodeFactory(d, instance)

    def __add_node(self, node):
        self.nodes.append(node)
        self._pending -= 1
        if self._pending <= 0:
            self.deferred.callback(self.nodes)



