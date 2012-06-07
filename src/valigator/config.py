from fabric.api import abort
import ConfigParser

class ConfigOption(object):
	"""An option retrieved from a config 'file'"""
	name = None
	section = None
	config = None
	@property
	def value(self):
		return self.config.get(str(self.section.name), str(self.name))

class ConfigSection(object):
	name = None
	config = None
	option_type = ConfigOption
	def __getattr__(self, option_name):
		try:
			return self.__dict__[option_name]
		except KeyError:
			ret = self.option_type()
			ret.name = option_name
			ret.config = self.config
			ret.section = self
			self.__dict__[option_name] = ret
			return ret

class AbortedConfigSection(ConfigSection):
	def __getattr__(self, option_name):
		try:
			ConfigSection.__getattr__(self, option_name)
		except NoOptionError as e:
			abort("No optioion %s in config %s (%s)" % (option_name,
						self.config, e))

class Config(object):
	config = None
	section_type = ConfigSection
	def __getattr__(self, section_name):
		ret = self.section_type()
		ret.config = self.config
		ret.name = section_name
		return ret

class MappedConfig(Config):
	section_type_map = None
	def __getattr__(self, section_name):
		self.section_type = self.section_type_map(self.config, section_name)
		return Config.__getattr__(self, section_name)

class AbortedConfig(Config):
	section_type = AbortedConfigSection
	def __getattr__(self, section_name):
		try:
			Config.__getattr__(self, section_name)
		except NoSectionError as e:
			abort("section %s not found in config %s (%s)" % (section_name, self.config, e))

class ConfigFile(Config):
	def __init__(self, file_name):
		self.config = ConfigParser.ConfigParser()
		cfd = open(file_name)
		self.config.readfp(cfd)
		cfd.close()
		self.file_name = file_name

class AbortedConfigFile(ConfigFile):
	def __int__(self, file_name):
		try:
			ConfigFile.__init__(self, file_name)
		except Error as e:
			abort("Error %s reading config %s" % (e, file_name))

class ConfigOptionsList(object):
	name = None
	config = None
	option_type = ConfigOption
	@property
	def options(self):
		options = []
		for option_name in self.config.options(str(self.name)):
			option = self.option_type()
			option.section_name = self.name
			option.name = option_name
			options.append(option)
		return options

class AbortedConfigOptionsList(ConfigOptionsList):
	@property
	def options(self):
		try:
			return ConfigOptionsList.options
		except Error as e:
			abort("Unable to create list of options for section %s (%s)" %
					(self.name, e))
