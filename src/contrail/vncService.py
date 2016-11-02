from vnc_api import vnc_api
import uuid

from hybridLogger import hybridLogger

from contrail.util import (readSvcTemplate, readNetwork, readTenant)

from exception import *

class vncService(hybridLogger):

    def __init__(self, vnc, **kwargs):

        self.log = super(vncService, self).log(name=vncService.__name__)
        self.vnc = vnc

        _requiredArgs = ['serviceTempName', 'interfaceMapping', 'domain', 'tenantName']

        try:
            self.interfaceMapping = kwargs['interfaceMapping']
            self.domain = kwargs['domain']
            self.tenantName = kwargs['tenantName']
        except KeyError:
            raise ArguementError(_requiredArgs, vncService.__name__)


        self.tenantObj = readTenant(self.vnc, domain=self.domain, tenantName=self.tenantName)

    def createServiceTemplateV2(self, **kwargs):


        serviceMode = kwargs.get('serviceMode', 'in-network')
        serviceType = kwargs.get('serviceType', 'firewall')
        orderedIntf = kwargs.get('orderedIntf', True)
        
        serviceTempName = kwargs['serviceTempName']
        stFqName = [self.domain, serviceTempName]

        try:
            serviceTemplate = readSvcTemplate(self.vnc, stFqName)
            self.log.warn("Service Template: {0} already exists".format(serviceTempName))
            return serviceTemplate
        except ContrailError:
            try:
                serviceTemplate = vnc_api.ServiceTemplate(name = serviceTempName)
                serviceTemplateType = vnc_api.ServiceTemplateType(version = 2, service_mode = serviceMode, 
                        service_type = serviceType, ordered_interfaces = orderedIntf)
                
                for intfType in self.interfaceMapping.keys():
                    vnName = self.interfaceMapping[intfType]
                    templateInterfaceType = vnc_api.ServiceTemplateInterfaceType(service_interface_type = intfType)
                    serviceTemplateType.add_interface_type(templateInterfaceType)
                
                serviceTemplate.set_service_template_properties(serviceTemplateType)
                serviceTemplateId = self.vnc.service_template_create(serviceTemplate)
                self.log.info("Service Template: {0} created ".format(serviceTempName))
            except Exception as e:
                raise ContrailError(vncApi='vnc_api.ServiceTemplate', error=e)


        return serviceTemplate


    def createServiceInstancev2(self, **kwargs):

        _requiredArgs = ['serviceInstanceName']

        serviceTempName = kwargs['serviceTempName']
        stFqName = [self.domain, serviceTempName]

        try:
            serviceInstanceName = kwargs.get('serviceInstanceName') 
        except KeyError:
            raise ArguementError(_requiredArgs, vncService.createServiceInstancev2.__name__)

        portTuple = []

        for intfType in self.interfaceMapping.keys():
            try:
                vnName = self.interfaceMapping[intfType]
                vnObj = readNetwork(self.vnc, domain=self.domain, 
                        tenantName=self.tenantName,networkName=vnName)
                vmiRef =  vnObj.get_virtual_machine_interface_back_refs()
                vmiId = vmiRef[0].get('uuid')
                portTuple.append(intfType+ '=' + str(vmiId))
            except (ContrailError, ArguementError) as e:
                self.log.error("Reading network failed with message: {0}".format(e))
                return False
            except IndexError as e:
                self.log.error("irtualNetwork does not have any Virtual Mahine Interface: {0}".format(e))
                return False



        try:
            serviceTemplate = readSvcTemplate(self.vnc, stFqName)
        except ContrailError:
            self.log.error("Service Template: {0} Does not exist".format(serviceTempName))
            return False
        
        try:
            serviceInstance = vnc_api.ServiceInstance(name = serviceInstanceName, parent_obj = self.tenantObj)
            serviceInstance.uuid = str(uuid.uuid4())
            serviceInstance.add_service_template(serviceTemplate)
            
            serviceInstanceType = vnc_api.ServiceInstanceType()
            stProperties = serviceTemplate.get_service_template_properties()
            
            for stInterface in stProperties.get_interface_type():
                stTypeName = stInterface.get_service_interface_type()
                interface = vnc_api.ServiceInstanceInterfaceType()
                interface.set_virtual_network(self.interfaceMapping[stTypeName])
                serviceInstanceType.add_interface_list(interface)
        except Exception as e:
            raise ContrailError(vncApi=['vnc_api.ServiceInstance', 'vnc_api.ServiceInstanceType', 'vnc_api.ServiceInstanceInterfaceType'], error=e)

        try:
            serviceInstance.set_service_instance_properties(serviceInstanceType)
            siId = self.vnc.service_instance_create(serviceInstance)
            self.log.info("Created Service Instance {0}".format(siId))
        except Exception as e:
            raise ContrailError(vncApi= 'vnc.service_instance_create', error=e)


        # Create port tuples

        ptList = []
        ptDict = {}
        self.log.info(portTuple)
        for intfMap in portTuple:
            portType, portId = intfMap.split('=')
            vmInterface = self.vnc.virtual_machine_interface_read(id = portId)
            vmIntfProps = vnc_api.VirtualMachineInterfacePropertiesType()
            vmIntfProps.set_service_interface_type(portType)
            vmInterface.set_virtual_machine_interface_properties(vmIntfProps)
            ptDict[portType] = vmInterface
        ptList.append(ptDict)

        idx = 0
        for tuples in ptList:
            name = str(serviceInstance.display_name) + '-port-tuple-' + str(idx)
            idx += 1
            pt = vnc_api.PortTuple(name = name, parent_obj = serviceInstance)
            self.vnc.port_tuple_create(pt)
            for types in tuples.keys():
                tuples[types].add_port_tuple(pt)
                self.vnc.virtual_machine_interface_update(tuples[types])

        return serviceInstance

