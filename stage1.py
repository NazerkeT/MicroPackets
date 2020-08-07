# Stage 1 of the heuristic algorithm
# Stage 1 - Critical path extraction routine with basic ASAP, ALAP
# ===> denotes to possible mistakes/improvements

import re

class Scheduler:
    def __init__(self, graph):
        self.graph = graph
        self.asap_labels = []
        self.alap_labels = []
    
    def findPreds(self, node):
        return self.graph[node]
    
    def findSuccs(self, node):
        if not node.conn:
            return None
        return node.conn

    def all_nodes_sched(self, preds, labels, peAssigned, cp):
        if peAssigned:
            inp_are_letters = all([True if pred.sched is 0 else False for pred in preds ])
            if inp_are_letters:
                return True
            
            isPredSched=all([True if (pred.sched is 0) or (pred in cp and pred.sched) or (pred not in cp) 
                            else False for pred in preds])

            return isPredSched
            
        for pred in preds:
            # print('Function  All Nodes Sched, pred ', pred.name)
            if labels[list(self.graph).index(pred)] is 0:
                return False

        if not preds:
            return False

        return True
    
    def max(self, preds, labels, peAssigned, cp):
        max = -1
        for pred in preds:
            if not peAssigned:
                max = labels[list(self.graph).index(pred)] if labels[list(self.graph).index(pred)] > max else max
            else:
                # pred.sched=0 denotes input, pred.sched=None unscheduled node
                if pred.sched is 0:
                    psblStep = compDistance(peAssigned, pred.alloc) 
                elif pred in cp:
                    psblStep = pred.sched
                elif pred not in cp and pred.sched and pred.alloc:
                    psblStep = pred.sched+compDistance(peAssigned, pred.alloc)
                else:
                    psblStep = -1

                max = psblStep if psblStep > max else max

        return max

    def min(self, preds, labels, T):
        min = T
        for pred in preds:
            if pred:
                min = labels[list(self.graph).index(pred)] if labels[list(self.graph).index(pred)] < min else min

        return min

    def assignMobility(self):
        for i, node in enumerate(list(self.graph)):
            node.mblty=self.alap_labels[i] - self.asap_labels[i]

    # Generalised scheduling algorithm for asap, alap modes and PE allocation
    def schedule(self, mode, T=None, peAssigned=None, cp=None):
        # Clear before looping again
        if peAssigned:
            for node in cp:
                node.sched = None

        labels = []
        orderedVertices = cp if peAssigned else list(self.graph)
        vertices = set(orderedVertices)
        for node in orderedVertices:
            if mode is 'asap':
                flagged = self.findPreds(node)
            else:
                flagged = self.findSuccs(node)

            if not peAssigned and not flagged:
                if mode is 'alap':
                    labels.append(T)
                else:
                    labels.append(1)

                vertices = vertices - {node}
            elif not peAssigned and flagged:
                labels.append(0)

            if peAssigned:
                distFromInps = [compDistance(peAssigned, pred.alloc) for pred in flagged if pred.sched is 0]
                if len(distFromInps) == 2:
                    # Two inputs from other pes cant be transferred at the same time
                    if 0 not in distFromInps:
                        labels.append(sum(distFromInps))
                        node.sched = sum(distFromInps)
                    else:
                        labels.append(max(distFromInps) + 1)
                        node.sched = max(distFromInps) + 1

                    vertices = vertices - {node}  
                else:
                    labels.append(0)     

        while vertices:
            for node in vertices:
                if mode is 'asap':
                    temp = self.findPreds(node)
                elif mode is 'alap':
                    temp = self.findSuccs(node)
                # print('\nFor node ', node.name, ' Preds are: ', temp,[t.name for t in temp])
                if self.all_nodes_sched(temp, labels, peAssigned, cp):
                    if mode is 'asap':
                        labels[orderedVertices.index(node)] = self.max(temp, labels, peAssigned, cp) + 1
                    else:
                        labels[orderedVertices.index(node)] = self.min(temp, labels, T) - 1  

                    if peAssigned:
                        node.sched = labels[orderedVertices.index(node)]

                    vertices = vertices - {node}

        if mode is 'asap':
            self.asap_labels = labels
        else:
            self.alap_labels = labels
            self.assignMobility()

        if not peAssigned:
            print('Labels for mode {}: '.format(mode.upper()), labels)
        
        return labels

class CPExtractor:
    def __init__(self, graph):
        self.graph = graph

    def extract(self):
        longestPathLen = 0
        longestPath = 0

        def caller(pointer,path=[]):
            preds = [node for node in self.graph[pointer] if not node.visited and (not re.search(r'[a-zA-Z]',node.name)  or node.op_type == 'Write')]
            if not preds:
                return path

            if len(preds) is 1:
                path.append(preds[0])
                return caller(preds[0], path)
            elif preds[0].mblty == preds[1].mblty:
                arrForAltCp = []
                for i in [0, 1]:
                    if not re.search(r'[a-zA-Z]', preds[i].name):
                        arrForAltCp.append(caller(preds[i], path+[preds[i]]))
                if len(arrForAltCp) is 2:
                    path = arrForAltCp[0] if len(arrForAltCp[0]) >= len(arrForAltCp[1]) else arrForAltCp[1]
                elif len(arrForAltCp) is 1:
                    path = arrForAltCp[0]

                return path
            else:
                temp = preds[0] if preds[0].mblty < preds[1].mblty else preds[1]
                path.append(temp)
                return caller(temp, path)

            return path

        starting_vertices = [vertex for vertex in list(self.graph) if (not vertex.conn and vertex.visited is None)]
        # If there is only one output node, then next time start searching for cps from nodes that connected to previous cp
        if not starting_vertices:
            starting_vertices = []
            starting_vertices.append([vertex for vertex in list(self.graph) for conn in vertex.conn
                                        if (not re.search(r'[a-zA-Z]',vertex.name) and not vertex.visited and conn.visited)])
            starting_vertices = max(starting_vertices,key = len)
            dump=[vertex.name for vertex in starting_vertices]
            print('Searching for other cps with nodes ', dump)

        # Call cp finder caller() routine
        for vertex in starting_vertices:
            path=caller(vertex, [vertex])
            longestPathLen, longestPath = (len(path), path) if len(path) > longestPathLen else (longestPathLen, longestPath)

        if longestPath:
            for node in longestPath:
                node.visited = 1
            
        return longestPath

def compDistance(coord1,coord2):
    return abs(coord2[0] - coord1[0]) + abs(coord2[1] - coord1[1])

