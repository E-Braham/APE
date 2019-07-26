import logging
import sys
from importlib import reload
from inspect import isclass
from types import ModuleType

from qtpy.QtCore import QObject, Property, Signal, Slot, QUrl

import Procedures
import Project_Procedures
from Core import Procedure, Apparatus, Executor
from GUI.main.ape.base.helpers import value_to_str, str_to_value
from ..nodes import GuiNode

logger = logging.getLogger('ProcedureInterface')


class ProcedureInterface(QObject):
    _gui_node: GuiNode
    guiNodeChanged = Signal()
    eprocsChanged = Signal()
    proclistChanged = Signal()
    proceduresChanged = Signal()

    def __init__(self, parent=None):
        super(ProcedureInterface, self).__init__(parent)

        self._gui_node = None
        self._eprocs = {}
        self._proclist = []
        self._procedures = []
        self._device_nodes = {}

    @Property(GuiNode, notify=guiNodeChanged)
    def guiNode(self):
        return self._gui_node

    @guiNode.setter
    def guiNode(self, value):
        if value == self._gui_node:
            return
        self._gui_node = value
        self.guiNodeChanged.emit()

    @property
    def eprocs(self):
        return self._eprocs

    @Property(list, notify=proclistChanged)
    def proclist(self):
        return self._proclist

    @Property(list, notify=proceduresChanged)
    def procedures(self):
        return self._procedures

    @Slot()
    def refreshEprocs(self):
        if not self._gui_node:
            logger.warning('Cannot fetch eprocs without guiNode')
            return

        def procs_from_module(module):
            procs = []
            for name in dir(module):
                proc = getattr(module, name)
                if isclass(proc) and issubclass(proc, Procedure):
                    procs.append(name)
            return procs

        logger.debug('fetching EProcs')
        epl_dict = {
            'Procedures': procs_from_module(Procedures),
            'Project_Procedures': procs_from_module(Project_Procedures),
        }

        self._device_nodes.clear()

        def fetch_procs(node):
            epl = self._gui_node.executor.getDevices(node)
            for device in epl:
                eprocs = self._gui_node.executor.getEprocs(device, node)
                epl_dict[device] = eprocs
                self._device_nodes[device] = node

        fetch_procs('procexec')
        fetch_procs('gui')
        logger.debug(f'Eprocs fetched {epl_dict}')
        self._eprocs = epl_dict
        self.eprocsChanged.emit()

    @Slot(str, str, result=list)
    def getRequirements(self, device, procedure):
        if not self._gui_node:
            logger.warning('Cannot fetch requirements without guiNode')
            return

        if device in ('Procedures', 'Project_Procedures', ''):
            if device == 'Procedures':
                module = Procedures
            elif device == 'Project_Procedures':
                module = Project_Procedures
            else:
                module = (
                    Procedures if procedure in dir(Procedures) else Project_Procedures
                )
            try:
                apparatus = Apparatus()
                executor = Executor()
                f = getattr(module, procedure)(apparatus, executor)
                return [
                    {'key': k, "value": value_to_str(v['value'])}
                    for k, v in f.requirements.items()
                ]
            except Exception as e:
                logger.warning(
                    f'Cannot fetch requirements of {device}_{procedure}: {str(e)}'
                )
                return []
        else:
            node = self._device_nodes.get(device, 'procexec')
            reqs = self._gui_node.executor.getRequirements(device, procedure, node)
            return [{'key': k, 'value': ''} for k in reqs]

    @staticmethod
    def _convert_procedure_list(procedures):
        for entry in procedures:
            if entry['device']:
                entry['name'] = f'{entry["device"]}_{entry["procedure"]}'
            else:
                entry['name'] = entry['procedure']
            raw_reqs = entry["requirements"]
            entry["requirements"] = [
                {'key': k, 'value': value_to_str(v)} for k, v in raw_reqs.items()
            ]
        return procedures

    @Slot()
    def refreshProclist(self):
        if not self._gui_node:
            logger.warning('Cannot refresh proclist without guiNode')
            return

        logger.debug('fetching proclist')
        proclist = self._gui_node.executor.getProclist()
        logger.debug(f'proclist updated {proclist}')
        self._proclist = self._convert_procedure_list(proclist)
        self.proclistChanged.emit()

    @Slot()
    def refreshProcedures(self):
        if not self._gui_node:
            logger.warning('Cannot refresh procedures without guiNode')
            return

        logger.debug('fetchiing procedures')
        procedures = self._gui_node.executor.getProcedures()
        logger.debug(f'procedures updated {procedures}')
        self._procedures = self._convert_procedure_list(procedures)
        self.proceduresChanged.emit()

    @staticmethod
    def _convert_req_model_to_list(requirements):
        return {
            entry['key']: str_to_value(entry['value'])
            for entry in requirements
            if entry['value']
        }

    @Slot(str, str, list)
    def addProclistItem(self, device, procedure, requirements):
        if not self._gui_node:
            logger.warning('Cannot add requirements without guiNode')
            return

        if device in ('Procedures', 'Project_Procedures'):
            device = ''

        reqs = self._convert_req_model_to_list(requirements)
        self._gui_node.executor.insertProclistItem(
            index=-1, device=device, procedure=procedure, requirements=reqs
        )

    @Slot(int)
    def removeProclistItem(self, index):
        if not self._gui_node:
            logger.warning('Cannot remove procedure without guiNode')
            return

        if 0 <= index < len(self._proclist):
            self._gui_node.executor.removeProclistItem(index=index)

    @Slot(int)
    def moveProcedureUp(self, index):
        if not self._gui_node:
            logger.warning('Cannot move procedure without guiNode')
            return

        if 0 < index < len(self._proclist):
            self._gui_node.executor.swapProclistItems(index - 1, index)

    @Slot(int)
    def moveProcedureDown(self, index):
        if not self._gui_node:
            logger.warning('Cannot move procedure without guiNode')
            return

        if 0 <= index < (len(self._proclist) - 1):
            self._gui_node.executor.swapProclistItems(index + 1, index)

    @Slot(int, list)
    def updateProclistItem(self, index, requirements):
        if not self._gui_node:
            logger.warning('Cannot update procedure without guiNode')
            return

        if 0 <= index < len(self._proclist):
            reqs = self._convert_req_model_to_list(requirements)
            self._gui_node.executor.updateProclistItem(index, reqs)

    @Slot()
    def clearProclist(self):
        if not self._gui_node:
            logger.warning('Cannot clear proclist without guiNode')
            return

        self._gui_node.executor.clearProclist()

    @Slot(int)
    def doProclistItem(self, index):
        if not self._gui_node:
            logger.warning('Cannot doProclistItem procedure without guiNode')
            return

        if 0 <= index < len(self._proclist):
            self._gui_node.executor.doProclistItem(index)

    @Slot()
    def doProclist(self):
        if not self._gui_node:
            logger.warning('Cannot do proclist without guiNode')
            return

        self._gui_node.executor.doProclist()

    @Slot(str, str, list)
    def do(self, device, procedure, requirements):
        if not self._gui_node:
            logger.warning('Cannot do procedure without guiNode')
            return

        if device in ('Procedures', 'Project_Procedures'):
            device = ''

        logger.debug(f'do procedure {device}_{procedure}')
        reqs = self._convert_req_model_to_list(requirements)
        self._gui_node.executor.do(device, procedure, reqs)
        logger.debug('done')

    @Slot(str, str)
    def doProcedure(self, device, procedure):
        if not self._gui_node:
            logger.warning('Cannot do procedure without guiNode')
            return

        if device in ('Procedures', 'Project_Procedures'):
            device = ''

        logger.debug(f'do procedure {device}_{procedure}')
        self._gui_node.executor.doProcedure(device, procedure)
        logger.debug('done')

    @Slot()
    def clearProcedures(self):
        if not self._gui_node:
            logger.warning('Cannot clear procedures without guiNode')
            return

        self._gui_node.executor.clearProcedures()

    @Slot()
    def reloadProcedures(self):
        if not self._gui_node:
            logger.warning('Cannot reload procedures without guiNode')
            return

        def deep_reload(module):
            for attribute_name in dir(module):
                attribute = getattr(module, attribute_name)
                if isclass(attribute):
                    reload(sys.modules[attribute.__module__])
                elif type(attribute) is ModuleType:
                    reload(attribute)
            reload(module)

        deep_reload(Procedures)
        deep_reload(Project_Procedures)

        self._gui_node.executor.reloadProcedures()

    @Slot(str, str, list)
    def createProcedure(self, device, procedure, requirements):
        if not self._gui_node:
            logger.warning('Cannot create procedure without guiNode')
            return

        if device in ('Procedures', 'Project_Procedures'):
            device = ''

        reqs = self._convert_req_model_to_list(requirements)
        self._gui_node.executor.createProcedure(device, procedure, reqs)

    @Slot(str, str)
    def removeProcedure(self, device, procedure):
        if not self._gui_node:
            logger.warning('Cannot remove procedure without guiNode')
            return

        if device in ('Procedures', 'Project_Procedures'):
            device = ''

        self._gui_node.executor.removeProcedure(device, procedure)

    @Slot(QUrl)
    def saveAs(self, url):
        if not self._gui_node:
            logger.warning('Cannot save without guiNode')
            return

        filename = url.toLocalFile()
        self._gui_node.executor.exportProclist(filename)

    @Slot(QUrl)
    def importFrom(self, url):
        if not self._gui_node:
            logger.warning('Cannot import without guiNode')
            return

        filename = url.toLocalFile()
        self._gui_node.executor.importProclist(filename)

    def _create_device(self, device_name, device_type, exec_address, rel_address):
        created = self._gui_node.executor.createDevice(
            device_name, device_type, exec_address, rel_address
        )
        if created:
            address = ['devices', device_name, 'type']
            if not self._gui_node.apparatus.checkAddress(address):
                self._gui_node.apparatus.createAppEntry(address)
            self._gui_node.apparatus.setValue(address, 'User_GUI')
            address = ['devices', device_name, 'address']
            if not self._gui_node.apparatus.checkAddress(address):
                self._gui_node.apparatus.createAppEntry(address)
            self._gui_node.apparatus.setValue(address, rel_address)
            address = ['devices', device_name, 'addresstype']
            if not self._gui_node.apparatus.checkAddress(address):
                self._gui_node.apparatus.createAppEntry(address)
            self._gui_node.apparatus.setValue(address, 'zmqNode')
            return True
        else:
            logger.error(f"Creating device {device_name} {device_type} failed")
            return False

    @Slot(str, str, result=bool)
    def createDevice(self, device_name, device_type):
        if not self._gui_node:
            logger.warning('Cannot create device without guiNode')
            return

        return self._create_device(device_name, device_type, 'procexec', 'procexec')

    @Slot(result=bool)
    def createUserDevice(self):
        if not self._gui_node:
            logger.warning('Cannot create use device without guiNode')
            return

        return self._create_device('User', 'User_GUI', 'procexec', 'gui')
