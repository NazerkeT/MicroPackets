# Stage 3 of the heuristic algorithm
# Stage 3 - Check graph for data redundancies - Reschedule 

# ===> Use graph whenever you need general overview of graph, 

from stage1 import compDistance

class Rescheduler:
    def __init__(self, graph):
        self.graph          = graph
        # Create dictionary to keep track of scheds by PE coords
        self.marker         = {}
        # Track MCLM addresses  
        self.inputs_by_pes = {}
        # Create dictionary for saving node and router scheds
        self.node_scheds = {}
        # Add [from, to] form routing addresses 
        self.router_scheds = {}

    def reschedule(self,throughput=1):
        # STEP 0 ---> Assign visited of all nodes to 1,
        # By this time every pred has been visited anyways
        for node in self.graph:
            node.visited = 1

        # STEP 1 ---> Initial check for inputs, distances, and data redundancy
        nodes = [node for node in list(self.graph) if node.sched]
        nodes.append(nodes.pop(0))

        for node in nodes:
            for pred in self.graph[node]:
                constant = pred.visited if throughput is 1 else ((pred.visited - 1) // 2) + 1
                constant += compDistance(node.alloc, pred.alloc)
                if node.sched < pred.sched + constant:
                    node.sched = pred.sched + constant
                    pred.visited += 1
       

        # STEP 2.0 ---> Main check for inputs and bypassing PEs

        # ===> Avoid hardcore PE 5*5 matrix definition, use variables instead
        coords = [ (x, y) for x in range(0, 6) for y in range(0, 6)]

        for coord in coords:
            self.marker.update({coord : []})
            self.inputs_by_pes.update({coord : []})
        
        # Check for inputs and bypassing PEs
        levelled_graph = self.bfs(nodes.pop()).reverse()

        for node in levelled_graph:
            first_step = [0, 0]
            last_step = [0, 0]
            not_ready = True

            for pred, i in enumerate(node.pred):
                
                first_step[i] = pred.sched + 1
                last_step[i] = pred.sched + 1

                if pred.name in self.inputs_by_pes[pred.alloc] or last_step[i] == first_step[i]:
                    last_step[i] = last_step[i] + 1
                    break

                walked_coords = self.walkedCoords(node.alloc, pred.alloc)

                # Check while you dont find free consequent scheds
                while walked_coords and not_ready:
                    first_step[i], last_step[i], not_ready = self.check(walked_coords, first_step[i], last_step[i], mode = 'send') 
                    
                    if not not_ready: 
                        first_step[i], last_step[i], not_ready = self.check(walked_coords, first_step[i], last_step[i], mode = 'route')      
                        
                    if not not_ready:
                        first_step[i], last_step[i], not_ready = self.check(walked_coords, first_step[i], last_step[i], mode = 'save')  
                
                if last_step[i] > first_step[i]:
                    # # Mark scheds and routers as busy          
                    for step in range(first_step[i], first_step[i] + 1):
                        self.marker[walked_coords[0]][step - 1] = 1     

                    for step in range(last_step[i] - 1, last_step[i] + 1):
                        self.marker[node.alloc][step - 1] = 1

                    for  coord, step in enumerate(walked_coords, range(first_step[i] + 2, last_step[i] - 1)):
                        self.marker[coord][step - 1] = 1
                        updateDict(self.router_scheds, step, [pred, coord])

                    # Send data from MCLM to gate router
                    asked_data_addr = self.inputs_by_pes[pred.alloc].index(pred.name)
                    # ===> Can we do following addressing?
                    updateDict(self.node_scheds, pred.sched + 1, [pred.alloc, ['CCM1', 1, asked_data_addr, walked_coords[1]], ['CCM3', walked_coords[1]]])
                    # Receive inputs from gate router to MCLM
                    updateDict(self.node_scheds, last_step[i] + 1, [node.alloc, ['CCM6', 'DPR3'], ['CCM2', 'MCLM']])
                    # Modify last_step for above clock steps
                    last_step[i] = last_step[i] + 3

            node_step = max(last_step[0], last_step[1])
            pred1_addr = self.inputs_by_pes[coord].index(node.pred[0].name)
            pred2_addr = self.inputs_by_pes[coord].index(node.pred[1].name)

            # change node sched to last step only!
            # steps exist for: 
            # - CCM1 - putting input to MCLM 
            # - tranfer data from MCLM to dprs 
            # - arithmetic op 
            # - CCM2 - saving op result to MCLM  
            # - tranfer data from MCLM to other PEs
            # - route info as bypassing PE(independent)
            
            control_by_stg = []
            control_by_stg.append(['CCM1', 1, pred1_addr, node.alloc, 1, pred2_addr, node.alloc])
            control_by_stg.append(['CCM3', 'DPR1', 'DPR2'])
            control_by_stg.append(['CCM4', node.op_type])
            control_by_stg.append(['CCM5', 'DPR3'])

            updateDict(self.node_scheds, node_step, [node, control_by_stg])

            # ===> Check last sched validity
            node.sched = node_step + 7            
            
                
    def check(self, walkedCoords, first_step, last_step, mode = None):
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

            if (len(self.marker[coord]) > last_step and self.marker[coord][last_step - 1] is 0) or (len(self.marker[coord]) <= last_step):
                if len(self.marker[coord]) <= last_step:
                    self.marker[coord] = self.marker[coord] + [0 for k in range(last_step + 1 - len(self.marker[coord]))]
                            
                last_step = last_step + 1

            else:
                first_step = last_step + 1
                last_step = last_step + 1
                not_ready = True
                return first_step, last_step, not_ready

        not_ready = False

        return first_step, last_step, not_ready

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
            if (node[0] >  pred[0]):
                coords += [(row, col) for row in range(node[0],pred[0],row_step) for col in [pred[1]]]
            else:
                coords = [(row, col) for row in range(node[0],pred[0],row_step) for col in [node[1]]] + coords

        # ===> Later the day change reverse to appr walked_coords implementation
        # Start walk from pred!
        walked_coords = [coord for coord in coords if (coord != node)].reverse()
        print('Walked coords ', walked_coords)
        return  walked_coords


def updateDict(dict_,key,value):
    if key in dict_:
        dict_[key].append(value)
    else:
        dict_.update({key : [value]})
