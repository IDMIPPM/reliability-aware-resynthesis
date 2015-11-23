# coding: utf-8
__author__ = 'IDM.IPPM (Mihail Myachikov)'

import copy
from string import ascii_uppercase
from itertools import product, chain, islice, repeat
from functools import reduce
from operator import and_, or_, xor

#from scheme.tmp.old import scheme as sc

def replace_elements_with_scheme(scheme, elements, subscheme):
    scheme = copy.deepcopy(scheme)
    scheme.replace_elements_with_scheme(elements, subscheme)
    return scheme

def read_scheme(filename):
    scheme = scheme_alt()
    f = open(filename)
    lines = f.readlines()
    scheme.__inputs__ = lines[0].split()[1:]
    scheme.__outputs__ = lines[1].split()[1:]
    elements = lines[3:]
    for element in elements:
        operation, *operands, result = element.split()
        scheme.__elements__[result] = (operation, list(operands))
    return scheme

def evaluate(operation, args, capacity=1, error=0):
    mask = (2 << (capacity - 1)) - 1
    if args != ():
        arg1, *additional_args = args

    result = 0
    if operation == 'AND':
        result = reduce(and_, args, mask)
    elif operation == 'OR':
        result = reduce(or_, args, 0)
    elif operation == 'XOR':
        result = reduce(xor, args, 0)
    elif operation == 'INV':
        result = mask ^ arg1
    elif operation == 'BUF':
        result = arg1
    elif operation == 'NAND':
        result = mask ^ reduce(and_, args, mask)
    elif operation == 'NOR':
        result = mask ^ reduce(or_, args, 0)
    elif operation == 'XNOR':
        result = mask ^ reduce(xor, args, 0)
    elif operation == 'VCC':
        result = mask
    elif operation == 'GND':
        result = 0

    if error and operation != 'BUF':
        result ^= error

    return result

def merge_schemes(schemes, connections=None, outputs=None):
    if not connections:
        connections = dict()

    schemes = [copy.deepcopy(scheme) for scheme in schemes]
    possible_labels = map(''.join, product(ascii_uppercase, repeat=3))  # 17576 possible labels 3 characters long
    labels_in_use = set(chain(*[sch.all_labels() for sch in schemes]))
    new_labels = (label for label in possible_labels if label not in labels_in_use)
    result = scheme_alt()
    rename_dict = [None for _ in schemes]

    for i, sch in enumerate(schemes):
        rename_dict[i] = dict(zip(sch.all_labels(), islice(new_labels, len(sch.all_labels()))))
        sch.rename_labels(rename_dict[i])
    renamed_connections = dict()
    for sch_number, label in connections:
        connection = connections[(sch_number, label)]
        new_connection = [rename_dict[n][l] for n, l in connection]
        new_label = rename_dict[sch_number][label]
        renamed_connections[new_label] = new_connection

    if outputs is None:
        result.__outputs__ = list(chain(*[sch.output_labels() for sch in schemes]))
    else:
        result.__outputs__ = [rename_dict[number][label] for number, label in outputs]


    result.__elements__ = dict()
    for sch in schemes:
        result.__elements__.update(sch.__elements__)

    rename_dict = dict()
    for input in renamed_connections:
        for output in renamed_connections[input]:
            rename_dict[output] = input
    result.rename_labels(rename_dict)
    all_schemes_inputs = chain(*[sch.input_labels() for sch in schemes])
    for sch in schemes:
        print(sch)
    print(list(chain(*[sch.input_labels() for sch in schemes])))
    result.__inputs__ = [input_label for input_label in all_schemes_inputs if input_label not in rename_dict]
    return result

def replicate(sch, num=3):
    connections = dict()
    for input_label in sch.input_labels():
        connections[(0, input_label)] = list(zip(range(1, num), repeat(input_label, num-1)))
    return merge_schemes([sch]*num, connections)

class scheme_alt(object):
    def __init__(self):
        self.__inputs__ = []
        self.__outputs__ = []
        self.__elements__ = dict()

    def __str__(self):
        return '\n'.join(
            ['inputs', str(self.__inputs__), 'outputs', str(self.__outputs__), 'elements', str(self.__elements__)])

    def inputs(self):
        return len(self.__inputs__)

    def outputs(self):
        return len(self.__outputs__)

    def elements(self):
        return len(self.__elements__)

    def input_labels(self):
        return list(self.__inputs__)

    def output_labels(self):
        return list(self.__outputs__)

    def element_labels(self):
        return list(self.__elements__.keys())

    def all_labels(self):
        return self.input_labels() + self.element_labels()

    def process(self, input_values, error_values=None, capacity=1):
        processed = dict()
        if error_values:
            error_values = {label: error for label, error in zip(sorted(self.__elements__.keys()), error_values)}
        else:
            error_values = {label: 0 for label in self.__elements__.keys()}
        for value, label in zip(input_values, self.__inputs__):
            processed[label] = value

        def process_element(label):
            if label in processed:
                return processed[label]
            else:
                operation, operands = self.__elements__[label]
                value = evaluate(operation, tuple(map(process_element, operands)), capacity, error_values[label])
                processed[label] = value
                return value

        return tuple(map(process_element, self.__outputs__))

    def subscheme(self, labels):
        scheme = scheme_alt()
        inputs = set(chain(*[list(self.__elements__[label][1]) for label in labels]))
        in_use = set(chain(chain(*[list(self.__elements__[key][1]) for key in self.__elements__ if key not in labels]), set(self.__outputs__)))
        scheme.__inputs__ = list(sorted(inputs - set(labels)))
        scheme.__outputs__ = list(sorted(in_use.intersection(set(labels))))
        for label in labels:
            if label in self.__elements__:
                scheme.__elements__[label] = self.__elements__[label]

        return scheme

    def subscheme_by_outputs(self, labels):
        stack = labels[:]
        visited = set(self.input_labels()[:])
        while stack:
            label = stack.pop()
            visited.add(label)
            op, args = self.__elements__[label]
            stack.extend(set(args) - visited)
        scheme = self.subscheme(visited - set(self.input_labels()[:]))
        scheme.__outputs__ = labels[:]
        return scheme

    def rename_labels(self, rename_dict):
        def rename(label):
            return rename_dict[label] if label in rename_dict else label

        self.__inputs__ = list(map(rename, self.__inputs__))
        self.__outputs__ = list(map(rename, self.__outputs__))

        renamed_elements = dict()
        for element_label in self.__elements__:
            new_label = rename(element_label)
            renamed_elements[new_label] = self.__elements__[element_label]
        self.__elements__ = renamed_elements

        for element_label in self.__elements__:
            operation, operands = self.__elements__[element_label]
            self.__elements__[element_label] = (operation, list(map(rename, operands)))

    def replace_elements_with_scheme(self, element_labels, sch, outputs_labels=None):
        sch = copy.deepcopy(sch)
        subscheme = self.subscheme(element_labels)
        if outputs_labels is not None:
            subscheme.__outputs__ = outputs_labels
        if len(subscheme.__inputs__) != len(sch.__inputs__) or len(subscheme.__outputs__) != len(sch.__outputs__):
            print('Number of inputs and outputs of circuits must agree.')
            return False
        rename_dict = dict()

        for i, input_label in enumerate(sch.__inputs__):
            rename_dict[input_label] = subscheme.__inputs__[i]
        for i, output_label in enumerate(sch.__outputs__):
            rename_dict[output_label] = subscheme.__outputs__[i]

        possible_labels = map(''.join, product(ascii_uppercase, repeat=3))  # 17576 possible labels 3 characters long
        new_element_labels = (label for label in possible_labels if label not in self.__elements__)
        # new_element_labels = islice(new_element_labels, sch.elements())
        for label, new_label in zip(sch.__elements__, new_element_labels):
            if label not in sch.__outputs__:
                rename_dict[label] = new_label
        sch.rename_labels(rename_dict)
        for element_label in element_labels:
            if not element_label in sch.output_labels():
                self.__elements__.pop(element_label)

        self.__elements__.update(sch.__elements__)
        return True

    def display_truth_table(self):
        for vector in product((0,1), repeat = self.inputs()):
            print(vector, '|', self.process(vector))

    def label_levels(self):
        return {label: self.level(label) for label in chain(self.__inputs__, self.__elements__.keys())}

    def level(self, label):
        if label in self.__inputs__:
            return 0
        else:
            operation, operands = self.__elements__[label]
            if operation in ('VCC', 'GND'):
                return 0
            else:
                return max(map(self.level, operands)) + 1

    def print_circuit_in_file(self, filename):
        f = open(filename, 'w')  # 'x'
        scheme = object
        f.write(str(len(self.__inputs__)) + ' ' + ' '.join(self.__inputs__) + '\n')
        f.write(str(len(self.__outputs__)) + ' ' + ' '.join(self.__outputs__) + '\n')
        f.write(str(len(self.__elements__)) + '\n')
        lst = sorted(list(self.__elements__.keys()))
        for i in lst:
            temp = self.__elements__[i]
            f.write(temp[0] + ' ')
            f.write(' '.join(temp[1]) + ' ')
            f.write(i + '\n')
        f.close()

    def print_verilog_in_file(self, filename):
        f = open(filename, 'w')  # 'x'
        scheme = object
        f.write('module circ (' + ', '.join(self.__inputs__) + ', ' + ', '.join(self.__outputs__) + ');\n')
        for i in self.__inputs__:
            f.write('   input ' + str(i) + ';\n')
        for i in self.__outputs__:
            f.write('   output ' + str(i) + ';\n')

        check_list = []
        lst = sorted(list(self.__elements__.keys()))
        for i in lst:
            temp = self.__elements__[i]
            for j in temp[1]:
                if j in self.__inputs__:
                    continue
                if j in self.__outputs__:
                    continue
                if j in check_list:
                    continue
                f.write('   wire ' + str(j) + ';\n')
                check_list.append(j)

        count = 0
        for i in lst:
            temp = self.__elements__[i]
            f.write('   ' + str(temp[0]) + ' inst' + str(count) + '(')
            f.write('.ZN(' + i + ')')
            k = 1
            for j in temp[1]:
                f.write(', .A' + str(k) + '(' + str(j) + ')')
                k += 1
            f.write(');\n')
            count += 1

        f.write('endmodule\n')
        f.close()
