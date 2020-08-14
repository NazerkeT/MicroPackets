# Stage 3 of the heuristic algorithm
# Stage 3 - Check graph for data redundancies - Reschedule 

# ===> Use graph whenever you need general overview of graph, 
# but it is enough to send cps with preds assigned to micropacket generator
# Dont waste space

from stage1 import compDistance

class Rescheduler:
    def __init__(self, graph, cps=[]):
        self.graph          = graph
        self.cps            = cps
        self.hlsResults     = {} 
        self.inputFootprint = []

    def updateHls(self,key,value):
        if key in self.hlsResults:
            self.hlsResults[key].append(value)
        else:
            self.hlsResults.update({key : [value]})

    def reschedule(self,throughput=1):
        # STEP 0 ---> Assign visited of all nodes to 1,
        # By this time every pred has been visited anyways
        for node in self.graph:
            node.visited = 1

        # STEP 1 ---> Initial check for inputs, distances, and data redundancy
        nodes = [node for node in list(self.graph) if node.sched]
        nodes.append(nodes.pop(0))
        # Following is to save constants for data propagation
        constants = []
        
        for node in nodes:
            for pred in self.graph[node]:
                constant = pred.visited if throughput is 1 else ((pred.visited - 1) // 2) + 1
                constant += compDistance(node.alloc, pred.alloc)
                constants.append(constant)
                if node.sched < pred.sched + constant:
                    node.sched = pred.sched + constant
                    pred.visited += 1

        # STEP 2.0 ---> Main check for inputs and bypassing PEs
        # Start from shortest cps to avoid their effect on longest cp
        # That may not be the best strategy, but has been chosen for heuristic purposes

        # To keep track of shifted node_afters
        node_stack = {}  
        for cp in reversed(self.cps):
            # To keep track of already loaded inputs
            input_stack = [] 
            for node in cp:
                for pred in self.graph[node]:
                    # Repetitive inputs later will be handled by micropacket generator 
                    if pred in input_stack:
                        continue
                    else:
                        input_stack.append(pred)

                    dist = compDistance(node.alloc,pred.alloc)
                    
                    if dist is 1:
                        self.inputFootprint.append([node, pred])

                    if dist > 1:
                        walked_cps, walked_coords = self.walkedCps(self.cps,node.alloc,pred.alloc)
                        if walked_coords:
                            self.inputFootprint.append([node, pred,walked_coords])

                        # Check each cp which will visited along the way from pred to node
                        for walked_cp in walked_cps:
                            # Dont do anything if inputs are from same pe whether input is in letters or in nums
                            if len(walked_cp) is 1 and walked_cp[0].sched is 1:
                                continue
                            
                            # Count number of nodes processed before in nearby cp
                            nodes_before = 0
                            for walked_cp_node in walked_cp:
                                if (walked_cp_node.sched > 1 and walked_cp_node.sched < node.sched):
                                    nodes_before += 1

                            if nodes_before < len(walked_cp) - 1:
                                node_after = walked_cp[nodes_before + 1]
                            elif nodes_before == len(walked_cp):
                                node_after = None
                            elif nodes_before == 0:
                                node_after = walked_cp[0]
                            else:
                                node_after = walked_cp[-1]

                            # Node.sched is defined by the number of nodes scheduled before in nearby cp                            
                            node.sched = node.sched + nodes_before

                            # Put node_after to stack, to proceed after nested for loop
                            if node_after and node_after in node_stack:
                                node_stack[node_after] += 1
                            elif node_after and node_after not in node_stack:
                                node_stack.update({node_after: 1})

        # STEP 2.1 ---> Update shifted node scheds
        for node in node_stack:
            node.sched += node_stack[node]

        # STEP 3 ---> Final check
        for i, node in enumerate(nodes):
            for j, pred in enumerate(self.graph[node]):
                if node.sched < pred.sched + constants[2 * i + j]:
                    node.sched = pred.sched + constants[2 * i + j]

    def walkedCps(self,cps,node,pred):
        max_row = max(node[0],pred[0])

        col_step = 1 if pred[1] >= node[1] else -1
        row_step = 1 if pred[0] >= node[0] else -1

        if node[0] == pred[0]:
            coords = [(row, col) for row in [node[0]] for col in range(node[1], pred[1], col_step)]
        elif node[1] == pred[1]:
            coords = [(row, col) for row in range(node[0], pred[0], row_step) for col in [node[1]]]
        else:
            coords = [(row,col) for row in [max_row] for col in range(node[1], pred[1] + col_step, col_step)]
            if (node[0] >  pred[0]):
                coords += [(row, col) for row in range(node[0],pred[0],row_step) for col in [pred[1]]]
            else:
                coords = [(row, col) for row in range(node[0],pred[0],row_step) for col in [node[1]]] + coords

        walked_coords = [coord for coord in coords if (coord != node and coord != pred)]
        walked_cps = [cp for coord in coords for cp in cps if (cp[0].alloc == coord and coord != node and coord != pred)]
        print('Walked coords ', walked_coords)
        return walked_cps, walked_coords

    def prepareResults(self):
        # Assign preds to nodes 
        for node in self.graph:
            if node.sched:
                node.pred = self.graph[node]
        
        # Assign cps with bypassing information
        # Also input transfer from predecessors configured in this step too
        # [addr, step, data] information is attached 
        for inp in self.inputFootprint:
            # Configs for bypassing nodes
            if len(inp) is 3:
                for i, peAddr in enumerate(inp[2]):
                    if (i is 0):
                        sendTo = inp[0].alloc
                    else:
                        sendTo = inp[2][i-1]

                    step = inp[0].sched - (i+1)
                    data = None

                    self.updateHls(peAddr,[sendTo,step,data])    
                
                # Configs for predecessor node
                step = inp[0].sched - len(inp[2]) - 1
                self.updateHls(inp[1].alloc,[inp[2][-1],step,inp[1].name])  
            else:
                step = inp[0].sched - compDistance(inp[0].alloc, inp[1].alloc)
                self.updateHls(inp[1].alloc,[inp[0].alloc,step,inp[1].name])     


        
