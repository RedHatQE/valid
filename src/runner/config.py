class ConfiguredObjectParser(object):
    """reads object attributes from a ini-like config made up of just one kind
    of sections"""
    def __init__(self, object_type):
        """object_type: type to instantiate for each section read. The instance
        is assumed to have a attribute_names attribute. The very
        first attribute is considered the section name"""
        from ConfigParser import ConfigParser
        self.config = ConfigParser(allow_no_value=True)
        self.object_type = object_type

    def add(self, other):
        section_name = str(getattr(other, other.attribute_names[0]))
        self.config.add_section(section_name)
        for attribute_name in other.attribute_names[1:]:
            self.config.set(section_name, attribute_name, getattr(other, attribute_name))

    def objects(self):
        from ConfigParser import NoOptionError
        for section_name in self.config.sections():
            obj = self.object_type()
            setattr(obj, obj.attribute_names[0], section_name)
            for attribute_name in obj.attribute_names[1:]:
                try:
                    setattr(obj, attribute_name, self.config.get(section_name, attribute_name))
                except NoOptionError:
                    setattr(obj, attribute_name, None)
            yield obj


    def remove(self, other):
        return self.config.remove_section(other.attribute_names[0])

    def read(self, config_path):
        self.config.read(config_path)

    def readfp(self, config_fp):
        self.config.readfp(config_fp)

    def write(self, file_object):
        self.config.write(file_object)


