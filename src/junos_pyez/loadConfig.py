from jnpr.junos import Device
from jnpr.junos.utils.config import Config
from jnpr.junos.exception import ConfigLoadError, CommitError

from hybridLogger import hybridLogger

import time

class loadConfig(hybridLogger):

    def __init__(self, **kwargs):

        logLevel = kwargs.get('logLevel', 'INFO')
        self.log = super(loadConfig, self).log(level=logLevel, name=loadConfig.__name__)
        deviceIp = kwargs.get('ip')
        user = kwargs.get('user', 'root')
        password = kwargs.get('password')

        deviceHandle = Device(host=deviceIp, user=user, password=password, port =22)

        self.device = deviceHandle.open()

        self.config = Config(self.device)

    def load(self, **kwargs):

        vpnConfFile = kwargs.get('vpnConfFile')

        try:
            self.config.load(path=vpnConfFile, merge=True)
        except ConfigLoadError as e:
                print e
                pass

        try:
            result =  self.config.commit()
            if result == True:
                time.sleep(1)
            else:
                raise AssertionError("Error while configuring device\n")
        except CommitError as e:
            raise Exception(e)

        self.device.close()
