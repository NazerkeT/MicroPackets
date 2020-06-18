# ASAP, ALAP scheduling

from generate import *

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

    def all_nodes_sched(self,preds,labels):
        for pred in preds:
            if labels[list(self.graph.keys()).index(pred)] is 0:
                return False

        if not preds:
            return False

        return True
    
    def max(self,preds,labels):
        max=-1
        for pred in preds:
            max = labels[list(self.graph.keys()).index(pred)] if labels[list(self.graph.keys()).index(pred)] > max else max

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

    def schedule(self,mode,T=None):
        vertices=set(list(self.graph.keys()))
        labels=[]
        for node in list(self.graph.keys()):
            if mode is 'asap':
                flag=self.findPreds(node)
            elif mode is 'alap':
                flag=self.findSuccs(node)
            else:
                 print('Error: Mode is not chosen properly') 

            if not flag:
                if mode is 'alap':
                    labels.append(T)
                else:
                    labels.append(1)
                vertices=vertices-{node}
            else:
                labels.append(0)
        
        print('Initial labels for mode {}: '.format(mode.upper()),labels)
        
        while vertices:
            for node in vertices:
                if mode is 'asap':
                    temp=self.findPreds(node)
                elif mode is 'alap':
                    temp=self.findSuccs(node)

                if self.all_nodes_sched(temp,labels):
                    if mode is 'asap':
                        labels[list(self.graph.keys()).index(node)]=self.max(temp,labels)+1
                    else:
                        labels[list(self.graph.keys()).index(node)]=self.min(temp,labels,T)-1  

                    vertices=vertices-{node}

        if mode is 'asap':
            self.asap_labels=labels
        else:
            self.alap_labels=labels
            self.assignMobility()
        
        print('Final labels for mode {}: '.format(mode.upper()),labels)
        return labels

class CPExtractor:
    def __init__(self,graph):
        self.graph=graph

    def cpFinder(self):
        longestPathLen=0
        longestPath=0

        def caller(pointer,path=[]):
            if len(self.graph[pointer]) is 0:
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
        # Because inputs are initially were entered to graph as the order of their 'mobility' - operation order in equation, they 
        # are naturally sorted during cp extraction. Nevertheless, this individual nodes may be problem in the future, be careful
        if not starting_vertices:
            starting_vertices=[vertex for vertex in list(self.graph.keys()) if (not re.search(r'[a-zA-Z]',vertex.name) and not vertex.visited and vertex.conn.visited)]
            dump=[vertex.name for vertex in starting_vertices]
            print('Searching for other cps with nodes ',dump)

        for vertex in starting_vertices:
            path=caller(vertex,[vertex])
            longestPathLen,longestPath=(len(path),path) if len(path)>longestPathLen else (longestPathLen,longestPath)

        if longestPath:
            for node in longestPath:
                node.visited=1
            
        return longestPath

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
    cps=cpextractor.cpFinder()
    i=1
    while cps:
        dump=[node.name for node in cps]
        print('\n{}. DUMPED cps'.format(i),dump)
        i=i+1
        cps=cpextractor.cpFinder()