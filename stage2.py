# Stage 2 of the heuristic algorithm
# Allocate and schedule each critical path

from stage1 import *

class Allocator:
    def __init__(self,graph,w,h):
        self.graph=graph
        self.cp=None
        self.pemap=[[0 for x in range(w)] for y in range(h)] 
        self.allocateInputs()

    def allocateInputs(self):
        inputs=[node for node in self.graph.keys() if not self.graph[node]]
        j=0
        for i in range(len(inputs)//2+1):
            if j<len(inputs):                
                inputs[j].visited,inputs[j].alloc=2,i
            if j+1<len(inputs):
                inputs[j+1].visited,inputs[j+1].alloc=2,i
                
            j=j+2

    def findMinPath(self,cp):
        minPaths=[]
        for i in range(len(cp)):
            path=0
            for node in cp:
                for pred in self.graph[node]:
                    if re.search(r'[a-zA-Z]',pred):
                        path=path+pred.alloc-i
            
            minPaths.append(path)

        return minPaths.index(min(minPaths)),minPaths

    def allocateCp(self,cp,w,h):
        cp.reverse()
        # 1st step - search for min path
        peAssigned=self.findMinPath(cp)
        for node in cp:
            node.alloc=peAssigned
        # 2nd step - schedule with respect to parents,change pemap values
        for node in cp:
            for pred in self.graph[node]:
                if pred.alloc:
                    dist=pred.alloc+1
                else:
                    dist=0

                
        # Reallocate if more than one min path PEs exist
        return 

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
    cp=cpextractor.extract()

    # Define map of PEs to mark which PEs are free, which are not
    # PE assignment will be reflected on Node.alloc property as well
    w, h = 5, 5
    allocator=Allocator(graph,w,h)

    i=1
    while cp:
        dump=[node.name for node in cp]
        print('\n{}. DUMPED cp'.format(i),dump)
        i=i+1
        cp=cpextractor.extract()
        allocator.allocateCp(cp,w,h)
    