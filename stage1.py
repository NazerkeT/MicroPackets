# Stage 1 of heuristic algorithm
# Critical path extraction routine with basic ASAP, ALAP
# ===> denotes to possible mistakes/improvements

from generator import *

class Scheduler:
    def __init__(self,graph):
        self.graph=graph
        self.asap_labels=[]
        self.alap_labels=[]
    
    def findPreds(self,node):
        return self.graph[node]
    
    def findSuccs(self,node):
        if node.conn is None:
            return None
        return [node.conn]

    def all_nodes_sched(self,preds,labels,peAssigned,cp):
        if peAssigned:
            inp_are_letters=all([True if pred.sched is 0 else False for pred in preds ])
            if inp_are_letters:
                return True
            
            isPredSched=any([True if (pred in cp) and (pred.sched) else False for pred in preds]) 
            return isPredSched
            
        for pred in preds:
            if labels[list(self.graph.keys()).index(pred)] is 0:
                return False

        if not preds:
            return False

        return True
    
    def max(self,preds,labels,peAssigned,cp):
        max=-1
        for pred in preds:
            if not peAssigned:
                max = labels[list(self.graph.keys()).index(pred)] if labels[list(self.graph.keys()).index(pred)] > max else max
            else:
                print('Info about preds at MAX function ',pred.name,pred.sched,pred.alloc)
                # pred.sched=0 denotes input, pred.sched=None unscheduled node
                if pred.sched is 0:
                    psblStep=compDistance(peAssigned,pred.alloc) 
                elif pred in cp:
                    psblStep=pred.sched
                elif pred not in cp and pred.sched and pred.alloc:
                    psblStep=pred.sched+compDistance(peAssigned,pred.alloc)
                else:
                    psblStep=-1

                max=psblStep if psblStep>max else max

        return max

    def min(self,preds,labels,T):
        min=T
        for pred in preds:
            if pred:
                min = labels[list(self.graph.keys()).index(pred)] if labels[list(self.graph.keys()).index(pred)] < min else min

        return min

    def assignMobility(self):
        for i,node in enumerate(list(self.graph.keys())):
            node.mblty=self.alap_labels[i]-self.asap_labels[i]

    # Generalised scheduling algorithm for asap, alap modes and PE allocation
    def schedule(self,mode,T=None,peAssigned=None,cp=None):
        # Clear before looping again
        if peAssigned:
            for node in cp:
                node.sched=None
        if cp:
            print('     To avod confusion ',[node.sched for node in cp])
        labels=[]
        orderedVertices=cp if peAssigned else list(self.graph.keys())
        vertices=set(orderedVertices)
        for node in orderedVertices:
            if mode is 'asap':
                flagged=self.findPreds(node)
            else:
                flagged=self.findSuccs(node)

            if not peAssigned and not flagged:
                if mode is 'alap':
                    labels.append(T)
                else:
                    labels.append(1)

                vertices=vertices-{node}
            elif not peAssigned and flagged:
                labels.append(0)

            if peAssigned:
                print('PE ASSIGNED, NODE.ALLOC ',peAssigned,flagged[0].name,flagged[0].alloc,flagged[0].sched)
                distFromInps=[compDistance(peAssigned,pred.alloc) for pred in flagged if pred.sched is 0]
                print('distFromInps ',distFromInps)
                if len(distFromInps)==2:
                    print('Actially I have entered here!')
                    # Two inputs from other pes cant be transfered at the same time
                    if 0 not in distFromInps:
                        labels.append(sum(distFromInps))
                        node.sched=sum(distFromInps)
                    else:
                        labels.append(max(distFromInps)+1)
                        node.sched=max(distFromInps)+1

                    vertices=vertices-{node}  
                else:
                    labels.append(0)     

        while vertices:
            for node in vertices:
                if mode is 'asap':
                    temp=self.findPreds(node)
                elif mode is 'alap':
                    temp=self.findSuccs(node)

                if self.all_nodes_sched(temp,labels,peAssigned,cp):
                    if mode is 'asap':
                        if peAssigned:
                            print('Node name passed ',node.name)
                        labels[orderedVertices.index(node)]=self.max(temp,labels,peAssigned,cp)+1
                    else:
                        labels[orderedVertices.index(node)]=self.min(temp,labels,T)-1  

                    if peAssigned:
                        node.sched=labels[orderedVertices.index(node)]
                        print('Node ',node.name, ' is scheduled to ',node.sched)

                    vertices=vertices-{node}

        if mode is 'asap':
            self.asap_labels=labels
        else:
            self.alap_labels=labels
            self.assignMobility()
       
        print('Labels for mode {}: '.format(mode.upper()),labels)
        return labels

class CPExtractor:
    def __init__(self,graph):
        self.graph=graph

    def extract(self):
        longestPathLen=0
        longestPath=0

        def caller(pointer,path=[]):
            if not self.graph[pointer]:
                return path
            if len(self.graph[pointer]) is 1:
                path.append(self.graph[pointer][0])
                return caller(self.graph[pointer][0],path)
            elif self.graph[pointer][0].mblty==self.graph[pointer][1].mblty:
                arrForAltCp=[]
                for i in [0,1]:
                    if not re.search(r'[a-zA-Z]',self.graph[pointer][i].name):
                        arrForAltCp.append(caller(self.graph[pointer][i],path+[self.graph[pointer][i]]))
                if len(arrForAltCp) is 2:
                    path=arrForAltCp[0] if len(arrForAltCp[0])>=len(arrForAltCp[1]) else arrForAltCp[1]
                elif len(arrForAltCp) is 1:
                    path=arrForAltCp[0]

                return path
            else:
                temp=self.graph[pointer][0] if self.graph[pointer][0].mblty<self.graph[pointer][1].mblty else self.graph[pointer][1]
                path.append(temp)
                return caller(temp,path)

            return path

        starting_vertices=[vertex for vertex in list(self.graph.keys()) if (vertex.conn is None and vertex.visited is None)]
        # If there is only one output node, then next time start searching for cps from nodes that connected to previous cp
        if not starting_vertices:
            starting_vertices=[vertex for vertex in list(self.graph.keys()) if (not re.search(r'[a-zA-Z]',vertex.name) and not vertex.visited and vertex.conn.visited)]
            dump=[vertex.name for vertex in starting_vertices]
            print('Searching for other cps with nodes ',dump)

        # Call cp finder caller() routine
        for vertex in starting_vertices:
            path=caller(vertex,[vertex])
            longestPathLen,longestPath=(len(path),path) if len(path)>longestPathLen else (longestPathLen,longestPath)

        if longestPath:
            for node in longestPath:
                node.visited=1
            
        return longestPath

def compDistance(coord1,coord2):
    return abs(coord2[0]-coord1[0])+abs(coord2[1]-coord1[1])

if __name__ == "__main__":
    equation1='z=(a*b+c/d)*(e+f)'
    equation2='v=(((a*b*n-m+c/d+(f-g)*h)-(x+y)/z)+(w-u))+(s*t)'
    equation3='v=w+((a*b*n-m+c/d+(f-g)*h)-(x+y)/z)'

    graph = DFGGenerator(equation1).graph.graph
    write(graph)

    scheduler=Scheduler(graph)
    asap=scheduler.schedule('asap')
    alap=scheduler.schedule('alap',max(asap))

    cpextractor=CPExtractor(graph)
    cps=cpextractor.extract()
    i=1
    while cps:
        dump=[node.name for node in cps]
        print('\n{}. DUMPED cps'.format(i),dump)
        i=i+1
        cps=cpextractor.extract()