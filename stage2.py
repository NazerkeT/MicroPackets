# Stage 2,3 of the heuristic algorithm
# Stage 2 - Allocate and schedule each critical path
# Stage 3 - Check graph for data redundancies => reschedule 

# It is assummed that pes are available to allocate and schedule all cps
# For now, PEs allocated as w*h square size matrice
# PE can receive only one input at a time from other PEs
# Letter denoted inputs(a-z) distributed over reg file of each pe, for now 2 inputs per 1 PE
# ===> denotes to possible mistakes/improvements, other comments are descriptive

from stage1 import *

class Allocator:
    def __init__(self, graph, w, h):
        self.graph = graph
        self.pemap = [[0 for x in range(w)] for y in range(h)] 
        self.allocateInputs()

    # Inputs are allocated to reg file of each pe, not to input registers
    def allocateInputs(self):
        inputs = [node for node in self.graph if not self.graph[node]]
        j = 0
        # ===> Change this piece of code later to make more pythonic
        for i in range(len(inputs)//2+1):
            i = (0, i) if i < 5 else (i//5, i%5)
            if j < len(inputs):                
                inputs[j].sched, inputs[j].alloc = 0, i
            if j+1 < len(inputs):
                inputs[j+1].sched, inputs[j+1].alloc = 0, i

            j = j + 2

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
        destinations=[(addr, self.summDists(addr,inputAllocs)) for addr in addrs if not self.pemap[addr[0]][addr[1]]]
        return destinations

    def findMinPath(self,cp):
        inputsUnsorted = [pred.alloc for node in cp for pred in self.graph[node] if pred.alloc]
        inputAllocs = {}
        for inp in inputsUnsorted:
            if inp in inputAllocs:
                inputAllocs[inp] = inputAllocs[inp] + 1
            else:
                inputAllocs.update({inp : 1})

        inputAllocs = [[key, value] for (key, value) in inputAllocs.items()]
        print('   Inputs ', inputAllocs)

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
        
        # 1st step - search for min path
        pe_options = self.findMinPath(cp)

        # 2nd step - Schedule with respect to parents,change pemap values
        # 3rd step - Reallocate if more than one min path PEs exist

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

class Rescheduler:
    def __init__(self, graph):
        self.graph = graph

    def reschedule(self,cps=[],throughput=1):
        # Extract only op nodes from graph and put 'Write' node to the end
        nodes = [node for node in list(self.graph) if node.sched]
        nodes.append(nodes.pop(0))

        # Check for sched step redundancy
        # ===> It seems that you do some actions twice or more, fix that!
        for cp in reversed(cps):
            for node in cp:
                for pred in self.graph[node]:
                    dist = compDistance(node.alloc,pred.alloc)
                    if (node.visited is 1) and dist > 1:
                        walked_cps = self.walkedCps(cps,node.alloc,pred.alloc)
                        # Check each cp which is visited along the way from pred to node
                        for walked_cp in walked_cps:
                            # Dont do anything if inputs are from same 
                            # pe whether input is in letters or in nums
                            if len(walked_cp) is 1 and walked_cp[0].sched is 1:
                                continue
                            
                            # If throughput is 2, nothing changes
                            if throughput is 1:
                                node_before = [walked_cp_node for walked_cp_node in walked_cp if walked_cp_node.sched < node.sched]
                                node_after  = walked_cp[len(node_before)] if len(node_before) < len(walked_cp) else None
                                node_before = node_before[-1]

                                # Node.sched is defined by equal or last before sched node in nearby cp
                                # Also distance and sched of predecessor node counts too
                                if node.sched < (node_before.sched + dist - 1 + pred.sched):
                                    node.sched = node_before.sched + dist - 1 + pred.sched
                                
                                # Increment sched of same or late level node in cp, check same for succ
                                if node_after:
                                    node_after.sched = node_after.sched + 1 if not all([True if node_.alloc == node_after.alloc else False for node_ in self.graph[node_after]]) else node_after.sched
                                    for i, succ in enumerate(node_after.conn):
                                        if succ.sched <= node_after.sched:
                                            succ.sched = succ.sched + 1 +i
                                    
                                    node_after.visited += 1

                                # Increment visited of all nodes in walked cps
                                node_before.visited += 1
                                

                    if node.sched <= pred.sched + dist:
                        node.sched = pred.sched + 1 + dist

                for succ in node.conn:
                    if succ.sched <= node.sched:
                        succ.sched = node.sched + 1 + compDistance(node.alloc,succ.alloc)

    def walkedCps(self,cps,node,pred):
        min_row, max_row = min(node[0],pred[0]), max(node[0],pred[0])
        min_col, max_col = min(node[1],pred[1]), max(node[1],pred[1])
        
        if node[0] == pred[0]:
            coords = [(row, col) for row in [min_row] for col in range(min_col,max_col)]
        elif node[1] == pred[1]:
            coords = [(row, col) for row in range(min_row,max_row) for col in [max_col]]
        else:
            coords = [(row,col) for row in [max_row] for col in range(min_col,max_col+1)]
            upper_col= min(node,pred,key=lambda coord: coord[0])[1]
            coords += [(row, col) for row in range(min_row,max_row) for col in [upper_col]]

        walked_cps = [cp for coord in coords for cp in cps if (cp[0].alloc == coord and coord != node and coord != pred)]

        return walked_cps

def printDict(dictry):
    for key, value in dictry.items():
        print(key, ' ---> ', value)
   
if __name__ == "__main__":
    equation1 = 'z=(a*b+c/d)*(e+f)'
    equation2 = 'v=(((a*b*n-m+c/d+(f-g)*h)-(x+y)/z)+(w-u))+(s*t)'
    equation3 = 'v=w+((a*b*n-m+c/d+(f-g)*h)-(x+y)/z)'
    equation4 = 'z=a*b+c/d*e+f'
    equation5 = 'z=a+b+(a+b)*c+d*(e+f)+e+f'

    # Generate DFG from equation
    graph = DFGGenerator(equation5).graph.graph
    write(graph)

    scheduler = Scheduler(graph)
    asap = scheduler.schedule('asap')
    alap = scheduler.schedule('alap',max(asap))
    
    cpextractor = CPExtractor(graph)
    cp = cpextractor.extract()
    cps = [cp]
    cp_allocs = {}

    # Define map of PEs to mark which PEs are free, which are not
    # PE assignment will be reflected on node.alloc property
    w, h = 5, 5
    allocator = Allocator(graph, w, h)

    # Extract critical paths, allocate and schedule
    i = 1
    while cp:
        dump = [node.name for node in reversed(cp)]
        print('\n{}. DUMPED cp: '.format(i), dump)
        i = i + 1
        allocator.allocateCp(cp, w, h, scheduler)
        cp_allocs.update({cp[0].alloc : [(node.name, node.sched) for node in cp]})
        cp = cpextractor.extract()

        if cp:
            cps.append(cp)
    
    # Collect input allocation per PEs
    input_allocs = {node.alloc : [] for node in graph if node.sched is 0}
    for node in graph:
        for alloc in input_allocs:
            if node.sched is 0 and node.alloc == alloc:
                        input_allocs[alloc].append(node.name)

    print('\nInput allocation by PEs:')
    printDict(input_allocs)

    print('\nFinal results before rescheduling (node.name, node.sched) by PEs: ')
    printDict(cp_allocs)

    rescheduler = Rescheduler(graph)
    # Second arg indicates throughput, which is by default = 1
    rescheduler.reschedule(cps,1)

    print('\nFinal results after rescheduling (node.name, node.sched): by PEs')
    cp_allocs = {cp[0].alloc : [(node.name, node.sched) for node in cp] for cp in cps}
    printDict(cp_allocs)

    # Show PE utilization
    print('\nPE map ')
    for pe in allocator.pemap:
        print(pe)