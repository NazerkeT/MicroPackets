# Script for DFG generator from equations
# ===> denotes to possible mistakes/improvements

# Assumption - There are no floating points in an equation
# No more than 99 possible operands in equation 

# Add ccm counter

import re

class Node:
    def __init__(self, name=None, value=None, op_type=None, conn=[]):
        self.name = name
        self.value = value
        self.op_type = op_type
        self.conn = [] + conn   # successors
        self.pred = []          # predecessors
        self.mblty = None
        self.visited = None
        self.alloc = None
        self.sched = None
        self.notif = [0, 0]     # notif from pred about presched

class Graph:
    def __init__(self, vertex):
        self.graph = {}
        self.graph[vertex] = []

    def addNode(self, vertex, edge = None):
        if vertex not in self.graph:
            self.graph[vertex] = []

        if edge:
            self.graph[vertex].append(edge)
            
class DFGGenerator:
    def __init__(self, equation):
        self.equation = equation
        self.graph = None
        self.ccm_size = 0

        self.generateDfg()

    def removeBrackets(self, start, end):
        self.equation = self.equation[:start] + self.equation[start+1:]
        self.equation = self.equation[:end-1] + self.equation[end:]

    def repl(self, matchobj):
        string = matchobj.group(0)[0] + 'int' + matchobj.group(0)[1:]
        return string

    def generateDfg(self):
        self.equation = self.equation.replace(" ","")
        # First replace the constant integer with int token
        self.equation = re.sub(r'[\/\+\*\-\^][0-9]+',self.repl, self.equation) 
        self.equation = re.sub(r'[^a-zA-Z\_0-9][0-9]+[\/\+\*\-\^]',self.repl, self.equation) 

        # Then we may proceed to parsing
        nodes = self.parse()
        print(nodes)
        acc_node = re.split('=', self.equation)[0]
        self.graph = Graph(Node(acc_node, None, 'Write'))

        inputs=[]

        for i, node in enumerate(nodes):
            self.graph.addNode(Node(node[0], None, None))
            vertices   = list(self.graph.graph)
            inputNames = [inp.name for inp in inputs]

            iterable = re.split(r'[\/\+\*\-\^]', node[1])
            op_ind   = len(iterable[0])
            for iter_ in iterable:
                if(re.search(r'[a-zA-Z\_]+', iter_)):
                    if (iter_ in inputNames):
                        inputs[inputNames.index(iter_)].conn.append(vertices[int(node[0])])
                        self.graph.addNode(vertices[i+1], inputs[inputNames.index(iter_)]) 
                    else:
                        node_addr = Node(iter_, None, 'Read', [vertices[int(node[0])]])
                        inputs.append(node_addr)
                        self.graph.addNode(vertices[i+1], node_addr) 
                else:
                    self.graph.addNode(vertices[i+1], vertices[int(iter_)])
                    vertices[int(iter_)].conn.append(vertices[int(node[0])])  

                vertices[i+1].op_type = node[1][op_ind]
            
        # Connect last and first vertices
        list(self.graph.graph)[-1].conn.append(list(self.graph.graph)[0]) 
        self.graph.addNode(list(self.graph.graph)[0], list(self.graph.graph)[-1])

        # Add child notes to graph
        inputs = [value for vertex in self.graph.graph for value in self.graph.graph[vertex] if (re.search(r'[a-zA-Z]+', value.name))]
        for input in inputs:
            self.graph.addNode(input)
                        
    def parse(self):
        bracket_indices = []
        pointer  = 0
        operands = []
        while pointer < len(self.equation):
            if(self.equation[pointer] == '('):
                bracket_indices.append(pointer)
                pointer = pointer + 1
            elif(self.equation[pointer] == ')'):
                start = bracket_indices.pop()
                self.removeBrackets(start, pointer)
                pointer = pointer - 1
                op_temp1, pointer = self.find('[\^]', operands, start, pointer)
                op_temp2, pointer = self.find('[\*\/]', op_temp1, start, pointer)
                operands, pointer = self.find('[\+\-]', op_temp2, start, pointer)

            else:
                pointer = pointer + 1

        # Final check
        operands = self.find('[\+\-]',self.find('[\*\/]', self.find('[\^]', operands, 0, len(self.equation))[0], 0, len(self.equation))[0], 0, len(self.equation))[0]
        return operands

    def find(self, pattern, i_list, start, pointer):
        

        if (re.search(r'[a-zA-Z0-9]+{}[a-zA-Z0-9]+'.format(pattern), self.equation[start:pointer])):
            o_list = re.findall(r'[a-zA-Z0-9]+{}[a-zA-Z0-9]+'.format(pattern), self.equation[start:pointer])

            for i, elem in enumerate(o_list):
                self.equation = self.equation.replace(elem, str(1+len(i_list)))
                pointer = pointer - abs(len(elem) - len(str(1 + len(i_list))))

                i_list.append((str(1+len(i_list)), o_list[i]))
            
            return self.find(pattern, i_list, start, pointer)
        else:
            return i_list, pointer
        
def write(graph):
    arr = list(graph) 
    print('\nGraph nodes:')
    print('Name   Value   Op_Type   Conn')
    for node in arr:
        if node.conn:
            conn_dump = [node_.name for node_ in node.conn]
            print(node.name, '    ', node.value, '    ', node.op_type, '    ', conn_dump)
        else:
            print(node.name, '    ', node.value, '    ', node.op_type, '    ', node.conn)


 

