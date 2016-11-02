from vnc_api import vnc_api
from vnc_api.vnc_api import NoIdError

from hybridLogger import hybridLogger

from contrail.util import (readSvcTemplate, readNetwork, readTenant, readPolicy)

from exception import *

class vncPolicy(hybridLogger):

    def __init__(self, vnc, **kwargs):
        self.log = super(vncPolicy, self).log(name=vncPolicy.__name__)

        self.vnc = vnc
        _requiredArgs = ['domain', 'tenantName']

        try:
            self.domain = kwargs['domain']
            self.tenantName = kwargs['tenantName']
        except KeyError:
            raise ArguementError(_requiredArgs, vncPolicy.__name__)

        self.tenantObj = readTenant(self.vnc, domain=self.domain, tenantName=self.tenantName)

    def createServicePolicy(self, **kwargs):

        _requiredArgs = ['activeSvcInstName', 'policyName', 'srcNetwork', 'destNetwork']

        try:
            activeSvcInstName = kwargs['activeSvcInstName']
            policyName = kwargs['policyName']
            srcNetwork = kwargs['srcNetwork']
            destNetwork = kwargs['destNetwork']
        except KeyError:
            raise ArguementError(_requiredArgs, vncPolicy.createServicePolicy.__name__)
            
        svcFq = self.domain + ':' + self.tenantName + ':' +  activeSvcInstName
        srcNetworkFq = self.domain + ':' + self.tenantName + ':' + srcNetwork
        destNetworkFq = self.domain + ':' + self.tenantName + ':' + destNetwork
        
        try:
            actionList = vnc_api.ActionListType(apply_service = [svcFq])
            
            srcNetworkFqType = vnc_api.AddressType(virtual_network = srcNetworkFq)
            destNetworkFqType = vnc_api.AddressType(virtual_network = destNetworkFq)
            
            srcPortType = vnc_api.PortType(start_port = -1, end_port = -1)
            destPortType = vnc_api.PortType(start_port = -1, end_port = -1)

            rule = vnc_api.PolicyRuleType(direction = '<>',protocol = 'any',action_list = actionList, 
                        src_addresses = [srcNetworkFqType],src_ports = [srcPortType],dst_addresses = [destNetworkFqType],dst_ports = [destPortType])

            policy = vnc_api.NetworkPolicy(name = policyName, parent_obj = self.tenantObj, network_policy_entries = vnc_api.PolicyEntriesType([rule]))

            self.log.info("Created Network Policy")

            return self.vnc.network_policy_create(policy)

        except Exception as e:
            raise ContrailError(vncApi='vnc_api.NetworkPolicy', error=e)

    def attachPolicyToNetwork(self, **kwargs):
        
        _requiredArgs = ['policyName', 'networkList']

        try:
            networkList = kwargs['networkList']
            policyName = kwargs['policyName']
        except KeyError:
            raise ArguementError(_requiredArgs, vncPolicy.attachPolicyToNetwork.__name__)
        
        policy = readPolicy(self.vnc, domain=self.domain, tenantName=self.tenantName, policyName = policyName)
        policyType = vnc_api.VirtualNetworkPolicyType(sequence = vnc_api.SequenceType(major = 0, minor = 0))
        
        for network in networkList:
            virtualNetwork = readNetwork(self.vnc, domain=self.domain, tenantName=self.tenantName,
                    networkName = network)
            virtualNetwork.add_network_policy(ref_obj = policy, ref_data = policyType)
            self.vnc.virtual_network_update(virtualNetwork)

        self.log.info("Attached Policy to networks: {0}".format(networkList))
