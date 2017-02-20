from vnc_api import vnc_api
from vnc_api.vnc_api import NoIdError

from hybridLogger import hybridLogger

from contrail.util import (readSvcTemplate, readNetwork, readTenant, readPolicy, readInstanceIp)

from exception import *

import uuid

class vncPort(hybridLogger):

    def __init__(self, vnc, **kwargs):
        logLevel = kwargs.get('logLevel', 'INFO')
        self.log = super(vncPort, self).log(level=logLevel, name=vncPort.__name__)

        self.vnc = vnc
        _requiredArgs = ['domain', 'tenantName']

        try:
            self.domain = kwargs['domain']
            self.tenantName = kwargs['tenantName']
        except KeyError:
            raise ArguementError(_requiredArgs, vncPort.__name__)

        self.tenantObj = readTenant(self.vnc, domain=self.domain, tenantName=self.tenantName)

    def createPorts(self, **kwargs):

        _requiredArgs = ['portList']

        try:
            portList = kwargs['portList']
        except KeyError:
            raise ArguementError(_requiredArgs, vncPort.createPorts.__name__)

	for portDetails in portList:
            try:
                network = portDetails['name']
            except KeyError:
                raise AssertionError("Please check your input file, path /nova/instance/networks/ does not have name")

            tempPortId = str(uuid.uuid4())

            try:
                vmi = vnc_api.VirtualMachineInterface(name=tempPortId, parent_obj = self.tenantObj)
            except Exception as e:
                 ContrailError(vncApi='vnc_api.VirtualMachineInterface', error=e)

            vmi.uuid = tempPortId
            networkObj = readNetwork(self.vnc, domain=self.domain, tenantName = self.tenantName, networkName=network)
            vmi.add_virtual_network(networkObj)
            self.vnc.virtual_machine_interface_create(vmi)
            portDetails['portId'] = vmi.uuid
            
            #Attach instance ip to the port
            instanceIpObj = self.returnInstanceIpForVmi(vmi, networkObj)

            portDetails['instanceIpId'] = instanceIpObj.uuid
            portDetails['instanceIp'] = self.getInstanceIp(instanceIpObj.uuid)

            self.log.debug("Created port and associated Ip with port_id: {0} instance_ip_id: {1}".format(vmi.uuid, instanceIpObj.uuid))

            try:
                fip = portDetails['fip']
            except KeyError:
                fip = False

            if fip:
                try:
                    fipPoolNetwork = portDetails['fipPoolNetwork']
                except KeyError:
                    raise AssertionError('In path privateCloud/nova/ fip has been set but fipPoolNetwork has not been provide')

                self.allocateAndAssociateFip(fipPoolNetwork, vmi)

        return portList

    def returnInstanceIpForVmi(self, vmi, networkObj):

        instanceIpId = str(uuid.uuid4())
        instanceIpObj = vnc_api.InstanceIp(name=instanceIpId)
        instanceIpObj.uuid = instanceIpId
        instanceIpObj.add_virtual_machine_interface(vmi)
        instanceIpObj.add_virtual_network(networkObj)
        self.vnc.instance_ip_create(instanceIpObj)
        return instanceIpObj

    def allocateAndAssociateFip(self, fipPoolNetwork, vmi):
        #Create Floating IP
        fipId = str(uuid.uuid4())

        fipPool = self.vnc.floating_ip_pool_read(fq_name = ['default-domain', self.tenantName, fipPoolNetwork])

        fip = vnc_api.FloatingIp(name = fipId, parent_obj = fipPool)
        fip.uuid = fipId

        fip.add_project(self.tenantObj)
        self.vnc.floating_ip_create(fip)
        self.log.debug("Created fip with fip_id: {0}".format(fip.uuid))

        #Assosiate fip

        fip.add_virtual_machine_interface(vmi)
        self.vnc.floating_ip_update(fip)

    def getInstanceIp(self, iipId):

	iipObject = readInstanceIp(self.vnc, iipId)

        return str(iipObject.get_instance_ip_address())
