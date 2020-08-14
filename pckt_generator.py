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
    def __init__(self,hlsResults, maxClock, tempMem):
        self.hlsResults = hlsResults
        self.maxClock   = maxClock
        # Following is to keep track of MCLMs
        self.tempMem    = tempMem 
        # Assume that inputs have been already preallocated to respective PEs
        self.generatePackets()

    def itIsNode(self, data):
        return (len(str(type(data))) >= 28) and (str(type(data))[22:-2] == 'Node')

    def extractCcm(self,peAddr,peInfo,clock):
        # 1st - load input(s) to MCLM               (PE specific, sep stage)
        # 2nd - load inputs(s) from MCLM to regs    (PE specific)
        # 3rd - arithmetic op                       (PE specific)
        # 4th - load result to the MCLM             (PE specific)
        # 5th - send info from this PE to other PE  (PE specific, sep stage)
        # From MCLM to PE router
        # 6th - route info as bypassing PE          (Router specific)
        # ===> Is automatic clock behav preserved in cases only 
        # some of the ccms are filled in?

        # CCM dictionary by mini stages
        pe_ccms     = {}
        router_ccms = {}
        stg = 1
        for arr in peInfo:
            if arr and self.itIsNode(arr[0]):
                if clock == arr[0].sched:
                    for i, pred in enumerate(arr[0].pred):
                        if pred.name not in self.tempMem[peAddr]:
                            # 1-step
                            pe_ccms.update({stg: ([1, 'CPR6', 'DPR3'])})
                            pe_ccms.update({stg: ([1, 'CPR2', 'MCLM'])})
                            self.tempMem[peAddr].append(pred.name)
                            stg += 1
                        # 2-step   
                        dataAddr = self.tempMem[peAddr].index(pred.name)     
                        pe_ccms.update({stg: [1, 'CPR1',(i+1), dataAddr, peAddr]})
                        # 4-step
                        pe_ccms.update({stg: [1, 'CPR2', 'MCLM']}) 
                        # 2-step
                        pe_ccms.update({stg: [1, 'CPR3', 'DPR{}'.format(i+1)]})
                    
                    # 3-step
                    pe_ccms.update({stg: [1, 'CPR4', arr[0].op_type]})
                    # 4-step
                    pe_ccms.update({stg: [1, 'CPR5', 'DPR3']})
                    peInfo.remove(arr)
            else:
                if arr and clock == arr[1] and arr[2]:
                    stg += 1
                    # 5-step
                    dataAddr = self.tempMem[peAddr].index(arr[2])
                    pe_ccms.update({stg: [1, 'CPR1', 1, dataAddr, arr[0]]})
                    pe_ccms.update({stg: [1, 'CPR3', arr[0]]})
                
                if arr and clock == arr[1]:
                    # 6-step
                    router_ccms.update({stg: arr[0]})
                    peInfo.remove(arr)
                                
        return pe_ccms, router_ccms         


    def generatePackets(self):        
        clock   = 1

        i = 1
        while clock <= self.maxClock:
            for peAddr, peInfo in self.hlsResults.items():
                print(i, clock, '  Key and Value ', peAddr,peInfo)
                pe_ccms, router_ccms = self.extractCcm(peAddr, peInfo, clock)
                
                print('PE CCMs')
                print(pe_ccms)
                print('Router CCMs')
                print(router_ccms)

                i += 1

            clock += 1


