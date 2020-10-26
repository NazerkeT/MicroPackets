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
    def __init__(self, graph, inputs_by_pes, mult_inputs_by_pes):
        # --------INPUT---------
        self.graph = graph
        # Track MCLM addresses  
        self.inputs_by_pes = inputs_by_pes
        # Track repeated inputs by PEs  
        self.mult_inputs_by_pes = mult_inputs_by_pes
        # --------OPERATIONAL---------
        # Create dictionary to keep track of scheds by PE coords
        self.marker = {}
        # Flag for immediate transmission
        self.rightaway = False
        # --------OUTPUT---------
        # Create dictionary for saving node and router scheds
        self.node_scheds = {}
        # Add [from, to] form routing addresses 
        self.router_scheds = {}

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
        # Node list without inputs
        nodes = [node for node in list(self.graph) if node.sched]
        # Last summing node
        nodes.append(nodes.pop(0))

        # Initial check for inputs, distances, and data redundancy
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
        
        # Check for inputs and bypassing PEs
        levelled_graph = reversed(self.bfs(nodes[-1]))

        print('\n\nRESCHEDULING')
        for node in levelled_graph:
            print('######', node.name)
            first_step = [0, 0]
            last_step = [0, 0]

            # Denote whether both inputs are from different PEs
            all_inputs_outside = all([True if pred.alloc != node.alloc and pred.name not in self.mult_inputs_by_pes[node.alloc] 
                                        else False for pred in self.graph[node]]) 

            for i, pred in enumerate(self.graph[node]):
                print('     Pred {} entered: '.format(i+1), pred.name)
                first_step[i] = pred.sched + 1
                last_step[i] = pred.sched + 1
                
                # Check for input presence and receive inputs to MCLM and DPRs
                if pred.name not in self.inputs_by_pes[node.alloc] and node.notif[i] is 0:
                    walked_coords = self.walkedCoords(node.alloc, pred.alloc)
                    # Check scheds for availability, move down if it is not and send data
                    first_step[i], last_step[i] = self.send(walked_coords, first_step[i], last_step[i])
                    # Send data from MCLM to gate router
                    print('Check for pred=====>', pred.name, pred.alloc, self.inputs_by_pes[pred.alloc])
                    asked_data_addr = self.inputs_by_pes[pred.alloc].index(pred.name)
                    updateDict(self.node_scheds, first_step[i], [pred.alloc, ['CCM1', 1, asked_data_addr, walked_coords[1]]])
                    updateDict(self.node_scheds, first_step[i] + 1, [pred.alloc, ['CCM3', walked_coords[1]]])
                    print('     1.0 Inputs are send from pred')
                    # Receive inputs from gate router to MCLM if this input will be repeated for this PE
                    # Else put input directly to DPR
                    # If both are from outside use both DPRs, else always use second DPR for outside/MCLM input, first DPR is for arithmetic op input
                    if pred.name in self.mult_inputs_by_pes[node.alloc] or node.op_type is 'Write':
                        updateDict(self.node_scheds, last_step[i] - 1, [node.alloc, ['CCM6', 'DPR3']])
                        updateDict(self.node_scheds, last_step[i], [node.alloc, ['CCM2', 'MCLM']])
                        updateDict(self.inputs_by_pes, node.alloc, pred.name)
                        last_step[i] = last_step[i] + 1
                        print('     1.1 Saving inputs to MCLM at node')
                    elif not all_inputs_outside:
                        updateDict(self.node_scheds, last_step[i] - 1, [node.alloc, ['CCM6', 'DPR1']])
                        print('     1.1 Putting inputs to DPR1 directly at node')
                    else:
                        updateDict(self.node_scheds, last_step[i] - 1, [node.alloc, ['CCM6', 'DPR{}'.format(i+1)]])
                        print('     1.1 Putting inputs to DPR-X directly at node')

                # If this is last node, then memory op is also last executed sched
                if node.op_type is 'Write':
                    node.sched = last_step[i]
                    print('     1.1 This is actually last node')

        #############################
        # STEP 3 - Inner operations #      
        #############################
            # Inner ops are valid for all nodes except last
            if node.op_type is not 'Write':

                all_inputs_in_mclm = all([True if pred.name in self.inputs_by_pes[node.alloc] else False for pred in self.graph[node]])

                for i, pred in enumerate(self.graph[node]):
                    # Load inputs from MCLM if applicable
                    if pred.name in self.inputs_by_pes[node.alloc]:
                        inp_addr = self.inputs_by_pes[node.alloc].index(pred.name)
                        diff = self.nextFreeSched(node.alloc, last_step[i]) - last_step[i]
                        updateDict(self.node_scheds, last_step[i] + diff, [node.alloc, ['CCM1', 1, inp_addr, node.alloc]])
                        self.updateMarker(node.alloc, last_step[i] + diff)
                        last_step[i] = last_step[i] + diff + 1

                        # Repeat above procedure to transfer loaded inputs to DPRs
                        reg_addr = 'DPR1' if not all_inputs_in_mclm else 'DPR{}'.format(i+1)
                        diff = self.nextFreeSched(node.alloc, last_step[i]) - last_step[i]
                        updateDict(self.node_scheds, last_step[i] + diff, [node.alloc, ['CCM3', reg_addr]])
                        self.updateMarker(node.alloc, last_step[i] + diff)
                        last_step[i] = last_step[i] + diff + 1

                        print('     2.0 Inputs loaded from MCLM to regs at node,', reg_addr)

                # Once inputs are ready, proceed to arithmetic op
                node_step = max(last_step[0], last_step[1])

                diff = self.nextFreeSched(node.alloc, node_step) - node_step
                updateDict(self.node_scheds, node_step + diff, [node.alloc, ['CCM4', node.op_type]])
                self.updateMarker(node.alloc, node_step + diff)
                node_step = node_step + diff + 1
                print('     3.0 Arithmetic op is done, next free step:', node_step)

                # Once op is finished, decide where to send the data  
                data_is_sent = False 
                if len(node.conn) is 1 and node.conn[0].op_type is not 'Write' and node.conn[0].alloc == node.alloc and node.conn[0].sched > node.sched:
                     # We cannot actually wait to any interrupt, things have to be steady 
                    #  ===> Think about updates!
                    diff = self.nextFreeSched(node.alloc, node_step) - node_step
                    updateDict(self.node_scheds, node_step + diff, [node.alloc, ['CCM5', 'DPR2']])
                    self.updateMarker(node.alloc, node_step + diff)
                    # This is last executed op for this node
                    node.sched = node_step + diff
                    data_is_sent = True
                    # Send notif to node that you have already sent input
                    node.conn[0].notif[self.graph[node.conn[0]].index(node)] = 1
                    print('     ---Notification is changed for', node.conn[0].name, node.conn[0].notif[self.graph[node.conn[0]].index(node)])
                    print('     4.0 Saving results to DPR2 directly', node.sched)

                elif (len(node.conn) is 1 and node.conn[0].alloc != node.alloc):
                    # Send op results to single other succ, so that they will receive input to MCLM directly
                    # If multiple succs, then save op result to MCLM 
                    walked_coords = self.walkedCoords(node.conn[0].alloc, node.alloc)
                    self.rightaway = True
                    # As long as self.send already marks self.marker, we do not modify it for this part
                    first_step, last_step = self.send(walked_coords, node_step, node_step, 1)
                    if [first_step, last_step] != [0, 0]:
                        if len(walked_coords) is 1:
                            addr = walked_coords[0]
                        elif len(walked_coords) is 2:
                            addr = walked_coords[-1]
                        else:
                            addr = walked_coords[1]

                        # Send data from this PE
                        updateDict(self.node_scheds, first_step, [node.alloc, ['CCM5', addr]])
                        # Node.sched is denoted by last executed step on node, 
                        # Other steps, on the other hand, denote next free step
                        node.sched = first_step

                        # Receive data at denoted second succ
                        updateDict(self.node_scheds, last_step - 1, [walked_coords[-1], ['CCM6', 'DPR3']])
                        updateDict(self.node_scheds, last_step - 1, [walked_coords[-1], ['CCM2', 'MCLM']])
                        updateDict(self.inputs_by_pes, walked_coords[-1], node.name)  

                        data_is_sent = True

                        print('     4.1 Sending results to  MCLM of succ', node.sched)

                        # Send notif to node that you have already sent input
                        node.conn[0].notif[self.graph[node.conn[0]].index(node)] = 1
                        print('     ---Notification is changed for', node.conn[0].name, node.conn[0].notif[self.graph[node.conn[0]].index(node)])

                if not data_is_sent:
                    # Send data to local MCLM
                    diff = self.nextFreeSched(node.alloc, node_step) - node_step
                    updateDict(self.node_scheds, node_step + diff, [node.alloc, ['CCM5', 'DPR3']])
                    node_step = node_step + diff + 1

                    diff = self.nextFreeSched(node.alloc, node_step) - node_step
                    updateDict(self.node_scheds, node_step + diff, [node.alloc, ['CCM2', 'MCLM']])
                    self.updateMarker(node.alloc, node_step + diff)
                    updateDict(self.inputs_by_pes, node.alloc, node.name)

                    node.sched = node_step + diff

                    print('     4.2 Saving results to own MCLM ', node.sched)

           

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

        # ===> Initiating constant outside the loop is not pythonic! Fix it!
        k = 0
        for coord, step in zip(walked_coords, range(first_step + 2, last_step - 1)):
            self.marker[coord][step - 1] = 1
            if k < len(walked_coords) - 1:
                updateDict(self.router_scheds, step, [coord, walked_coords[k+1]])
            
            k = k + 1

        return first_step, last_step           

    def checkMultSched(self, walkedCoords, first_step, last_step, mode = None):
        if mode is 'send':
            coord = walkedCoords[0]
            iterable = range(first_step, first_step + 2)
        elif mode is 'save':
            coord = walkedCoords[-1]
            iterable = range(last_step, last_step + 2)
        else:
            coord = None
            iterable = walkedCoords[2:-1]

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
        visited, queue = [], [start]

        while queue:
            vertex = queue.pop(0)
            if vertex not in visited and vertex.sched:
                visited.append(vertex)
                temp_arr = self.graph[vertex]
                # Check for cycle and common predecessors
                for node in temp_arr:
                    if node in visited and node.sched > vertex.sched:
                        temp_arr.remove(node)
                    elif node in visited and node.sched < vertex.sched:
                        visited.remove(node)

                queue.extend(temp_arr)

        return visited

    def walkedCoords(self,node,pred):

        col_step = 1 if pred[1] >= node[1] else -1
        row_step = 1 if pred[0] >= node[0] else -1

        if (node[0] == pred[0] and node[1] == pred[1]):
            return [(node[0], node[1])]
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
        walked_coords = [coord for coord in coords]
        walked_coords.reverse()
        print('     Walked coords ', walked_coords)
        return  walked_coords

def updateDict(dict_,key,value):
    if key in dict_:
        dict_[key].append(value)
    else:
        dict_.update({key : [value]})
