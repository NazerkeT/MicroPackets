# ===> denotes to possible mistakes/improvements, other comments are descriptive
# Assumption per algorithm sections are described in each file below

from dfg_generator import *
from stage1 import *
from stage2 import *
from stage3 import *
# from pckt_generator import *

if __name__ == "__main__":
    equation1 = 'z=(a*b+c/d)*(e+f)'
    equation2 = 'v=(((a*b*n-m+c/d+(f-g)*h)-(x+y)/z)+(w-u))+(s*t)'
    equation3 = 'v=w+((a*b*n-m+c/d+(f-g)*h)-(x+y)/z)'
    equation4 = 'z=a*b+c/d*e+f'
    equation5 = 'z=a+b+(a+b)*c+d*(e+f)+e+f'
    equation6 = 'z=a+(b*(c+d)+(a+b))-b'

    # ===> Add here file parser, to read eqs from file

    ###################
    # SECTION 1: HLS  #
    ###################

    # Generate DFG from equation
    graph = DFGGenerator(equation1).graph.graph
    write(graph)

    scheduler = Scheduler(graph)
    asap = scheduler.schedule('asap')
    alap = scheduler.schedule('alap',max(asap))
    
    cpextractor = CPExtractor(graph)
    cp = cpextractor.extract()
    # Cps are collected just for print purposes
    cps = [cp]
    cp_allocs = {}

    # Define map of PEs to mark which PEs are free, which are not
    # PE assignment will be reflected on node.alloc property
    w, h = 5, 5
    allocator = Allocator(graph, w, h)

    # Extract critical paths, allocate and schedule
    # CPs are extracted from longest to shortest length
    i = 1
    while cp:
        dump = [node.name for node in reversed(cp)]
        print('\n{}. DUMPED cp: '.format(i), dump)
        i = i + 1
        allocator.allocateCp(cp, w, h, scheduler)
        cp_allocs.update({cp[0].alloc : [(node.name, node.sched) for node in cp]})
        cp = cpextractor.extract()

        if cp:
            cps.append(cp)
    
    # Collect input allocation per PEs
    input_allocs = {node.alloc : [] for node in graph if node.sched is 0}
    for node in graph:
        for alloc in input_allocs:
            if node.sched is 0 and node.alloc == alloc:
                        input_allocs[alloc].append(node.name)

    print('\nInput allocation by PEs:')
    printDict(input_allocs)

    print('\nFinal results before rescheduling (node.name, node.sched) by PEs: ')
    printDict(cp_allocs)

    rescheduler = Rescheduler(graph, allocator.inputs_by_pes, allocator.mult_inps)

    # Second arg indicates throughput, which is by default = 1
    # For now rescheduler works only for throughput of 1
    rescheduler.reschedule(1)

    print('\nFinal results after rescheduling (node.name, node.sched): by PEs')
    cp_allocs = {cp[0].alloc : [(node.name, node.sched) for node in cp] for cp in cps}

    printDict(cp_allocs)

    # Show PE utilization
    print('\nPE map ')
    for pe in allocator.pemap:
        print(pe)

    ############################
    # SECTION 2: MICROPACKETS  #
    ############################

    print("\nNode scheds and CCM commands:")
    printDict(rescheduler.node_scheds)

    print("\nRouter scheds and CCM commands:")
    printDict(rescheduler.router_scheds)

    print('\nRescheduler marker')
    printDict(rescheduler.marker)