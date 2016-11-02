from credentials import get_nova_credentials
import os
from novaclient.client import Client
import time

class novaBasic(object):

    def __init__(self, **kwargs):
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

        nics = []
        for network in netList:
            netid = {}
            net = self.novaClient.networks.find(label=network)
            netid['net-id'] = net.id
            nics.append(netid)

        instance = self.novaClient.servers.create(name=instanceName, image=image,flavor=flavor, nics=nics)

        time.sleep(5)

        if instance not in self.novaClient.servers.list():
            raise Exception("Issue while creating server")
        return instance

