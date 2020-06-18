# Stage 2 of the heuristic algorithm
# Allocate and schedule each critical path


 
from stage1 import *

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