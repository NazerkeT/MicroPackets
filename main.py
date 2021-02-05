# ===> denotes to possible mistakes/improvements, other comments are descriptive
# Assumption per algorithm sections are described in each file below

from dfg_generator import *
from stage1 import *
from stage2 import *
from stage3 import *
from functions import *
from math import ceil

if __name__ == "__main__":
    ###########################
    # SECTION 0: Preparation  #
    ###########################

    # Generate DFG from equation
    equations = []
    with open('input.txt') as text:
        for line in text:
            equations.append(line.strip())
    
    # Define map of PEs to mark which PEs are free, which are not
    # PE assignment will be reflected on node.alloc property
    w, h = 10, 10
    scheduler = Scheduler( )
    allocator = Allocator(w, h)
    rescheduler = Rescheduler(w, h, 256, False)

    for i, equation in enumerate(equations):
        ###################
        # SECTION 1: HLS  #
        ###################
        print('\n------------------Synthesys of equation {} has started!---------------\n'.format(i+1))
        graph = DFGGenerator(equation).graph.graph
        write(graph)
        scheduler.putNewGraph(graph)
        allocator.putNewGraph(graph)

        # Initial schedule
        asap = scheduler.schedule('asap')
        alap = scheduler.schedule('alap',max(asap))
        
        # Critical path
        cpextractor = CPExtractor(graph)
        cp = cpextractor.extract()
        # Cps are collected just for print purposes
        cps = [cp]
        cp_allocs = {}

        # Extract critical paths, allocate and schedule
        # CPs are extracted from longest to shortest length
        i = 1
        while cp:
            if i > w*h:
                pass
                # raise error!
                
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

        rescheduler.putNewGraph(graph, allocator.inputs_by_pes, allocator.mult_inps)

        # Second arg indicates throughput, which is by default = 1
        # For now rescheduler works only for throughput of 1
        # ===> Change it later for throughput of 2
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

        print('\nRescheduler marker:')
        printDict(rescheduler.marker)

        print("\nScheduling duration in clocks: ", rescheduler.duration)

        print("\nCCM Size in bits: ", rescheduler.ccmsize)

        print("\nCCM Size in bytes: ", ceil(rescheduler.ccmsize/8))
        