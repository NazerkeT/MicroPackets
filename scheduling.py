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
        return node.conn

    def all_nodes_sched(self,preds,labels):
        for pred in preds:
            if labels[list(self.graph.keys()).index(pred)] is 0:
                return False
        
        return True
    
    def max(self,preds,labels):
        max=-1
        for pred in preds:
            max = labels[list(self.graph.keys()).index(pred)] if labels[list(self.graph.keys()).index(pred)] > max else max

        print(max)
        return max

    def min(self,preds,labels):
        min=1000
        for pred in preds:
            min = labels[list(self.graph.keys()).index(pred)] if labels[list(self.graph.keys()).index(pred)] < min else min

        print(min)
        return min

    def schedule(self,mode):
        vertices=set(list(self.graph.keys()))
        # Debugging
        for node in list(self.graph.keys()):
            print(node.name)
        
        labels=[]
        for node in list(self.graph.keys()):
            if mode is 'asap':
                flag=self.findPreds(node)
            elif mode is 'alap':
                flag=self.findSuccs(node)
            else:
                 print('Error: Mode is not chosen properly') 

            if not flag:
                labels.append(1)
                vertices=vertices-{node}
            else:
                labels.append(0)
        
        print('Labels: ',labels)
        
        while vertices:
            for node in vertices:
                preds=self.findPreds(node)
                # Debugging
                for pred in preds:
                    print(pred.name)
                    
                if self.all_nodes_sched(preds,labels):
                    if mode is 'asap':
                        print('Before change, aSap: ',labels[list(self.graph.keys()).index(node)])
                        labels[list(self.graph.keys()).index(node)]=self.max(preds,labels)+1
                        print('After change, aSap: ',labels[list(self.graph.keys()).index(node)])
                    else:
                        print('Before change, aLap: ',labels[list(self.graph.keys()).index(node)])
                        labels[list(self.graph.keys()).index(node)]=self.min(self.findSuccs(node),labels)-1  
                        print('After change, aLap: ',labels[list(self.graph.keys()).index(node)])

                    vertices=vertices-{node}
        
        if mode is 'asap':
            self.asap_labels=labels
        else:
            self.alap_labels=labels
        
        print(labels)
        return labels



if __name__ == "__main__":
    equation1='z=(a*b+c/d)*(e+f)'
    equation2='v=(((a*b*n-m+c/d+(f-g)*h)-(x+y)/z)+(w-u))+(s*t)'
    equation3='v=w+((a*b*n-m+c/d+(f-g)*h)-(x+y)/z)'

    graph = DFGGenerator(equation1).graph.graph
    write(graph)

    print('ASAP')
    scheduler=Scheduler(graph)
    asap=scheduler.schedule('asap')
    print('ALAP')
    asap=scheduler.schedule('alap')