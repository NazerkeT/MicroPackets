# This script generates micropacket control programs

# Common terminology:
# CPR  - Configuration Packet Receiver
# CPDA - Configuration Packet Destination Address
# DPR  - Data Packet Receiver
# DPG  - Data Packet Generator
# MCLM - MiCropacket Local Memory

# ===> The thing that you are transferring big graph and cps, 
# already duplicate items twice just because of preds, does not seem good resource 
# usage strategy. Even if it may seem not that important now, come back and avoid this!

class PacketGenerator:
    def __init__(self,graph,cps,inputFootprint):
        self.graph = graph
        self.cps = cps
        self.inputFootprint = inputFootprint
        # Dictionary to save Schedulules by PEs
        self.table = {}

        self.allocateInputs()
        self.allocateInputFootprint()
        self.writeTable()

    def allocateInputs(self):
        inputs = [node for node in self.graph if node.sched is 0]
        # 2 CPRs used for initial input placement per PE register file
        # Micropacket table entry format is the following ---> PE coord: node.sched - Valid bit - CPDA - Sub Micropacket
        # Sub Micropacket usually includes (1) packet dest addr and (2) data itself

        for inp in inputs:
            self.table.update({inp.alloc: [inp.sched, 1, 'CPR6', 'DPR3', inp.name]})
            self.table.update({inp.alloc: [inp.sched, 1, 'CPR2', 'MCLM', inp.name]})

    # ===> Check for conditions when input is literal but result of some node
    def allocateInputFootprint(self):
        inpFootprintDict = {}
        for inpInfo in self.inputFootprint:
            for i, alloc in enumerate(inpInfo[2]):
                inpFootprintDict.update({(alloc,): [inpInfo[0].sched,inpInfo[0],inpInfo[1]]})
            
    def writeTable(self):
        
        # Step 1: Place standard ops with local inputs first
        for cp in self.cps:
            for node in cp:
                for i, pred in enumerate(self.graph[node]):
                    if node.alloc == pred.alloc:
                        # Sub Micropacket format for CPR1 ---> Clock Step - Load Addr - Dest Addr
                        self.table.update({node.alloc: [node.sched, 1, 'CPR1', (i+1), (i+1),node.alloc]})
                        self.table.update({node.alloc: [node.sched, 1, 'CPR3', 'DPR{}'.format(i+1)]})
                
                self.table.update({node.alloc: [node.sched, 1, 'CPR4', node.op_type]})
                self.table.update({node.alloc: [node.sched, 1, 'CPR5','DPR2']})
                # In my understanding, it is not necessary for CA computed result to be
                # saved in MCLM, it should be directly travel to DPR2, Clarify!

        # Step 2: Now place travelling inputs
        for inpInfo in self.inputFootprint:
            for i, inp in enumerate(inpInfo[2]):
                # put node inp
                # put preed out
                # put intermed inp+out