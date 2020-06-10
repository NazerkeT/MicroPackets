# ASAP, ALAP scheduling

from generate import DFGGenerator,write

class ASAP:
    def __init__(self,dfg):
        self.dfg=dfg

        self.schedule()
    
    def schedule(self):
        # pred={}
        # for node in self.tree:
        #     if 
        pass

class ALAP:
    def __init__(self,dfg):
        self.dfg=dfg




if __name__ == "__main__":
    equation1='z=(a*b+c/d)*(e+f)'
    equation2='v=(((a*b*n-m+c/d+(f-g)*h)-(x+y)/z)+(w-u))+(s*t)'
    equation3='v=w+((a*b*n-m+c/d+(f-g)*h)-(x+y)/z)'
    equation4=''

    tree = DFGGenerator(equation1).tree
    write(tree)
    asap=ASAP(tree)
    alap=ALAP(tree)