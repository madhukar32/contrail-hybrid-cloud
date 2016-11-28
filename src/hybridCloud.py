from contrail.vncNetwork import vncNetwork
from contrail.vncService import vncService
from contrail.vncPolicy import vncPolicy
from contrail.vncPort import vncPort
from contrail.util import vncObj

from junos_pyez.loadConfig import loadConfig
from jnpr.junos.exception import ConnectTimeoutError

from hybridLogger import hybridLogger

from nova.novaBasic import novaBasic
from exception import *

import yaml
import sys
import os
import time

from aws.vpc import vpc
from aws.vpn import vpnConnection
from aws.s3Instance import s3Instance
from aws.vpnCustomerConfig.createJuniperConfig import createJuniperConfig
from aws.util import awsTag


class privateCloud(hybridLogger): 

    def __init__(self, inputDict, logLevel='INFO'):

        self.level = logLevel
        self.log = super(privateCloud,self).log(level=logLevel, name=privateCloud.__name__)

        self.inputDict = inputDict
        
        self.tenantName = self.inputDict['tenantName']
        self.domain = self.inputDict['domain']
        username = self.inputDict['username']
        password = self.inputDict['password']
        apiHost = self.inputDict['apiHost']
        
        #Getting vnc object
        self.vncObj = vncObj.get(username=username, tenantName=self.tenantName, domain=self.domain,
                password=password, apiHost=apiHost)

    def setup(self):

        # Creating network
        vncN = vncNetwork(self.vncObj, self.domain, self.tenantName, logLevel=self.level)

        for network in self.inputDict['networks']:
            
            if 'allocationPool' in network.keys():
                allocationPool = network['allocationPool']
            else:
                allocationPool = False

            if 'routeTarget' in network.keys():
                routeTarget = network['routeTarget']
            else:
                routeTarget = False

            if 'fipPoolName' in network.keys():
                fipPoolName = network['fipPoolName']
            else:
                fipPoolName = False

            networkName = network['name']
            networkCidr = network['cidr']

            netObj = vncN.createNetwork(cidr=networkCidr, name = networkName, 
                    allocationPool= allocationPool,routeTarget = routeTarget, fipPoolName=fipPoolName)

            if not netObj:
                return False

            network['obj'] = netObj

        self.log.debug("Updated network list with object: {0}".format(self.inputDict['networks']))

        #Create Service Template v2
        
        for template in self.inputDict['services']['templates']:
            svcTempName = template['name']
            intfMap = template['intfMapping']

            if 'serviceMode' in template.keys():
                svcMode = template['serviceMode']
            else:
                svcMode = 'in-network'

            if 'serviceType' in template.keys():
                svcType = template['serviceType']
            else:
                svcType = 'firewall'

            if 'orderedIntf' in template.keys():
                orderedIntf = template['orderedIntf']
            else:
                orderedIntf = True

            vncSvc = vncService(self.vncObj,interfaceMapping = intfMap,domain = self.domain, tenantName=self.tenantName, logLevel=self.level)

            vncSvcTmpObj = vncSvc.createServiceTemplateV2(serviceTempName=svcTempName)

            if not vncSvcTmpObj:
                return False

            template['obj'] = vncSvcTmpObj

        #Create vSRX Instance
        novaClient = novaBasic(logLevel=self.level)

        vncVmi = vncPort(self.vncObj, domain = self.domain, tenantName=self.tenantName, logLevel=self.level)

        for novaInstance in self.inputDict['nova'].keys():
            networkList = self.inputDict['nova'][novaInstance]['networks']

            #Create virtual machine interfaces

            updatedNetwork = vncVmi.createPorts(portList=networkList)
            self.inputDict['nova'][novaInstance]['networks'] = updatedNetwork

            portIdList = [networks['portId'] for networks in updatedNetwork]

            instanceImage = self.inputDict['nova'][novaInstance]['imageName']
            instanceFlavor = self.inputDict['nova'][novaInstance]['flavorName']
            instanceName = self.inputDict['nova'][novaInstance]['instanceName']

            novaInstanceObj = novaClient.createInstance(port_id_list=portIdList, image_name=instanceImage,flavor_name=instanceFlavor, instance_name=instanceName)
            self.inputDict['nova'][novaInstance]['obj'] = novaInstanceObj
        
        #Create Service Instance v2
        for svcInstance in self.inputDict['services']['instances']:
            svcInstanceName = svcInstance['name']
            svcTempName = svcInstance['templateName']

            if svcInstance['instanceKey'] in self.inputDict['nova'].keys():
                networkDetails = self.inputDict['nova'][svcInstance['instanceKey']]['networks']
            else:
                raise AssertionError("instanceKey does not match with your nova instance key, please check your input file")

            vncSvcInstObj = vncSvc.createServiceInstancev2(serviceInstanceName=svcInstanceName, serviceTempName=svcTempName, networkDetails=networkDetails)
            
            if not vncSvcInstObj:
                continue
            else:
                svcInstance['obj'] = vncSvcInstObj

        #Create Policy

        vncP = vncPolicy(self.vncObj, domain = self.domain, tenantName=self.tenantName, logLevel=self.level)

        for policy in self.inputDict['policies']:
            policyName = policy['name']
            srcNetwork = policy['srcNetwork']
            destNetwork = policy['destNetwork']
            svcInstName = policy['serviceInstance']

            vncPolicyObj = vncP.createServicePolicy(activeSvcInstName=svcInstName, policyName=policyName, srcNetwork=srcNetwork, destNetwork=destNetwork)
            vncP.attachPolicyToNetwork(policyName=policyName, networkList=[srcNetwork, destNetwork])

        return self.inputDict

class awsCloud(hybridLogger):

    def __init__(self, inputDict, customerGwIp):
        
        self.log = super(awsCloud,self).log(name=awsCloud.__name__)
        self.inputDict = inputDict
        self.vpcName = self.inputDict['vpc']['name']
        self.awsCidrBlock = self.inputDict['vpc']['cidrBlock']
        self.privateCloudCidr = self.inputDict['privateCloudCidr']
        self.customerGwIp = customerGwIp
        self.awsResourceIdList = []

    def setup(self):

        vpnH = vpnConnection()

        vpcRet = vpnH.createVpc(vpcName=self.vpcName, cidrBlock = self.awsCidrBlock)
        vpcId = vpcRet['vpcId']
        routeTableId = vpcRet['routeTableId']
        sgId =  vpcRet['securityGroupId']

        self.inputDict['vpcId'] = vpcId
        self.inputDict['routeTableId'] = routeTableId
        self.inputDict['securityGroupId'] = sgId

        self.awsResourceIdList.append(vpcId)
        self.awsResourceIdList.append(routeTableId)
        self.awsResourceIdList.append(sgId)

        subnetRet = vpnH.createSubnet(vpcId = vpcId, vpcSubnet = self.awsCidrBlock)
        subnetId = subnetRet['subnetId']
        self.inputDict['subnetId'] = subnetId
        self.awsResourceIdList.append(subnetId)
        ret = vpnH.associateSubnetWithRouteTable(routeTableId=routeTableId,
                subnetId = subnetId)
        self.log.info(ret)

        custGwRet=vpnH.createCustomerGw(gatewayIP=self.customerGwIp, 
                customerCidrBlock=self.privateCloudCidr, sgId = sgId)
        if custGwRet:
            custGwId = custGwRet['customerGatewayId']
            self.awsResourceIdList.append(custGwId)
            self.inputDict['customerGatewayId'] = custGwId
        else:
            self.log.error("While creating customer gateway", exc_info=True)  
            return False

        vpnGwRet = vpnH.createVpnGw(vpcId=vpcId, routeTableId = routeTableId)
        if vpnGwRet:
            vpnGwId = vpnGwRet['vpnGatewayId']
            self.awsResourceIdList.append(vpnGwId)
            self.inputDict['vpnGatewayId'] = vpnGwId
        else:
            self.log.error("While creating Vpn gateway", exc_info=True)  
            return False


        vpnConnectionRet = vpnH.createVpnConnection(custGwId = custGwId, vpnGwId = vpnGwId)
        if vpnGwRet:
            vpnConnectionId = vpnConnectionRet['vpnConnectionId']
            self.awsResourceIdList.append(vpnConnectionId)
            self.inputDict['vpnConnectionId'] = vpnConnectionId
        else:
            self.log.error("While creating Vpn Connecion", exc_info=True)  
            return False

        vpnRoute = vpnH.createVpnRoute(customerCidrBlock = self.privateCloudCidr, vpnConnectionId=vpnConnectionId)
        if vpnRoute:
            pass
        else:
            self.log.error("While creating Vpn Route", exc_info=True)  
            return False

        awsTag.assignTag(vpnH.ec2, name='Name', value=self.vpcName, resourceIdList=self.awsResourceIdList)

        configXml = vpnH.getCustomerConfigInfo(vpnConnectionId = vpnConnectionId)
        self.inputDict['awsOutputXml'] = configXml
        self.log.debug("This is how the vpnconnection config looks like: \n{0}".format(configXml))

        keyPairName = self.inputDict['s3Instance']['keyPairName']
        awsImageId = self.inputDict['s3Instance']['imageId']
        awsFlavor = self.inputDict['s3Instance']['instanceType']

        s3H = s3Instance()
        instances = s3H.create(name=self.vpcName, subnetId=subnetId, sgId=sgId, 
                imageId=awsImageId, instanceType=awsFlavor, keyPairName=keyPairName)
        self.log.info(instances)
        instanceIdList = instances['instanceId']

        custRoutableIntf = self.inputDict['publiclyRoutableIntf']
        templatePath = self.inputDict['junosJ2TemplatePath']
        outputJunosFile = self.inputDict['outputJunosFile']

        junosconf = createJuniperConfig(awsVpnConfigXml = configXml, awsCidrBlock = self.awsCidrBlock, 
                custRoutableIntf=custRoutableIntf)

        vpn_dict  = junosconf.parseXml()
        junosconf.outputConfig(templatePath = templatePath, outputConfFile=outputJunosFile)


if __name__ == "__main__":

    h = hybridLogger()
    log = h.log(name= __name__)

    try:
        inputYamlFile = sys.argv[1]
    except IndexError:
        log.error("yaml file should be passed as an arguement. Ex: python hybridCloud.py inputHybird.yaml", exc_info=True)
        sys.exit(1)

    try:
        level = sys.argv[2]
        inputLogList = level.split('=')
        validKey = ['level', 'loglevel', 'log']
        validValue = ['INFO', 'ERROR', 'WARN', 'DEBUG', 'CRITICAL']
        logKey = inputLogList[0]
        logKey = logKey.lower()
        logValue = inputLogList[1]
        logValue = logValue.upper()

        if logKey not in validKey:
            raise KeyError()

        if logValue not in validValue:
            raise ValueError()
        logLevel = logValue

    except IndexError:
        logLevel = 'INFO'
    except KeyError, ValueError:
        print "Log value is not in correct format, setting the log level to INFO by default"
        logLevel = 'INFO'

    if os.path.exists(inputYamlFile):
        fh = open(inputYamlFile)
    else:
        log.error("File: {0} path does not exist".format(inputYamlFile), exc_info=True)
        sys.exit(1)
    
    try:
        hybridCloudDict = yaml.safe_load(fh)
    except Exception as e:
        log.error(e, exc_info=True)
        sys.exit(1)

    publicCloudDict = hybridCloudDict['publicCloud']
    privateCloudDict = hybridCloudDict['privateCloud']

    try:
        private = privateCloud(privateCloudDict, logLevel=logLevel)
        updatedPrivateDict = private.setup()
    except Exception as e:
        log.error(e, exc_info=True)
        sys.exit(1)

    for network in updatedPrivateDict['networks']:
        if network['name'] == updatedPrivateDict['publiclyRoutableNetwork']:
            custGwIp = network['ip']

    try:
        public = awsCloud(publicCloudDict, custGwIp)
        updatedPublicDict = public.setup()
    except Exception as e:
        log.error(e, exc_info=True)
        sys.exit(1)

    outputJunosFile = publicCloudDict['outputJunosFile']

    vsrxUsername = privateCloudDict['nova']['vsrx']['username']
    vsrxPassword = privateCloudDict['nova']['vsrx']['password']
    vsrxUp = False
    for t in range(10, 3, -1):
        try:
            vSRX = loadConfig(ip=custGwIp, user = vsrxUsername, password = vsrxPassword)
            vsrxUp = True
        except ConnectTimeoutError:
            t = t-2
            time.sleep(10*t)
            continue

    if vsrxUp:
        vSRX.load(vpnConfFile=outputJunosFile)
        log.info("Successfully loaded the configuration")
    else:
        log.error("vSRX failed to come up")

