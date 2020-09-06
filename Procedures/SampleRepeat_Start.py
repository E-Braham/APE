#THIS NEEDS TO BE RETURNED TO ITS ORIGINAL FORM#

from Core import Procedure
import copy

class SampleRepeat_Start(Procedure):
    def Prepare(self):
        self.name = 'SampleRepeat_Start'
        self.requirements['tray'] = {
            'source': 'apparatus',
            'address': '',
            'value': '',
            'desc': 'tray',
        }
        self.requirements['procedure'] = {
            'source': 'apparatus',
            'address': '',
            'value': '',
            'desc': 'pointer to defined procedure to be performed at each position in tray',
        }
        self.requirements['start_count'] = {
            'source': 'apparatus',
            'address': '',
            'value': '',
            'desc': 'starting sample number',
        }
        # Setup Apparatus
        self.apparatus.createAppEntry(
            ['information', 'ProcedureData', self.name, 'original_alignments']
        )

    def Plan(self):
        # Renaming useful pieces of information
        tray = self.requirements['tray']['value']
        procedure = self.requirements['procedure']['value']
        start_count = self.requirements['start_count']['value']

        # Retrieving necessary device names

        # Retrieving information from apparatus

        # Getting necessary eprocs

        # Assign apparatus addresses to procedures

        # Doing stuff

        # Do experiments
        for i,position in enumerate(tray):
            self.Report(position['sample'] + ' in progress.')
            samplename = self.apparatus.getValue(['information','ProcedureData',self.name,'samplename']).split('_')[0]
            self.apparatus.setValue(['information','ProcedureData',self.name,'samplename'], samplename+"_sample"+str(i+start_count))
            procedure.Do({'samplename': position['sample']})
            position['used'] = True
            