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

from functions import *

class Rescheduler:
    def __init__(self, w, h, clock_limit, verbose):
        # --------INPUT---------
        # Graph is subject to change, but other props will be saved as part of the structure
        self.graph = None  
        # Track MCLM addresses
        self.inputs_by_pes = {}      
        # Track repeated inputs by PEs  
        self.mult_inputs_by_pes = {}     
        self.w = w
        self.h = h
        # Clock limit for CCM1
        self.clock_limit = clock_limit 
        # If true avoid detailed prints
        self.verbose = verbose         

        # --------OPERATIONAL---------
        # Create dictionary to keep track of scheds by PE coords
        self.marker = {}
        coords = [ (x, y) for x in range(0, self.w) for y in range(0, self.h)]
        
        # Consruct marker for each coord and 
        # (0)CCM1, (1)CCM2, (2)CCM4, (3)CCM3+5+6, (4)Node Router respectively
        # This is the list of scheduled busy steps
        for coord in coords:
            self.marker.update({coord : [ [], [], [], [], [] ]})

        # Flag for immediate transmission
        self.rightaway = False
        # --------OUTPUT---------
        # Create dictionary for saving node and router scheds
        self.node_scheds = {}
        # Add [from, to] form routing addresses 
        self.router_scheds = {}

    def putNewGraph(self, graph, inputs_by_pes, mult_inputs_by_pes):
        self.graph = graph
        self.rightaway = False
        for key, value in inputs_by_pes.items():
            updateDict(self.inputs_by_pes, key, value, "inp")

        for key, value in mult_inputs_by_pes.items():
            updateDict(self.mult_inputs_by_pes, key, value, "inp")            

    def reschedule(self, throughput=1):
        
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
        # ===> Need to improve application for throughput of 2 later
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

            # Clarify whether node should wait for pred which lies in same PE for reg access
             

            for i, pred in enumerate(self.graph[node]):
                print('     Pred {} entered: '.format(i+1), pred.name)
                first_step[i] = pred.sched + 1
                last_step[i] = pred.sched + 1
                
                # Check for input presence and receive inputs to MCLM and DPRs
                if pred.name not in self.inputs_by_pes[node.alloc] and node.notif[i] is 0:
                    print('     Check for pred "{}" =====> in'.format(pred.name), pred.alloc, self.inputs_by_pes[pred.alloc])

                    walked_coords = self.walkedCoords(node.alloc, pred.alloc)
                    # Check scheds for availability, move down if it is not and send data
                    first_step[i], last_step[i] = self.send(walked_coords, first_step[i], last_step[i], pred.name)
                    # Send data from MCLM to gate router
                    asked_data_addr = self.inputs_by_pes[pred.alloc].index(pred.name)
                    updateDict(self.node_scheds, first_step[i], [pred.alloc, ['CCM1', first_step[i], asked_data_addr, 'DPR']])
                    self.updateMarker(pred.alloc, first_step[i], 0)
                    updateDict(self.node_scheds, first_step[i] + 1, [pred.alloc, ['CCM3', walked_coords[1]]])
                    self.updateMarker(pred.alloc, first_step[i] + 1, 3)

                    # ===> Add CCM6
                    updateDict(self.node_scheds, first_step[i] + 2, [pred.alloc, ['CCM6', walked_coords[1]]])
                    self.updateMarker(pred.alloc, first_step[i] + 2, 3)

                    print('     1.0 Inputs are send from pred at step ', first_step[i] + 2)

                    # Receive inputs from gate router to MCLM if this input will be repeated for this PE
                    # Else put input directly to DPR
                    # If both are from outside use both DPRs, else always use second DPR for outside/MCLM input, first DPR is for arithmetic op input
                    if pred.name in self.mult_inputs_by_pes[node.alloc]:
                        updateDict(self.node_scheds, last_step[i] - 1, [node.alloc, ['CCM6', 'DPR3']])
                        self.updateMarker(node.alloc, last_step[i] - 1, 3)
                        updateDict(self.node_scheds, last_step[i], [node.alloc, ['CCM2', 'MCLM']])
                        self.updateMarker(node.alloc, last_step[i], 1)
                        updateDict(self.inputs_by_pes, node.alloc, pred.name)
                        print('     1.1 Saving inputs to MCLM at node at step ', last_step[i])
                        last_step[i] = last_step[i] + 1
                    elif not all_inputs_outside:
                        # If one of the preds lies in the same cp, 
                        # then pred from outside pe will be placed to DPR1 instead of DPR2
                        if sum(node.notif) is 0:
                            updateDict(self.node_scheds, last_step[i] - 1, [node.alloc, ['CCM6', 'DPR2']])
                            print('     1.2 Putting inputs to DPR2 directly at node at step ', last_step[i] - 1)
                        else:
                            updateDict(self.node_scheds, last_step[i] - 1, [node.alloc, ['CCM6', 'DPR1']])
                            print('     1.2 Putting inputs to DPR1 directly at node at step ', last_step[i] - 1)
                        
                        self.updateMarker(node.alloc, last_step[i] - 1, 3)

                    else:
                        updateDict(self.node_scheds, last_step[i] - 1, [node.alloc, ['CCM6', 'DPR{}'.format(i+1)]])
                        self.updateMarker(node.alloc, last_step[i] - 1, 3)
                        print('     1.3 Putting inputs to DPR-X directly at node at step ', last_step[i] - 1)

                # If this is last node, then memory op is also last executed sched
                if node.op_type is 'Write':
                    node.sched = last_step[i]
                    print('     1.4 This is actually last node at step ', node.sched)

        #############################
        # STEP 3 - Inner operations #      
        #############################
            # Inner ops are valid for all nodes except last
            if node.op_type is not 'Write':

                all_inputs_in_mclm = all([True if pred.name in self.inputs_by_pes[node.alloc] else False for pred in self.graph[node]])
                offset_flag = 1 if last_step[0] == last_step[1] else 0
            
                for i, pred in enumerate(self.graph[node]):
                    # Load inputs from MCLM if applicable
                    if pred.name in self.inputs_by_pes[node.alloc]:
                        inp_addr = self.inputs_by_pes[node.alloc].index(pred.name)
                        offset = i if offset_flag else 0

                        last_step[i] = last_step[i] + offset

                        first_step[i], last_step[i] = self.send([node.alloc, node.alloc], last_step[i], last_step[i], pred.name)

                        updateDict(self.node_scheds, first_step[i], [node.alloc, ['CCM1', first_step[i], inp_addr, 'DPR']])
                        self.updateMarker(node.alloc, first_step[i], 0)

                        # Repeat above procedure to transfer loaded inputs to DPRs
                        reg_addr = 'DPR1' if not all_inputs_in_mclm else 'DPR{}'.format(i+1)
                        updateDict(self.node_scheds, first_step[i] + 1, [node.alloc, ['CCM3', reg_addr]])
                        self.updateMarker(node.alloc, first_step[i] + 1, 3)

                        print('     2.0 Inputs loaded from MCLM to regs at node ', reg_addr, ' at step ', first_step[i] + 1)

                        last_step[i] = last_step[i] - 1

                # Once inputs are ready, proceed to arithmetic op
                node_step = max(last_step[0], last_step[1])

                updateDict(self.node_scheds, node_step, [node.alloc, ['CCM4', node.op_type]])
                self.updateMarker(node.alloc, node_step, 2)
                print('     3.0 Arithmetic op is done at step ', node_step)
                node_step = node_step + 1
                

                if len(node.conn) is 1 and node.conn[0].op_type is not 'Write' and node.conn[0].alloc == node.alloc:
                    updateDict(self.node_scheds, node_step, [node.alloc, ['CCM5', 'DPR2']])
                    self.updateMarker(node.alloc, node_step, 3)
                    # This is last executed op for this node
                    node.sched = node_step
                    # Send notif to node that you have already sent input
                    node.conn[0].notif[self.graph[node.conn[0]].index(node)] = 1
                    print('     4.0 ---Notification is changed for', node.conn[0].name, node.conn[0].notif[self.graph[node.conn[0]].index(node)])
                    print('     4.0 Saving results to DPR2 directly at step ', node.sched)

                else:
                    # Send data to local MCLM whenever node has (a) several successors, 
                    # (b) single successor in different alloc or (c) single successor which is last result node
                    updateDict(self.node_scheds, node_step, [node.alloc, ['CCM5', 'DPR3']])
                    self.updateMarker(node.alloc, node_step, 3)
                    node_step = node_step + 1

                    updateDict(self.node_scheds, node_step, [node.alloc, ['CCM2', 'MCLM']])
                    self.updateMarker(node.alloc, node_step, 1)
                    updateDict(self.inputs_by_pes, node.alloc, node.name)

                    # Additional step is to ensure a safe interval between subsequent write read ops in MCLM
                    node.sched = node_step +1 

                    print('     4.2 Saving results to own MCLM at step ', node.sched)

                print('    ', node.alloc, '--->', self.marker[node.alloc])


    def send(self, walked_coords, first_step, last_step, pred_name):
        not_ready = True

        while not_ready:
            first_step, last_step, not_ready = self.checkMultSched(walked_coords, first_step, last_step, 'send', pred_name) 
                    
            if not not_ready: 
                first_step, last_step, not_ready = self.checkMultSched(walked_coords, first_step, last_step, 'route', pred_name)      
                        
            if not not_ready:
                first_step, last_step, not_ready = self.checkMultSched(walked_coords, first_step, last_step, 'save', pred_name) 

            # Check for free scheds only one iteration for right away transmission
            if self.rightaway and not_ready:
                self.rightaway = False
                return 0, 0
            elif self.rightaway and not not_ready:
                self.rightaway = False
                break
        
        # ===> Initiating constant outside the loop is not pythonic! Fix it!
        # Pred and node alloc are same no need to route
        if walked_coords[0] != walked_coords[-1]:
            k = 1
            for coord, step in zip(walked_coords, range(first_step + 3, last_step - 1)):
                self.marker[coord][4].append(step)
                if k < len(walked_coords) - 1:
                    updateDict(self.router_scheds, step, [walked_coords[1], walked_coords[k+1]])
                
                k = k + 1

        return first_step, last_step           

    def checkMultSched(self, walkedCoords, first_step, last_step, mode, pred_name):
        # ===> Codes below do not look pythonic or well structured, fix that
        # Detailed condition check various send, save and route possibilities
        if mode is 'send':
            coord = walkedCoords[0]
            iterable = [0, 3, 3] if walkedCoords[0] != walkedCoords[-1] else [0, 3]
        elif mode is 'save':
            coord = walkedCoords[-1]
            ccm_ind1 = 3

            if pred_name in self.mult_inputs_by_pes[walkedCoords[-1]] and pred_name not in self.inputs_by_pes[walkedCoords[-1]]:
                ccm_ind2 = 1
            elif pred_name in self.inputs_by_pes[walkedCoords[-1]]:
                ccm_ind1 = 2
                ccm_ind2 = 3
            else:
                ccm_ind2 = 2

            iterable = [ccm_ind1, ccm_ind2]
        else:
            coord = None
            iterable = walkedCoords if walkedCoords[0] != walkedCoords[-1] else []
        
        # Iterate to check for availability
        for i in iterable:
            if mode is 'route':
                coord = i
                ind = 4
            else:
                ind = i

            if not self.checkSingleSched(coord, last_step, ind):    
                if self.verbose: 
                    print("     ---I failed here", mode, first_step, last_step, coord, "CCM", ind)
                
                first_step = first_step + 1
                last_step = first_step
                not_ready = True
                return first_step, last_step, not_ready
            else:
                if self.verbose:
                    print("     ---Things are right", mode, first_step, last_step, coord, "CCM", ind)
                
                last_step = last_step + 1    

        not_ready = False

        if mode is 'save':
            last_step = last_step - 1

        if self.verbose:
            print("     ---I succeeded here", mode, first_step, last_step, coord)
        
        return first_step, last_step, not_ready
    
    def checkSingleSched(self, coord, last_step, ind):
        if ind is 0 and last_step >= 256:
            pass
            # ===> raise error!

        if last_step in self.marker[coord][ind]:
            return False

        return True
        
    def updateMarker(self, coord, last_step, ind):
        if last_step not in self.marker[coord][ind]:
            self.marker[coord][ind].append(last_step)

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

    def walkedCoords(self, node, pred):
        # Order is important in this case
        # Walk from pred to node
        col_step = 1 if node[1] >= pred[1] else -1
        row_step = 1 if node[0] >= pred[0] else -1

        if (node[0] == pred[0] and node[1] == pred[1]):
            return [pred, node]
        elif node[0] == pred[0]:
            coords = [(row, col) for row in [node[0]] for col in range(pred[1], node[1] + col_step, col_step)]
        elif node[1] == pred[1]:
            coords = [(row, col) for row in range(pred[0], node[0] + row_step, row_step) for col in [node[1]]]
        else:
            max_row = max(node[0], pred[0])
            
            coords = [(row,col) for row in [max_row] for col in range(pred[1], node[1] + col_step, col_step)]
            if (pred[0] > node[0]):
                coords += [(row, col) for row in range(pred[0] + row_step, node[0] + row_step, row_step) for col in [node[1]]]
            else:
                coords = [(row, col) for row in range(pred[0], node[0], row_step) for col in [pred[1]]] + coords

        print('     Walked coords ', coords)
        return  coords



