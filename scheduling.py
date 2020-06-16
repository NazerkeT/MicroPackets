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
        
        print('Final labels for mode {}: '.format(mode.upper()),labels)
        return labels

if __name__ == "__main__":
    equation1='z=(a*b+c/d)*(e+f)'
    equation2='v=(((a*b*n-m+c/d+(f-g)*h)-(x+y)/z)+(w-u))+(s*t)'
    equation3='v=w+((a*b*n-m+c/d+(f-g)*h)-(x+y)/z)'

    graph = DFGGenerator(equation3).graph.graph
    write(graph)

    scheduler=Scheduler(graph)
    asap=scheduler.schedule('asap')
    alap=scheduler.schedule('alap',max(asap))