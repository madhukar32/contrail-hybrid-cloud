try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

from jinja2 import Environment
from jinja2 import FileSystemLoader

from hybridLogger import hybridLogger
from exception import *

import os
import yaml

class createJuniperConfig(hybridLogger):

    def __init__(self, **kwargs):

        logLevel = kwargs.get('logLevel', 'INFO')
        self.log = super(createJuniperConfig, self).log(level=logLevel, name=createJuniperConfig.__name__)

        _requiredArgs = ['awsVpnConfigXml', 'awsCidrBlock', 'custRoutableIntf']
        try:
            self.awsVpnConfigXml = kwargs['awsVpnConfigXml']
            self.awsCidrBlock = kwargs['awsCidrBlock']
            self.custRoutableIntf = kwargs['custRoutableIntf']
        except KeyError as e:
            raise ArguementError(_requiredArgs, createJuniperConfig.__name__)

        self.juniperConfig = {}
        self.juniperConfig['aws_private_cidr'] = self.awsCidrBlock
        self.juniperConfig['routable_interface'] = self.custRoutableIntf
        self.juniperConfig['ipsec_tunnels'] = []
    
    def parseXml(self, **kwargs):

        try:
            awsVpnRoot = ET.fromstring(self.awsVpnConfigXml)
        except Exception as e:
            self.log.error("Function: parseXml Message: Error while converting xml string to xml element", exc_info=True)
            return False

        self.juniperConfig['vpn_connection_id'] = awsVpnRoot.attrib['id']
        tunnelNum = 0
        for ipsecTun in awsVpnRoot.findall('ipsec_tunnel'):
            tunnelNum += 1
            tunnelInfo = {}
            tunnelInfo['id'] = tunnelNum

            tunnelInfo['IKE'] = {}
            tunnelInfo['IKE']['authentication_protocol'] = ipsecTun.find('ike/authentication_protocol').text
            tunnelInfo['IKE']['encryption_protocol'] = ipsecTun.find('ike/encryption_protocol').text
            tunnelInfo['IKE']['lifetime'] = ipsecTun.find('ike/lifetime').text
            tunnelInfo['IKE']['perfect_forward_secrecy'] = ipsecTun.find('ike/perfect_forward_secrecy').text
            tunnelInfo['IKE']['mode'] = ipsecTun.find('ike/mode').text
            tunnelInfo['IKE']['pre_shared_key'] = ipsecTun.find('ike/pre_shared_key').text

            tunnelInfo['IPsec'] = {}
            tunnelInfo['IPsec']['protocol'] = ipsecTun.find('ipsec/protocol').text
            tunnelInfo['IPsec']['authentication_protocol'] = ipsecTun.find('ipsec/authentication_protocol').text
            tunnelInfo['IPsec']['encryption_protocol'] = ipsecTun.find('ipsec/encryption_protocol').text
            tunnelInfo['IPsec']['lifetime'] = ipsecTun.find('ipsec/lifetime').text
            tunnelInfo['IPsec']['perfect_forward_secrecy'] = ipsecTun.find('ipsec/perfect_forward_secrecy').text

            tunnelInfo['Tunnel'] = {}
            tunnelInfo['Tunnel']['bind_interface'] = "st0." + str(tunnelNum)
            tunnelInfo['Tunnel']['tcp_mss_adjustment'] = ipsecTun.find('ipsec/tcp_mss_adjustment').text
            tunnelInfo['Tunnel']['vpn_gateway_outside_address'] = ipsecTun.find('vpn_gateway/tunnel_outside_address/ip_address').text
            tunnelInfo['Tunnel']['vpn_gateway_inside_address'] = ipsecTun.find('vpn_gateway/tunnel_inside_address/ip_address').text
            tunnelInfo['Tunnel']['customer_gateway_inside_address'] = ipsecTun.find('customer_gateway/tunnel_inside_address/ip_address').text

            self.juniperConfig['ipsec_tunnels'].append(tunnelInfo)
        
        return self.juniperConfig

    def outputConfig(self, **kwargs):
        
        _requiredArgs = ['templatePath', 'outputConfFile']
        try:
            templatePath  = kwargs['templatePath']
            outputConfFile = kwargs['outputConfFile']
        except KeyError as e:
            raise ArguementError(_requiredArgs, createJuniperConfig.__name__)
        
        try: 
            directory = templatePath.rpartition('/')[0]
            fileName = templatePath.rpartition('/')[2]
        except IndexError:
            self.log.error("Function: outputConfig Message: Does not have a correct path \nEx: /home/vagrany/vpn.j2, ./vpn.j2", exc_info=True)
            return False


        if os.path.exists(templatePath):
            pass
        else:
            raise Exception("Function: outputConfig  Mesage: Invalid file Path")

        
        try:
            env = Environment(loader=FileSystemLoader(directory))
            template = env.get_template(fileName)
            junosConf = template.render(self.juniperConfig)
            self.log.debug("Juniper Configuration built: {0}".format(junosConf))
        except Exception as e:
            self.log.error("Function: outputConfig Message: Error while rendering the jinja template", exc_info=True)
            return False
        
        
        opFileHandle = open(outputConfFile, 'w+')
        opFileHandle.write(junosConf)
        opFileHandle.close()

        self.log.info("Junos Vpn configuration are written in path: {0}".format(outputConfFile))

