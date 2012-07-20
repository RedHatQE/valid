from config import ConfiguredObjectParser

class Node(object):
    attribute_names = ('id',
            'region_name',
            'image_id',
            'security_groups',
            'instance_type',
            'key_name',
            'role',
            'architecture',
            'public_dns_name',
            'private_dns_name')
    def __init__(self, **kvargs):
        for attribute_name in self.attribute_names:
            try:
                setattr(self, attribute_name, kvargs[attribute_name])
            except KeyError:
                setattr(self, attribute_name, None)

    def __repr__(self):
        return "Node(" + ", ".join(["%s=%r" % (name, getattr(self, name)) for name in self.attribute_names]) + ")"

    __str__ = __repr__


if __name__ == '__main__':
    from ConfigParser import ConfigParser
    import StringIO
    cfg = ConfigParser()
    cfg.add_section("RHUA")
    cfg.set("RHUA", "region_name", "us-east-1")
    cfg.set("RHUA", "image_id", "ami-12345")
    cfg.set("RHUA", "instance_type", "m1.small")
    cfg_fd = StringIO.StringIO()
    cfg.write(cfg_fd)
    cfg_str = cfg_fd.getvalue()
    print cfg_str
    cp = ConfiguredObjectParser(Node)
    cp.readfp(StringIO.StringIO(cfg_str))
    for node in cp.objects():
        print node
    cw = ConfiguredObjectParser(Node)
    cw.add(node)
    import sys
    cw.write(sys.stdout)
