# Stage 2 of the heuristic algorithm
# Stage 2 - Allocate and schedule each critical path

# It is assummed that pes are available to allocate and schedule all cps
# For now, PEs allocated as w*h square size matrice
# PE can receive only one input at a time from other PEs
# Letter denoted inputs(a-z) distributed over reg file of each pe, for now 2 inputs per 1 PE
# Distance between diagonal neibours is two PEs, any direct transfer is not assumed
# ===> denotes to possible mistakes/improvements, other comments are descriptive

from stage1 import *

class Allocator:
    def __init__(self, graph, w, h):
        self.graph = graph
        self.pemap = [[0 for x in range(w)] for y in range(h)] 
        self.inputs_by_pes = {}
        self.mult_inps = {}
        self.allocateInputs()

    # Inputs are allocated to reg file of each pe, not to input registers
    def allocateInputs(self, mode=2):
        # Create dictof inputs
        coords = [ (x, y) for x in range(0, 6) for y in range(0, 6)]
        
        for coord in coords:
            self.mult_inps.update({coord : []})
            self.inputs_by_pes.update({coord : []})

        inputs = [node for node in self.graph if not self.graph[node]]
        j = 0
        # ===> Change this piece of code later to make more pythonic
        # ===> Change these pieces of code to allocate variable number of inputs per pe
        # But 2 inputs per pe seems optimal option considering throughput of 1 or 2
        if mode is 2:
            #  Code for 2 inputs per PE
            for i in range(len(inputs)//2+1):
                i = (0, i) if i < 5 else (i//5, i%5)
                if j < len(inputs):                
                    inputs[j].sched, inputs[j].alloc = 0, i
                    updateDict(self.inputs_by_pes, i, inputs[j].name)
                if j+1 < len(inputs):
                    inputs[j+1].sched, inputs[j+1].alloc = 0, i
                    updateDict(self.inputs_by_pes, i, inputs[j+1].name)

                j = j + 2

        else:
        # Code for 1 input per PE
            for i,inp in enumerate(inputs):
                inp.sched, inp.alloc = 0, (j,i % 5)
                j = j + 1 if (i != 0 and i % 4 == 0) else j

    def summDists(self, coord, dests):
        return sum([compDistance(coord, dest[0]) * dest[1] for dest in dests])

    def neighborsOfCell(self, x, y, step):
        w = 5
        h = 5
        neighbors = [(nx, ny) for nx in range(x-step, x+step+1) for ny in range(y-step, y+step+1) 
                                if(-1 < x < w and -1 < y < h and (nx != x or ny != y) and (-1 < nx < w) 
                                and (-1 < ny < h) and ((abs(x - nx) >= step) or (abs(y - ny) >= step)))]

        neighbors.sort(key = lambda coord: compDistance((x, y), coord))           
        return neighbors

    def criticalSched(self, inputs):
        # Start searching for other most suitable and closest coords by steps of 8 
        # neighbours(both direct and diagonal nbors)
        if len(inputs) is 1:
            step = 1
            indices = self.neighborsOfCell(inputs[0][0][0], inputs[0][0][1], step)
            while indices:
                ind = indices.pop(0)
                if not self.pemap[ind[0]][ind[1]]:
                    return [(ind, inputs[0][1] * compDistance(ind, inputs[0][0]))]
                
                if not indices:
                    step = step + 1
                    indices = self.neighborsOfCell(inputs[0][0][0], inputs[0][0][1], step)

        step = 1
        indices = self.findPsbleDests(inputs, step)
        while not indices:
            step = step + 1
            indices = self.findPsbleDests(inputs, step)

        return indices

    def findPsbleDests(self, inputAllocs, step=0):
        # step 0 for searching inside, step>0 for searching outside neighbours
        rowColRange = []
        for i in range(0, 2):
            inds = [inp[0][i] for inp in inputAllocs]
            min_ind = min(inds) - step if min(inds) - step >= 0 else 0
            max_ind = max(inds) + step if max(inds) + step < len(self.pemap) else len(self.pemap) - 1
            rowColRange.append((min_ind, max_ind)) 
            rowColRange[i] = [rowColRange[i][0]] if rowColRange[i][0] == rowColRange[i][1] else list(range(rowColRange[i][0], rowColRange[i][1] + 1))
        
        # Permute all pe addrs
        if not step:
            addrs = [(x,y) for x in rowColRange[0] for y in rowColRange[1]]
        else:
            addrs = [(x,y) for x in [min(rowColRange[0]), max(rowColRange[0])] for y in rowColRange[1]]
            addrs = addrs + [(x,y) for x in rowColRange[0] for y in [min(rowColRange[1]), max(rowColRange[1])]]
        
        # Calculate sum of distances for each permutted pe
        destinations = [(addr, self.summDists(addr,inputAllocs)) for addr in addrs if not self.pemap[addr[0]][addr[1]]]
        return destinations

    def checkForRepetitions(self, inputs, outputs, names=False):
        for inp in inputs:   
            if inp in outputs and (outputs[inp] + 1) <= 2:
                outputs[inp] = outputs[inp] + 1
                if names:
                    updateDict(self.mult_inps, inp.alloc, inp.name)
            elif inp in outputs and (outputs[inp] + 1) > 2:
                continue
            else:
                outputs.update({inp : 1})

        return outputs

    def findMinPath(self,cp):
        inputsUnsorted = [pred.alloc for node in cp for pred in self.graph[node] if pred.alloc]
        namesUnsorted = [pred for node in cp for pred in self.graph[node]]

        print('   Inputs & Coords:')
        for node in cp:
            for pred in self.graph[node]:
                print('    ', node.name,pred.name, pred.alloc)

        print('   Pre inputs:', inputsUnsorted)
        inputAllocs = {}
        mult_inputs = {}

        # Check for repeated coords
        inputAllocs = self.checkForRepetitions(inputsUnsorted, inputAllocs)

        # Now # Check for repeated inputs
        mult_inputs = self.checkForRepetitions(namesUnsorted, mult_inputs, names=True)

        inputAllocs = [[key, value] for (key, value) in inputAllocs.items()]
        print('   \n   Inputs ', inputAllocs)

        # Find valid range of cells for pe search in terms of row, col inds of inputs
        destinations = self.findPsbleDests(inputAllocs)

        if not destinations:
            destinations = self.criticalSched(inputAllocs)
        
        closest_dest = min(destinations, key = lambda x: x[1])
        destinations = [dest[0] for dest in destinations if closest_dest[1] == dest[1]]
        
        print('   All psbl destinations: ', destinations)
        print('   Closest pe coord: ', destinations[0])
        
        return destinations

    def allocateCp(self, cp, w, h, scheduler):
        if not cp:
            return

        cp.reverse()
        
        # STEP 1 ---> Search for min path
        pe_options = self.findMinPath(cp)

        # STEP 2 ---> Schedule with respect to parents,change pemap values
        # STEP 3 ---> Reallocate if more than one min path PEs exist

        allPsblScheds = [scheduler.schedule('asap', None, pe, cp) for pe in pe_options]
        shortest_sched = min(allPsblScheds, key = max)
        min_dist_pe = pe_options[allPsblScheds.index(shortest_sched)]
        self.pemap[min_dist_pe[0]][min_dist_pe[1]] = 1
        for node, sched_step in zip(cp, shortest_sched):
            node.alloc = min_dist_pe
            node.sched = sched_step

        print('   All schedules generated: ', allPsblScheds)
        print('   Final closest pe coord and schedule ', min_dist_pe, shortest_sched)
        return min_dist_pe, shortest_sched

def printDict(dictry):
    for key, value in dictry.items():
        print(key, ' ---> ', value)
   
def updateDict(dict_,key,value):
    if key in dict_:
        dict_[key].append(value)
    else:
        dict_.update({key : [value]})
