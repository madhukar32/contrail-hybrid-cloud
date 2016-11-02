from vnc_api import vnc_api

from contrail.util import (readTenant, readNetwork)

from hybridLogger import hybridLogger

from exception import *

class vncNetwork(hybridLogger):

    def __init__(self, vnc, domain, tenantName):

        self.log = super(vncNetwork, self).log(name=vncNetwork.__name__)
        self.vnc = vnc
        self.tenantName = tenantName
        self.domain = domain

        self.tenantObj = readTenant(self.vnc, domain=self.domain, tenantName=self.tenantName)

    def createNetwork(self, **kwargs):
        
        _requiredArgs = ['cidr', 'name']
        try:
            cidr = kwargs['cidr']
            networkName = kwargs['name']
            prefix, prefixLen = cidr.split('/')
        except KeyError:
            raise ArguementError(_requiredArgs, vncNetwork.createNetwork.__name__)
        except Exception as e:
            self.log.error("Function: createNetwork Message: cidr is not in correct format : {0}".format(e))
            return False

        prefixLen = int(prefixLen)


        try:
            allocationPool = kwargs['allocationPool']
        except KeyError, AttributeError:
            allocationPool = False

        try:
            routeTarget = kwargs['routeTarget']
        except KeyError, AttributeError:
            routeTarget = False

        if allocationPool:
            try:
                allocationPoolStart, allocationPoolStop = allocationPool.split('-') 
                allocType = vnc_api.AllocationPoolType()
                allocType.set_start(allocationPoolStart)
                allocType.set_end(allocationPoolStop)
                allocTypeList = [allocType]
            except Exception as e:
                self.log.error("Function: createNetwork Message: allocationPool error : {0}".format(e))
                return False
                
        else:
            allocTypeList = []

        try:
            networkObj = vnc_api.VirtualNetwork(name=networkName, parent_obj=self.tenantObj)
            
            networkExists = self._checkIfNetworkExists(networkObj, self.tenantObj)

            if networkExists:
                self.log.warn("Network: {0} already exists".format(networkName))
                return networkObj

            subnet = vnc_api.SubnetType(prefix, prefixLen)

            if not allocTypeList:
                ipamSubnet = vnc_api.IpamSubnetType(subnet = subnet)
            else:
                ipamSubnet = vnc_api.IpamSubnetType(subnet = subnet, allocation_pools=allocTypeList)

            networkObj.add_network_ipam(vnc_api.NetworkIpam(),vnc_api.VnSubnetsType([ipamSubnet]))
            newNetworkId = self.vnc.virtual_network_create(networkObj)
            self.log.info("Virtual Network: {0} created ".format(networkName))
        except Exception as e:
            self.log.error("Function: createNetwork Message: Error While Creating network : {0}".format(e))
            return False
            

        if routeTarget:
            try:
                updateNetwork = self._addRouteTarget(networkObj, routeTarget)
            except Exception as e:
                self.log.error("Function: createNetwork Message: Error While adding route target to the network: {0}".format(e))
                return False

        return networkObj

    def _checkIfNetworkExists(self, networkObj, tenantObj):

        newFqName = networkObj.get_fq_name()
        vnList = self.vnc.virtual_networks_list(parent_id=tenantObj.uuid)
        if not vnList:
            return False
        else:
            for elem in vnList['virtual-networks']:
                if(elem['fq_name'] == newFqName):
                    return True
                else:
                    continue
        return False

    def _addRouteTarget(self, networkObj, routeTarget):

        try:
            routeTargets = vnc_api.RouteTargetList(['target:' + routeTarget])
            networkObj.set_route_target_list(routeTargets)
            return self.vnc.virtual_network_update(networkObj)
        except Exception as e:
            raise ContrailError(vncApi='vnc_api.RouteTargetList', error=e)

