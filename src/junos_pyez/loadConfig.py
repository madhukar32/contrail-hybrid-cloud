from jnpr.junos import Device
from jnpr.junos.utils.config import Config
from jnpr.junos.exception import ConfigLoadError, CommitError

import time

class loadConfig(object):

    def __init__(self, **kwargs):

        deviceIp = kwargs.get('ip')
        user = kwargs.get('user', 'root')
        password = kwargs.get('password')

        device_handle = Device(host=deviceIp, user=user, password=password, port =22)

        self.device = device_handle.open()

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
