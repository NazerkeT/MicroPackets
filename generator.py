# Script for DFG generator from equations
# ===> denotes to possible mistakes/improvements

# Assumption - Equation is given only in terms of letters, not numbers, values are assigned later 
# No more than 99 possible operands in equation 

# Extend parsing for numeric ops like x1, x2
# Extend parsing for other algorithmic ops like power, log, etc
# Add ccm counter
# Improve code, make more intuitive
# Extend graph and parsing functionality, so that now number of equations can be joined to single graph
# Node.conn may not be needed in the near future, or can be extended to list, due to number of successors possible

# ===> Check parsing whether does it work for complicated equations without brackets

import re

class Node:
    def __init__(self, name=None, value=None, op_type=None, conn=[]):
        self.name = name
        self.value = value
        self.op_type = op_type
        self.conn = [] + conn
        self.mblty = None
        self.visited = None
        self.alloc = None
        self.sched = None

class Graph:
    def __init__(self, vertex):
        self.graph = {}
        self.graph[vertex] = []

    def addNode(self, vertex, edge = []):
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

    def generateDfg(self):
        nodes = self.parse()
        print(nodes)
        self.graph = Graph(Node(self.equation[0], None, 'Write'))
        for i, node in enumerate(nodes):
            self.graph.addNode(Node(node[0], None, None))
            vertices = list(self.graph.graph)
            
            iterable = re.finditer(r'[0-9]+', node[1]) 
            for iter_ in iterable:
                start = iter_.start()
                end = iter_.end()
                    
                if start is 0:
                    self.graph.addNode(vertices[i+1], vertices[int(node[1][:end])])
                    vertices[i+1].op_type = node[1][end]
                    vertices[int(node[1][:end])].conn.append(vertices[int(node[0])])

                    if(not re.search(r'[0-9]+', node[1][end+1:])):
                        self.graph.addNode(vertices[i+1], Node(node[1][end+1:], None, 'Read', [vertices[int(node[0])]]))
                    
                else:
                    if(not re.search(r'[0-9]+', node[1][:start-1])):
                        self.graph.addNode(vertices[i+1], Node(node[1][:start-1], None, 'Read', [vertices[int(node[0])]]))

                    self.graph.addNode(vertices[i+1], vertices[int(node[1][start:])])
                    vertices[i+1].op_type = node[1][start-1]
                    vertices[int(node[1][start:])].conn.append(vertices[int(node[0])])

            if not self.graph.graph[vertices[i+1]]:
                self.graph.addNode(vertices[i+1], Node(node[1][0], None, 'Read', [vertices[int(node[0])]]))
                self.graph.addNode(vertices[i+1], Node(node[1][2], None, 'Read', [vertices[int(node[0])]]))
                vertices[i+1].op_type = node[1][1]
            
        # ===> This part is heavily subject to change after upgrading parse and graph for multiple equations   
        # Connect last and first vertices
        list(self.graph.graph)[-1].conn.append(list(self.graph.graph)[0]) 
        self.graph.addNode(list(self.graph.graph)[0], list(self.graph.graph)[-1])

        # Add child notes to graph
        inputs=[value for vertex in self.graph.graph for value in self.graph.graph[vertex] if (not re.search(r'[0-9]+', value.name))]
        for input in inputs:
            self.graph.addNode(input)
        
    def parse(self):
        self.equation = self.equation.replace(" ","")
        bracket_indices = []
        pointer = 0
        operands = []
        while pointer < len(self.equation):
            if(self.equation[pointer] == '('):
                bracket_indices.append(pointer)
                pointer = pointer + 1
            elif(self.equation[pointer] == ')'):
                start = bracket_indices.pop()
                self.removeBrackets(start, pointer)
                pointer = pointer - 1
                op_temp1, pointer = self.find('[*/]', operands, start, pointer)
                operands, pointer = self.find('[+-]', op_temp1, start, pointer)

            else:
                pointer = pointer + 1

        # Final check
        operands = self.find('[+-]',self.find('[*/]', operands, 0, len(self.equation))[0], 0, len(self.equation))[0]
        return operands

    def find(self, pattern, i_list, start, pointer):
        if (re.search(r'[a-z0-9]+{}[a-z0-9]+'.format(pattern), self.equation[start:pointer])):
            o_list = re.findall(r'[a-z0-9]+{}[a-z0-9]+'.format(pattern), self.equation[start:pointer])

            for i, elem in enumerate(o_list):
                self.equation = self.equation.replace(elem, str(1+len(i_list)))
                i_list.append((str(1+len(i_list)), o_list[i]))
                if((len(i_list) < 9 and len(o_list[i]) == 3) or (len(o_list[i]) == 4)):
                    pointer = pointer - 2
                elif(len(i_list) >= 9 and len(o_list[i]) == 3):
                    pointer = pointer - 1
                else:
                    pointer = pointer - 3

            return self.find(pattern, i_list, start, pointer)
        else:
            return i_list, pointer
        
def write(graph):
    arr = list(graph) 
    print('\nGraph nodes:')
    print('Name   Value   Op_Type   Conn')
    for node in arr:
        if node.conn:
            conn_dump = [node.name for node in node.conn]
            print(node.name, '    ', node.value, '    ', node.op_type, '    ', conn_dump)
        else:
            print(node.name, '    ', node.value, '    ', node.op_type, '    ', node.conn)

if __name__ == "__main__":
    equation1 = 'z=(a*b+c/d)*(e+f)'
    equation2 = 'v=(((a*b*n-m+c/d+(f-g)*h)-(x+y)/z)+(w-u))+(s*t)'
    equation3 = 'v=w+((a*b*n-m+c/d+(f-g)*h)-(x+y)/z)'

    graph = DFGGenerator(equation3).graph.graph
    write(graph)

 
