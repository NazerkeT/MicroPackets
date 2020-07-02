# Stage 2,3 of the heuristic algorithm
# Allocate and schedule each critical path
# Check graph for data redundancies => reschedule 
# It is assummed that pes are available to allocate and schedule all cps
# ===> denotes to possible mistakes/improvements, other comments are descriptive

from stage1 import *

class Allocator:
    def __init__(self,graph,w,h):
        self.graph=graph
        self.pemap=[[0 for x in range(w)] for y in range(h)] 
        self.allocateInputs()

    # Inputs are allocated to reg file of each pe, not to input registers
    def allocateInputs(self):
        inputs=[node for node in self.graph.keys() if not self.graph[node]]
        j=0
        # ===> Change this piece of code later to make more pythonic
        for i in range(len(inputs)//2+1):
            i=(0,i) if i<5 else (i//5,i%5)
            if j<len(inputs):                
                inputs[j].sched,inputs[j].alloc=0,i
            if j+1<len(inputs):
                inputs[j+1].sched,inputs[j+1].alloc=0,i

            j=j+2

    def summDists(self,coord,dests):
        return sum([compDistance(coord,dest[0])*dest[1] for dest in dests])

    def criticalSched(self,cp,addrs):
        # Start searching for other most suitable coords
        if len(cp) is 1:
            indices_list=[]
        return (),[]

    def findMinPath(self,cp):
        # Prepare input allocations with freq of each cell set
        inputAllocs=[[child.alloc,1] for node in cp for child in self.graph[node] if child.alloc]
        visited=[]
        for inp in inputAllocs:
            if inp in visited:
                inputAllocs.remove(inp)
                inp[-1]=inp[-1]+1
            else:
                visited.append(inp)

        print('   Inputs ',inputAllocs)

        # Find valid range of cells for pe search in terms of row, col inds of inputs
        rowColRange=[]
        for i in range(0,2):
            inds=[inp[0][i] for inp in inputAllocs]
            rowColRange.append((min(inds),max(inds))) 
            rowColRange[i]=[rowColRange[i][0]] if rowColRange[i][0]==rowColRange[i][1] else list(range(rowColRange[i][0],rowColRange[i][1]+1))
       
        # Permute all pe addrs
        addrs=[(x,y) for x in rowColRange[0] for y in rowColRange[1]]

        # Calculate sum of distances for each permutted pe
        distances=[(addr,self.summDists(addr,inputAllocs)) for addr in addrs if not self.pemap[addr[0]][addr[1]]]

        if distances:
            min_dist=min(distances,key=lambda x: x[1])
        else:
            min_dist,distances=self.criticalSched(cp,addrs)
                
        distances=[dist[0] for dist in distances if min_dist[1]==dist[1]]
        
        print('   (Min d coord, min d), all dists: ', min_dist,distances)
        return distances

    def allocateCp(self,cp,w,h,scheduler):
        if not cp:
            return
        cp.reverse()
        # 1st step - search for min path
        pe_options=self.findMinPath(cp)

        # 2nd step - schedule with respect to parents,change pemap values
        # 3rd step - Reallocate if more than one min path PEs exis

        print('    Schedule labels with allocation: ')
        allPsblScheds=[scheduler.schedule('asap',None,pe,cp) for pe in pe_options]
        shortest_sched=min(allPsblScheds,key=max)
        min_dist_pe=pe_options[allPsblScheds.index(shortest_sched)]
        print(min_dist_pe)
        self.pemap[min_dist_pe[0]][min_dist_pe[1]]=1
        for node,sched_step in zip(cp,shortest_sched):
            node.alloc=min_dist_pe
            node.sched=sched_step

        print('Final (min d coord,min d) and schedule ',min_dist_pe,shortest_sched)
        print('All schedules generated: ', allPsblScheds)
        return min_dist_pe,shortest_sched

class Rescheduler:
    def __init__(self,graph):
        self.graph=graph
        self.final_schedule=[]

        self.reschedule()

    def reschedule(self):
        # Extract only op nodes from graph and put 'Write' node to the end
        nodes=[node for node in list(self.graph.keys()) if node.sched]
        nodes.append(nodes.pop(0))

        self.final_schedule=[node.sched for node in list(self.graph.keys())]
        dump=[node.name for node in list(self.graph.keys())]
        print('\nPred-final results for all 3 stages of heuristic scheduling: ')
        print([(name,sched) for name,sched in zip(dump,self.final_schedule)])

        # Check for sched step redundancy
        for node in nodes:
            for pred in self.graph[node]:
                if pred.sched and node.sched<=pred.sched:
                    node.sched=pred.sched+1
        
        self.final_schedule=[node.sched for node in list(self.graph.keys())]
        dump=[node.name for node in list(self.graph.keys())]
        print('Final results for all 3 stages of heuristic scheduling: ')
        print([(name,sched) for name,sched in zip(dump,self.final_schedule)])


if __name__ == "__main__":
    equation1='z=(a*b+c/d)*(e+f)'
    equation2='v=(((a*b*n-m+c/d+(f-g)*h)-(x+y)/z)+(w-u))+(s*t)'
    equation3='v=w+((a*b*n-m+c/d+(f-g)*h)-(x+y)/z)'

    graph = DFGGenerator(equation2).graph.graph
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
        print('\n{}. DUMPED cp: '.format(i),dump)
        i=i+1
        allocator.allocateCp(cp,w,h,scheduler)
        cp=cpextractor.extract()

    rescheduler=Rescheduler(graph)
        
    # Show pe utilization
    print(allocator.pemap)