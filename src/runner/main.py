from twisted.internet import reactor

def write(nodes):
    reactor.stop()
    from config import ConfiguredObjectParser
    from node import Node
    node_writer = ConfiguredObjectParser(Node)
    for node in nodes:
        node_writer.add(node)
    import sys
    node_writer.write(sys.stdout)


if __name__ == '__main__':
    from instance import NodeInstantiator
    from twisted.internet.defer import Deferred
    from twisted.python import log
    import sys
    log.startLogging(sys.stderr, setStdout=False)
    deferred = Deferred()
    deferred.addCallback(write)
    NodeInstantiator(deferred)
    reactor.run()
