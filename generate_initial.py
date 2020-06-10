# Script for DFG generator from equations
# Initial version for tree output only. Refer to generate.py for full graph version

import re

class Node:
    def __init__(self,name=None,value=None,op_type=None,conn=None):
        self.name=name
        self.value=value
        self.op_type=op_type
        self.conn=conn

class Tree:
    def __init__(self,root):
        self.root=root
        self.children=[]

    def addNode(self,node):
        self.children.append(node)

class DFGGenerator:
    def __init__(self,equation):
        self.equation=equation
        self.tree=None 
        self.ccm_size=0

        self.generateDfg()

    def removeBrackets(self,start,end):
        self.equation=self.equation[:start]+self.equation[start+1:]
        self.equation=self.equation[:end-1]+self.equation[end:]

    def generateDfg(self):
        nodes=self.parse()
        print(nodes)
        self.tree=Tree(Node(self.equation[0],None,'Write'))

        for i,node in enumerate(nodes):
            nodes[i]=Tree(Node(node[0],None,None,None))
            iterable=re.finditer(r'[0-9]+',node[1]) 
            for iter_ in iterable:
                start=iter_.start()
                end=iter_.end()
                    
                if start is 0:
                    nodes[i].root.op_type=node[1][end]
                    nodes[i].addNode(nodes[int(node[1][:end])-1])
                    nodes[i].children[0].root.conn=node[0]
                    if(not re.search(r'[0-9]+',node[1][end+1:])):
                        nodes[i].addNode(Tree(Node(node[1][end+1:],None,'Read',node[0])))
                    
                else:
                    nodes[i].root.op_type=node[1][start-1]
                    if(not re.search(r'[0-9]+',node[1][:start-1])):
                        nodes[i].addNode(Tree(Node(node[1][:start-1],None,'Read',node[0])))
                    nodes[i].addNode(nodes[int(node[1][start:])-1])
                    nodes[i].children[1].root.conn=node[0]
                

            if not nodes[i].children:
                nodes[i].addNode(Tree(Node(node[1][0],None,'Read',node[0])))
                nodes[i].addNode(Tree(Node(node[1][2],None,'Read',node[0])))
                nodes[i].root.op_type=node[1][1]

           
        nodes[-1].root.conn=self.tree.root.name
        self.tree.addNode(nodes[-1])
     
        
    def parse(self):
        self.equation=self.equation.replace(" ","")
        bracket_indices=[]
        pointer=0
        operands=[]
        while pointer<len(self.equation):
            if(self.equation[pointer]=='('):
                bracket_indices.append(pointer)
                pointer=pointer+1
            elif(self.equation[pointer]==')'):
                start=bracket_indices.pop()
                self.removeBrackets(start,pointer)
                pointer=pointer-1
                op_temp1,pointer=self.find('[*/]',operands,start,pointer)
                operands,pointer=self.find('[+-]',op_temp1,start,pointer)

            else:
                pointer=pointer+1

        # Final check
        operands=self.find('[+-]',self.find('[*/]',operands,0,len(self.equation))[0],0,len(self.equation))[0]
        return operands

    def find(self,pattern,i_list,start,pointer):
        if (re.search(r'[a-z0-9]+{}[a-z0-9]+'.format(pattern),self.equation[start:pointer])):
            o_list=re.findall(r'[a-z0-9]+{}[a-z0-9]+'.format(pattern),self.equation[start:pointer])

            for i,elem in enumerate(o_list):
                self.equation=self.equation.replace(elem,str(1+len(i_list)))
                i_list.append((str(1+len(i_list)),o_list[i]))
                if((len(i_list)<9 and len(o_list[i])==3) or(len(o_list[i])==4)):
                    pointer=pointer-2
                elif(len(i_list)>=9 and len(o_list[i])==3):
                    pointer=pointer-1
                else:
                    pointer=pointer-3

            return self.find(pattern,i_list,start,pointer)
        else:
            return i_list,pointer
        
def write(tree):
    arr=traverse(tree,[])
    for node in arr:
        print(node.name,node.value,node.op_type,node.conn)

def traverse(tree,arr):
    if tree:
        if tree.children:
            for child in tree.children:
                traverse(child,arr)
        arr.append(tree.root)

    return arr

if __name__ == "__main__":
    equation1='z=(a*b+c/d)*(e+f)'
    equation2='v=(((a*b*n-m+c/d+(f-g)*h)-(x+y)/z)+(w-u))+(s*t)'
    equation3='v=w+((a*b*n-m+c/d+(f-g)*h)-(x+y)/z)'
    equation4=''

    tree = DFGGenerator(equation3).tree
    write(tree)

 
