from credentials import get_nova_credentials
import os
from novaclient.client import Client
import time

from hybridLogger import hybridLogger

class novaBasic(hybridLogger):

    def __init__(self, **kwargs):

        logLevel = kwargs.get('logLevel', 'INFO')
        self.log = super(novaBasic, self).log(level=logLevel, name=novaBasic.__name__)
        try:
            novaCredentials = get_nova_credentials()
            self.novaClient = Client(**novaCredentials)
        except Exception as e:
            raise Exception(e.message)


    def createInstance(self, **kwargs):

        netList = kwargs.get('network_name_list')
        
        flavor = kwargs.get('flavor_name', 'm1.medium')
        flavor = self.novaClient.flavors.find(name=flavor)

        image  = kwargs.get('image_name')
        image = self.novaClient.images.find(name=image)
        
        instanceName = kwargs.get('instance_name')
        
        portIdList = kwargs.get('port_id_list')

        nics = []
        for portId in portIdList:
            port = {}
            port['port-id'] = portId
            nics.append(port)

        instance = self.novaClient.servers.create(name=instanceName, image=image,flavor=flavor, nics=nics)

        time.sleep(5)

        if instance not in self.novaClient.servers.list():
            raise Exception("Issue while creating server")
        self.log.info("Successfully created instance: {0}".format(instanceName))
        return instance

