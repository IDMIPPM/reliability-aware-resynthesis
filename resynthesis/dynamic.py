# coding: utf-8
__author__ = 'IDM.IPPM (Mihail Myachikov)'

from itertools import product
import copy

def make_func(code):
    """
    :param code: Source code of function definition.
    :return: Function defined in the input code.
    """
    d = {}
    exec(code, d)
    return d['f']


def __make_operation_str(op, args, err=None, capacity=1):
    mask = (1 << capacity) - 1
    args = list(map(str, args))
    if args:
        arg1, *additional_args = args

    result = None
    if op == 'AND':
        result = ' & '.join(args)
    elif op == 'OR':
        result = ' | '.join(args)
    elif op == 'XOR':
        result = ' ^ '.join(args)
    elif op == 'NAND':
        result = str(mask) + ' ^ (' + ' & '.join(args) + ')'
    elif op == 'NOR':
        result = str(mask) + ' ^ (' + ' | '.join(args) + ')'
    elif op == 'XNOR':
        result = str(mask) + ' ^ (' + ' ^ '.join(args) + ')'
    elif op == 'INV':
        result = str(mask) + ' ^ ' + arg1
    elif op == 'BUF':
        result = arg1
    elif op == 'VCC':
        result = str(mask)
    elif op == 'GND':
        result = str(0)
    elif op == 'ID':
        result = arg1
    elif op == 'o':
        result = arg1

    if err is None or op in ['VCC', 'GND']:
        return result
    else:
        return '(' + result + ')' + ' ^ ' + err


def make_process_func_code(input_sch, capacity=1):
    """
    :param input_sch: Input scheme.
    :return: Function "process" code for input scheme.
    """
    sch = copy.deepcopy(input_sch)

    err_num = dict(zip(sorted(sch.__elements__.keys()), range(sch.elements())))

    code = "def f(input, error=None):\n  if error is None:\n    error = [0] * " + str(sch.elements())
    inputs = ['el_' + inp for inp in sch.__inputs__]
    code += '\n  ' + ', '.join(map(str, inputs)) + '= input'
    label_levels = sch.label_levels()
    levels = max(label_levels.values())
    for level in range(levels+1):
        labels = [label for label in sch.__elements__ if label_levels[label] == level]
        for el_label in labels:
            el_type, operands = sch.__elements__[el_label]
            operands = ['el_' + operand for operand in operands]
            el_expression = __make_operation_str(el_type, operands, 'error[' + str(err_num[el_label]) + ']', capacity)
            code += "\n  " + str('el_' + el_label) + " = " + el_expression
    sch.__outputs__ = ['el_' + out for out in sch.__outputs__]
    if len(sch.__outputs__) > 1:
        outputs = ', '.join(sch.__outputs__)
    else:
        outputs = '( ' + sch.__outputs__[0] + ',)'
    code += "\n  return " + outputs
    return code


def make_process_func(input_sch, debug=False, capacity=1):
    if debug:
        print(make_process_func_code(input_sch, capacity))
    return make_func(make_process_func_code(input_sch, capacity))
