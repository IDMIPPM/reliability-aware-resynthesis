# coding: utf-8
__author__ = 'IDM.IPPM (Roman Solovyev, Dmitry Telpukhov)'

import os
import copy
from itertools import product
import subprocess
from math import floor, log2
from resynthesis.binary_op import *
from resynthesis.resynthesis_external_stats import get_project_directory

def get_binary_value(vec):
    val = 0
    mul = 1
    for v in vec:
        val += v*mul
        mul = mul*2
    return val

def create_truth_table (cir):
    tt = []
    for vector in product((0,1), repeat = cir.inputs()):
        tt.append(cir.process(vector))
    return tt

def compareStrDiff(s1, s2):
    l1 = len(s1)
    l2 = len(s2)
    if l1 != l2:
        print("Fatal error {0}, {1}").format(s1, s2)
        exit()
    diff_count = 0
    diff_pos = -1
    for i in range(0, l1):
        sym1 = s1[int(i):int(i+1)]
        sym2 = s2[int(i):int(i+1)]
        if sym1 != sym2:
            if (sym1 == 'X' or sym2 == 'X'):
                return 'diff'
            diff_count = diff_count + 1
            diff_pos = i

    if diff_count == 0:
        return 'same'
    elif diff_count > 1:
        return 'diff'
    else:
        return s1[0:diff_pos] + 'X' + s1[diff_pos+1:]

def write_truth_table_to_espresso(truth_table, scheme,  filename):
    """
    :param truth_table: Truth table to write.
    :param filename: Name of file to write.
    :return: None
    """
    f = open(filename, 'w')
    inputs = floor(log2(len(truth_table)))
    outputs = len(truth_table[0])


    f.write('.i ' + str(inputs) + '\n')
    f.write('.o ' + str(outputs) + '\n')

    input_names = scheme.input_labels()
    output_names = scheme.output_labels()

    f.write('.ilb ' + ' '.join(input_names) + '\n')
    f.write('.ob  ' + ' '.join(output_names) + '\n')

    def row_in_espresso_format(row, index):
        s = ''.join(map(str, list(reversed(num2vec(index, inputs)))))
        s += ' '
        s += ''.join(map(str, row))
        s += '\n'

        return s

    for i, row in enumerate(truth_table):
        f.write(row_in_espresso_format(row, i))

    f.write('.e\n')
    f.close()

def quineStep1(arr):
    counter = 0
    cur_arr = copy.copy(arr)
    flag = 1
    while (flag):
        flag = 0
        new_arr = []
        for i in range(0, len(cur_arr)):
            ci = cur_arr[i]
            if ci == 'same':
                continue
            flag1 = 0
            for j in range(i+1, len(cur_arr)):
                cj = cur_arr[j]
                if cj == 'same':
                    continue
                data = compareStrDiff(ci, cj)
                if data != 'diff':
                    if data == 'same':
                        cur_arr[j] = 'same'
                    else:
                        new_arr.append(data)
                        flag1 = 1
                        flag = 1
            if flag1 == 0:
                if ci != 'same':
                    new_arr.append(ci)
        counter = counter + 1
        if (counter > 10000):
            break
        cur_arr = copy.copy(new_arr)
    return cur_arr

def isCover(s1, s2):
    l1 = len(s1)
    l2 = len(s2)
    if l1 != l2:
        print("Fatal error {0}, {1}").format(s1, s2)
        exit()
    for i in range(0, l1):
        sym1 = s1[i:i+1]
        sym2 = s2[i:i+1]
        if sym1 == 'X':
            continue
        if sym1 != sym2:
            return 0
    return 1

# Оставить только те что дают хоть один крестик
def quineFindUsable(arr, needed):
    usable = []
    total = len(arr)
    for i in range(0, total):
        ttl1 = len(needed)
        flag = 0
        for j in range(0, ttl1):
            if isCover(arr[i], needed[j]):
                flag = 1
        if flag == 1:
            usable.append(arr[i])
    return usable

def checkCov(arr1, arr2):
    l1 = len(arr1)
    l2 = len(arr2)
    if l1 != l2:
        print("Fatal error {0}, {1}").format(arr1, arr2)
        exit()
    c1 = 0
    c2 = 0
    for i in range(0, l1):
        if (arr1[i] == 1 and arr2[i] == 0):
            c1 = c1 + 1
        if (arr1[i] == 0 and arr2[i] == 1):
            c2 = c2 + 1
    if (c1 == 0 and c2 >= 0):
        return 0
    if (c2 == 0 and c1 >= 0):
        return 1
    return 2


def useCovMatrix(arr, needed):
    covarr = []
    marked = []

    # Построить матрицу покрытия

    total = len(arr)
    for i in range(0, total):
        marked.append(1)
        covarr.append([])
        ttl1 = len(needed)
        for j in range(0, ttl1):
            covarr[i].append(-1)
            if isCover(arr[i], needed[j]):
                covarr[i][j] = 1
            else:
                covarr[i][j] = 0

    # Вычеркнуть те, что полностью покрываются другими
    for i in range(0, total):
        if marked[i] == 0:
            continue
        for j in range(i+1, total):
            if marked[j] == 0:
                continue
            tp = checkCov(covarr[i], covarr[j])
            if tp == 0:
                marked[i] = 0
            elif tp == 1:
                marked[j] = 0

    # Заполняем финальный массив
    usable = []
    for i in range(0, total):
        if marked[i] == 0:
            continue
        usable.append(arr[i])

    return usable


def quineForOutput(variable, minterm):

    needed = []
    for i in minterm:
        str1 = "{0}0:0{1}b{2}".format('{', variable, '}')
        needed.append(str1.format(i))
    # print(needed)

    arr = quineStep1(needed)

    # print(arr)

    arr = quineFindUsable(arr, needed)
    arr = useCovMatrix(arr, needed)

    # print(arr)
    return arr

def goQuine(tt, cir):
    i = 0
    ott = dict()
    ret = dict()
    minterm = list()
    for o in cir.__outputs__:
        for el in range(len(tt)):
            if tt[el][i] == 1:
                minterm.append(el)
        ret[i] = quineForOutput(cir.inputs(), minterm)
        minterm = []
        i = i + 1
    return ret

def goEspresso_external(tt, cir, exact = True):
    dfile = get_project_directory()
    tt_file = os.path.join(dfile, "temp", "espresso-tt.txt")
    if exact:
        type = '-Dexact'
    else:
        type = ''
    write_truth_table_to_espresso(tt, cir,  tt_file)

    ostype = "win32"
    exe = os.path.join(dfile, "utils", "bin", ostype, "espresso", "espresso.exe") + " " + type + " " + tt_file
    try:
        ret = subprocess.check_output(exe, shell=True).decode('UTF-8')
    except:
        print('ESPRESSO FAILED')
    lines = ret.splitlines()
    rows = lines[5 : 5 + int(lines[4][2:])]
    ins = []
    outs = []
    for row in rows:
        [i, o] = row.split(' ')
        ins.append(i.replace('-','X'))
        outs.append(o)
    data = {i:[] for i in range(cir.outputs())}
    for i in range(len(outs)):
        for j in range(cir.outputs()):
            if outs[i][j] == '1':
                data[j].append(ins[i])

    return data
