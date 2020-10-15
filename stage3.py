# Stage 3 of the heuristic algorithm
# Stage 3 - Check graph for data redundancies - Reschedule 

# Assumption 1: Once initial steps of target PE is free, other scheds are also assummed to be free
# Assumption 2: Commands are given in continuous manner without gaps
# This is because nodes are rescheduled in levelled manner

# Node sched changed to last step only!
# Steps exist for: 
# - CCM1 - putting input to MCLM 
# - tranfer data from MCLM to dprs 
# - arithmetic op 
# - CCM2 - saving op result to MCLM  
# - tranfer data from MCLM to other PEs
# - route info as bypassing PE(independent)
# - decide on whether to forward directly or by MCLM!

# ===> Use graph whenever you need general overview of graph, 

from stage1 import compDistance

class Rescheduler:
    def __init__(self, graph):
        self.graph = graph
        # Create dictionary to keep track of scheds by PE coords
        self.marker = {}
        # Track MCLM addresses  
        self.inputs_by_pes = {}
        # Track repeated inputs by PEs  
        self.mult_inputs_by_pes = {}
        # Create dictionary for saving node and router scheds
        self.node_scheds = {}
        # Add [from, to] form routing addresses 
        self.router_scheds = {}
        # Flag for immediate transmission
        self.rightaway = False
        self.all_inputs_outside = False

    def reschedule(self,throughput=1):
        #############################
        # STEP 0 - Data Preparation #
        #############################
        # Assign visited of all nodes to 1
        for node in self.graph:
            node.visited = 1

        ##########################
        # STEP 1 - Initial check #
        ##########################
        # Initial check for inputs, distances, and data redundancy
        nodes = [node for node in list(self.graph) if node.sched]
        nodes.append(nodes.pop(0))

        for node in nodes:
            for pred in self.graph[node]:
                constant = pred.visited if throughput is 1 else ((pred.visited - 1) // 2) + 1
                constant += compDistance(node.alloc, pred.alloc)
                if node.sched < pred.sched + constant:
                    node.sched = pred.sched + constant
                    pred.visited += 1
        
        #######################
        # STEP 2 - Free paths #
        #######################
        # Establish free path from pred to node
        # Load inputs where necessary

        # Initiate marker for PE scheds and Inputs by PEs
        # ===> Avoid hardcore PE 5*5 matrix definition, use variables instead
        coords = [ (x, y) for x in range(0, 6) for y in range(0, 6)]
        
        for coord in coords:
            self.marker.update({coord : []})
            # ===> This already should be given by stage2!
            # self.inputs_by_pes.update({coord : []})
        
        # Check for inputs and bypassing PEs
        levelled_graph = self.bfs(nodes.pop()).reverse()

        for node in levelled_graph:
            first_step = [0, 0]
            last_step = [0, 0]
            pred_addr = [-1, -1]
            control_by_stg = []

            # Denote whether both inputs are from different PEs
            self.all_inputs_outside = all([True if pred.alloc != node.alloc and pred.name not in self.mult_inputs_by_pes[node.coord] 
                                        else False for pred in node.pred]) 

            for pred, i in enumerate(node.pred):
                first_step[i] = pred.sched + 1
                last_step[i] = pred.sched + 1
                
                # Check for input presence and receive inputs to MCLM and DPRs
                if pred.name not in self.inputs_by_pes[node.alloc]:
                    walked_coords = self.walkedCoords(node.alloc, pred.alloc)
                    # Check scheds for availability, move down if it is not and send data
                    first_step[i], last_step[i] = self.send(walked_coords, first_step[i], last_step[i])
                    # Send data from MCLM to gate router
                    asked_data_addr = self.inputs_by_pes[pred.alloc].index(pred.name)
                    # ===> Can we do following addressing?
                    # ===> Do we need to follow consistency here?
                    updateDict(self.node_scheds, first_step[i], [pred.alloc, ['CCM1', 1, asked_data_addr, walked_coords[1]], ['CCM3', walked_coords[1]]])
                                    
                    # Receive inputs from gate router to MCLM if this input will be repeated for this PE
                    # Else put input directly to DPR
                    # If both are from outside use both DPRs, else always use second DPR for outside/MCLM input, first DPR is for arithmetic op input
                    if pred.name in self.mult_inputs_by_pes[node.coord]:
                        updateDict(self.node_scheds, last_step[i] - 1, [node.alloc, ['CCM6', 'DPR4'], ['CCM2', 'MCLM']])
                        updateDict(self.inputs_by_pes, node.alloc, pred.name)
                        last_step[i] = last_step[i] + 1
                    elif not self.all_inputs_outside:
                        updateDict(self.node_scheds, last_step[i] - 1, [node.alloc, ['CCM6', 'DPR3']])
                    else:
                        updateDict(self.node_scheds, last_step[i] - 1, [node.alloc, ['CCM6', 'DPR{}'.format(i+1)]])

        #############################
        # STEP 3 - Inner operations #
        #############################

            all_inputs_in_mclm = all([True if pred.name in self.inputs_by_pes[node.alloc] else False for pred in node.pred])

            for pred, i in enumerate(node.pred):
                # Load inputs from MCLM if applicable
                if pred.name in self.inputs_by_pes[node.alloc]:
                    inp_addr = self.inputs_by_pes[node.alloc].index(pred.name)
                    diff = self.nextFreeSched(node.coord, last_step[i]) - last_step[i]
                    updateDict(self.node_scheds, last_step[i] + diff, [node.alloc, ['CCM1', 1, inp_addr, node.alloc]])
                    self.updateMarker(node.alloc, last_step[i] + diff)
                    last_step[i] = last_step[i] + diff + 1
                    
                    # Repeat above procedure to transfer loaded inputs to DPRs
                    reg_addr = 'DPR3' if not all_inputs_in_mclm else 'DPR{}'.format(i+1)
                    diff = self.nextFreeSched(node.coord, last_step[i]) - last_step[i]
                    updateDict(self.node_scheds, last_step[i] + diff, [node.alloc, ['CCM3', reg_addr]])
                    self.updateMarker(node.alloc, last_step[i] + diff)
                    last_step = last_step + diff + 1

            # Once inputs are ready, proceed to arithmetic op
            node_step = max(last_step[0], last_step[1])

            diff = self.nextFreeSched(node.coord, node_step) - node_step
            updateDict(self.node_scheds, node_step + diff, [node.alloc, ['CCM4', node.op_type]])
            self.updateMarker(node.alloc, node_step + diff)
            node_step = node_step + diff + 1
            
            # Redirect arithmetic op results to DPR2 always
            diff = self.nextFreeSched(node.coord, node_step) - node_step
            updateDict(self.node_scheds, node_step + diff, [node.alloc, ['CCM5', 'DPR2']])
            self.updateMarker(node.alloc, node_step + diff)
            node_step = node_step + diff + 1

            # Send op results to single other succs, so that they will receive input to MCLM directly
            # If multiple succs, then save op result to MCLM
            if len(node.conn) == 2:
                walked_coords = self.walkedCoords(node.conn[-1].alloc, node.alloc)
                self.rightaway = True
                first_step, last_step = self.send(walked_coords, node_step, node_step, 1)
                if len(walked_coords) is 1:
                    addr = walked_coords[0]
                elif len(walked_coords) is 2:
                    addr = walked_coords[-1]
                else:
                    addr = walked_coords[1]

                # Send data from this PE
                updateDict(self.node_scheds, first_step, [node.alloc, ['CCM5', addr]])
                node.sched = first_step

                # Receive data at denoted second succ
                updateDict(self.node_scheds, last_step[i] - 1, [walked_coords[-1].alloc, ['CCM6', 'DPR4'], ['CCM2', 'MCLM']])
                updateDict(self.inputs_by_pes, walked_coords[-1].alloc, node.name)  
                
            elif len(node.conn) > 2:
                # Send data to local MCLM
                diff = self.nextFreeSched(node.coord, node_step) - node_step
                updateDict(self.node_scheds, node_step + diff, [node.alloc, ['CCM5', 'DPR4']])
                node_step = node_step + diff + 1

                diff = self.nextFreeSched(node.coord, node_step) - node_step
                updateDict(self.node_scheds, node_step + diff, [node.alloc, ['CCM3', 'MCLM']])
                self.updateMarker(node.alloc, node_step + diff)
                updateDict(self.inputs_by_pes, node.alloc, node.name)
           

    def send(self, walked_coords, first_step, last_step, offset=0):
        not_ready = True
        pred_alloc = walked_coords[0]

        while not_ready:
            first_step, last_step, not_ready = self.checkMultSched(walked_coords, first_step, last_step, mode = 'send') 
                    
            if not not_ready: 
                first_step, last_step, not_ready = self.checkMultSched(walked_coords, first_step, last_step, mode = 'route')      
                        
            if not not_ready:
                first_step, last_step, not_ready = self.checkMultSched(walked_coords, first_step, last_step, mode = 'save') 

            # Check for free scheds only one iteration for right away transmission
            if self.rightaway and not_ready:
                self.rightaway = False
                return 0, 0
            elif self.rightaway and not not_ready:
                self.rightaway = False
                break
            
        # Mark scheds and routers as busy    
        # Offset is for sending data from op node results directly, instead of MCLM      
        for step in range(first_step, first_step + 1 - offset):
            self.updateMarker(pred_alloc, step - 1) 

        for step in range(last_step - 1, last_step + 1):
            self.updateMarker(walked_coords[-1], step - 1) 

        for coord, step, k in enumerate(zip(walked_coords, range(first_step + 2, last_step - 1))):
            self.marker[coord][step - 1] = 1
            if k < len(walked_coords) - 1:
                updateDict(self.router_scheds, step, [coord, walked_coords[k+1]])

        return first_step, last_step           

    def checkMultSched(self, walkedCoords, first_step, last_step, mode = None):
        if mode is 'send':
            coord = walkedCoords[0].alloc
            iterable = range(first_step, first_step + 2)
        elif mode is 'save':
            coord = walkedCoords[-1].alloc
            iterable = range(last_step, last_step + 2)
        else:
            coord = None
            iterable = walkedCoords[1:-1]

        for i in iterable:
            if mode is 'route':
                coord = walkedCoords[i]

            if self.checkSingleSched(coord, last_step):               
                last_step = last_step + 1
            else:
                first_step = last_step + 1
                last_step = last_step + 1
                not_ready = True
                return first_step, last_step, not_ready

        not_ready = False

        return first_step, last_step, not_ready
    
    def checkSingleSched(self, coord, last_step):
        if (len(self.marker[coord]) > last_step and self.marker[coord][last_step - 1] is 0) or (len(self.marker[coord]) <= last_step):
            if len(self.marker[coord]) <= last_step:
                self.marker[coord] = self.marker[coord] + [0 for k in range(last_step + 1 - len(self.marker[coord]))]

            return True
        
        return False

    def nextFreeSched(self, coord, pointer):
        while not self.checkSingleSched(coord, pointer):
            pointer = pointer + 2

        return pointer

    def updateMarker(self, coord, last_step):
        if len(self.marker[coord]) <= last_step:
            self.marker[coord] = self.marker[coord] + [0 for k in range(last_step + 1 - len(self.marker[coord]))]
        
        self.marker[coord][last_step - 1] = 1

    def bfs(self, start):
        visited, queue = set(), [start]

        while queue:
            vertex = queue.pop(0)
            if vertex not in visited:
                visited.add(vertex)
                temp_arr = self.graph[vertex]
                # Check for cycle and common predecessors
                for node in temp_arr:
                    if node in visited and node.sched > vertex.sched:
                        temp_arr.remove(node)
                    elif node in visited and node.sched < vertex.sched:
                        visited.remove(node)

                queue.extend(temp_arr)

        return list(visited)

    def walkedCoords(self,node,pred):

        col_step = 1 if pred[1] >= node[1] else -1
        row_step = 1 if pred[0] >= node[0] else -1

        if (node[0] == pred[0] and node[1] == pred[1]):
            return []
        elif node[0] == pred[0]:
            coords = [(row, col) for row in [node[0]] for col in range(node[1], pred[1], col_step)]
        elif node[1] == pred[1]:
            coords = [(row, col) for row in range(node[0], pred[0], row_step) for col in [node[1]]]
        else:
            max_row = max(node[0],pred[0])
            coords = [(row,col) for row in [max_row] for col in range(node[1], pred[1] + col_step, col_step)]
            # Order is important in this case
            if (node[0] > pred[0]):
                coords += [(row, col) for row in range(node[0],pred[0],row_step) for col in [pred[1]]]
            else:
                coords = [(row, col) for row in range(node[0],pred[0],row_step) for col in [node[1]]] + coords

        # ===> Later the day change reverse to appr walked_coords implementation
        # Start walk from pred!
        walked_coords = [coord for coord in coords].reverse()
        print('Walked coords ', walked_coords)
        return  walked_coords

def updateDict(dict_,key,value):
    if key in dict_:
        dict_[key].append(value)
    else:
        dict_.update({key : [value]})
