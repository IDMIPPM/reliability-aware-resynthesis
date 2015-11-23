# coding: utf-8
__author__ = 'IDM.IPPM (Mihail Myachikov, Dmitry Telpukhov)'

import random
import time
from math import floor, ceil, log2, sqrt
from operator import mul, or_
from functools import reduce
from itertools import *
from fractions import Fraction
import copy

from numpy.polynomial import Polynomial
from numpy.polynomial.polynomial import polypow
from numpy.random import randint

from resynthesis.resynthesis_external_stats import external_reliability
from resynthesis.binary_op import *
import resynthesis.dynamic as d
import resynthesis as sa

def error_test(scheme, input_values, error):
    """
    :param scheme: Input logic scheme.
    :param input_values: Input combination.
    :param error: Error combination.
    :return: True if scheme has wrong output on input and error combinations.
    """
    nonerror = [0] * scheme.elements()
    if scheme.process(input_values, error) != scheme.process(input_values, nonerror):
        return True
    else:
        return False


def __normalize_array(arr):
    return list(map(lambda x: x * len(arr) / sum(arr), arr))


def __rand_bit(prob):
    """
    :param prob: Probability of 1.
    :return: 0 or 1 with respect to given probability.
    """
    r = random.random()
    if r < prob:
        return 1
    else:
        return 0


def rand_bit_vec(elements_number, prob=0.5):
    """
    :param elements_number: Lehgth of the output list.
    :param prob: Probability of 1.
    :return: List of random binary values with respect to given probability.
    """
    if prob == 0:
        rand_bit_vec = [0] * elements_number
    else:
        rand_bit_vec = [__rand_bit(prob) for _ in range(elements_number)]
    return rand_bit_vec


def distribution(scheme, tests=0):
    """
    :param scheme: Input scheme.
    :param tests: Number of tests. If 0(default), all tests will be performed.
    :return: Probabilities of every possible outputs combination.
    """
    dist = [0.0] * (2 ** scheme.outputs())
    errors = [0] * scheme.elements()
    if tests == 0 or tests > 2 ** scheme.inputs():
        tests = 2 ** scheme.inputs()
    for test in range(tests):
        if tests == 2 ** scheme.inputs():
            input_num = test
        else:
            input_num = random.randrange(2 ** scheme.inputs())
        input_values = num2vec(input_num, scheme.inputs())
        outputs = scheme.process(input_values, errors)
        output = vec2num(outputs)
        dist[output] += 1
    dist = [count / tests for count in dist]
    return dist


def distribution_by_outputs(dist):
    """
    :param dist: List of probabilities of scheme output combinations.
    :return: List of distribution probabilities of every single output (bit).
    """
    outputs = floor(log2(len(dist)))
    dist_by_outputs = [[0 for _ in range(2)] for _ in range(outputs)]

    for output_combination, prob in enumerate(dist):
        output_combination_vec = num2vec(output_combination, outputs)
        for output, bit in enumerate(output_combination_vec):
            dist_by_outputs[output][bit] += prob
    return dist_by_outputs


def __dependence(dist):
    outputs = floor(log2(len(dist)))
    dist_by_outputs = distribution_by_outputs(dist)
    dep = 0

    def dep_comb(output_comb):
        output_comb_vec = num2vec(output_comb, outputs)
        output_comb_prob_vec = [dist_by_outputs[output][bit] for output, bit in zip(range(outputs), output_comb_vec)]
        eps = abs(reduce(mul, output_comb_prob_vec, 1) - dist[output_comb])

        return eps

    for output_comb in range(outputs):
        dep += dep_comb(output_comb)

    return dep


def __permutation(scheme, tests=100000):
    dist = distribution(scheme, 10000)
    dist_by_outputs = distribution_by_outputs(dist)
    best_dep = __dependence(dist)
    best_perm = list(range(len(dist)))

    def perm_by_outputs(outputs, outputs_comb_perm):
        perm = [0] * 2 ** scheme.outputs()
        for i, comb in enumerate(perm):
            i_vec = num2vec(i, scheme.outputs())
            j = number_bits(i, outputs, scheme.outputs())
            outputs_comb_perm_vec = num2vec(outputs_comb_perm[j], len(outputs))
            for k, output in enumerate(outputs):
                i_vec[output] = outputs_comb_perm_vec[k]
            perm[i] = vec2num(i_vec)
        return perm

    for i in range(2, 3):
        for outputs in combinations(range(scheme.outputs()), i):
            for outputs_comb_perm in permutations(range(2 ** i)):
                print(outputs_comb_perm)
                perm = perm_by_outputs(outputs, outputs_comb_perm)
                perm_dist = [dist[j] for j in perm]
                current_dep = __dependence(perm_dist)
                if current_dep < best_dep:
                    best_dep = current_dep
                    best_perm = perm
                    print(best_perm)
                    print(best_dep)

    return best_perm, best_dep, __dependence(dist)


def reliability(scheme, tests=0):
    """
    :param scheme: Input scheme.
    :param tests: Number of tests. If 0 all possible tests will be performed.
    :return: Scheme COF characteristics.
    """
    reliability = 0.0
    if tests == 0 or tests > 2 ** scheme.inputs():
        tests = 2 ** scheme.inputs()

    for elem in range(scheme.elements()):
        error_number = 2 ** elem
        error = num2vec(error_number, scheme.elements())
        error_count = 0.0
        for test in range(tests):
            if tests == 2 ** scheme.inputs():
                input_num = test
            else:
                input_num = random.randrange(2 ** scheme.inputs())
            input_values = num2vec(input_num, scheme.inputs())
            if error_test(scheme, input_values, error):
                error_count += 1
        reliability += error_count / tests
    return reliability


def distribution_estim(scheme, nodes, tests=0):
    distr = [0 for i in range(2 ** len(nodes))]
    outs = copy.copy(scheme.__outputs__)
    scheme.__outputs__ = nodes
    if tests == 0 or tests > 2 ** scheme.inputs():
        tests = 2 ** scheme.inputs()
    for test in range(tests):
        if tests == 2 ** scheme.inputs():
            input_num = test
        else:
            input_num = random.randrange(2 ** scheme.inputs())
        input_values = num2vec(input_num, scheme.inputs())
        out = vec2num(scheme.process(input_values))
        distr[out] += 1/(tests)
    scheme.__outputs__ = outs
    return distr

# all possible errors for every input vector
def matrix_estim(scheme, nodes, tests=0):
    matrix = [[0 for _ in range(2**len(nodes))] for _ in range(2**len(nodes))]
    outs = copy.copy(scheme.__outputs__)
    scheme.__outputs__ += nodes

    if tests == 0 or tests > 2 ** scheme.inputs():
        tests = 2 ** scheme.inputs()
    for test in range(tests):
        if tests == 2 ** scheme.inputs():
            input_num = test
        else:
            input_num = random.randrange(2 ** scheme.inputs())
        input_values = num2vec(input_num, scheme.inputs())

        out = (scheme.process(input_values))
        ind1 = vec2num(out[len(outs):])

        matrix[ind1][ind1] += 1

        error = [0 for _ in scheme.element_labels()]
        #print('input - ', input_values, 'error vector - ', error)
        for err_pos in range(2**len(nodes)):
            err_val = num2vec(err_pos, len(nodes))

            for node in nodes:
                ind = sorted(scheme.__elements__.keys()).index(node)
                error[ind] = err_val[nodes.index(node)]

            #print('input - ', input_values, 'error vector - ', error)

            out_err = (scheme.process(input_values, error))
            if out[:len(outs)] != out_err[:len(outs)]:
                ind2 = vec2num(out_err[len(outs):])
                matrix[ind1][ind2] += 1

    for line in range(len(matrix)):
        norma = matrix[line][line]
        for elm in range(len(matrix[line])):
            if norma != 0:
                matrix[line][elm] /= norma


    scheme.__outputs__ = outs
    return matrix

# random error for every input vector
def matrix_estim_rnd(scheme, nodes, tests=0):
    matrix = [[0 for _ in range(2**len(nodes))] for _ in range(2**len(nodes))]
    total = [[0 for _ in range(2**len(nodes))] for _ in range(2**len(nodes))]
    outs = copy.copy(scheme.__outputs__)
    scheme.__outputs__ += nodes
    # MonteCarlo or BruteForce?
    if tests == 0 or tests > 2 ** scheme.inputs():
        tests = 2 ** scheme.inputs()
    for test in range(tests):
        if tests == 2 ** scheme.inputs():
            input_num = test
        else:
            input_num = random.randrange(2 ** scheme.inputs())
        input_values = num2vec(input_num, scheme.inputs())
        # Output evaluation
        out = (scheme.process(input_values))
        ind1 = vec2num(out[len(outs):])

        # Generate error vector
        err_pos = random.randrange(2**len(nodes))
        error = [0 for _ in scheme.element_labels()]
        err_val = num2vec(err_pos, len(nodes))
        # Setup errors in error vector
        for node in nodes:
            ind = sorted(scheme.__elements__.keys()).index(node)
            error[ind] = err_val[nodes.index(node)]
        out_err = (scheme.process(input_values, error))
        ind2 = vec2num(out_err[len(outs):])
        total[ind1][ind2] += 1
        if out[:len(outs)] != out_err[:len(outs)]: # if error is observable
            matrix[ind1][ind2] += 1
    # normalize matrix
    #print(total)
    #print(matrix)
    for line in range(len(matrix)):
        for elm in range(len(matrix[line])):
            if total[line][elm] != 0:
                matrix[line][elm] /= total[line][elm]
    scheme.__outputs__ = outs
    return matrix


# simultaneous estimation of all stats for subscheme
# random input - one random error (use it for MonteCarlo only)
def subscheme_stats_rnd(scheme, inp_nodes, out_nodes, tests=1000):
    matrix = [[0 for _ in range(2**len(out_nodes))] for _ in range(2**len(out_nodes))]
    total = [[0 for _ in range(2**len(out_nodes))] for _ in range(2**len(out_nodes))]
    distr = [0 for i in range(2 ** len(inp_nodes))]

    outs = copy.copy(scheme.__outputs__)
    scheme.__outputs__ += inp_nodes
    scheme.__outputs__ += out_nodes
    # MonteCarlo
    for test in range(tests):
        input_num = random.randrange(2 ** scheme.inputs())
        input_values = num2vec(input_num, scheme.inputs())
        # Output evaluation
        out = (scheme.process(input_values))
        distr[vec2num(out[len(outs):len(outs)+len(inp_nodes)])] += 1/(tests)
        ind1 = vec2num(out[len(outs)+len(inp_nodes):])

        # Generate error vector
        err_pos = random.randrange(2**len(out_nodes))
        error = [0 for _ in scheme.element_labels()]
        err_val = num2vec(err_pos, len(out_nodes))
        # Setup errors in error vector
        for node in out_nodes:
            ind = sorted(scheme.__elements__.keys()).index(node)
            error[ind] = err_val[out_nodes.index(node)]
        out_err = (scheme.process(input_values, error))
        ind2 = vec2num(out_err[len(outs)+len(inp_nodes):])
        total[ind1][ind2] += 1
        if out[:len(outs)] != out_err[:len(outs)]: # if error is observable
            matrix[ind1][ind2] += 1
    # normalize matrix
    for line in range(len(matrix)):
        for elm in range(len(matrix[line])):
            if total[line][elm] != 0:
                matrix[line][elm] /= total[line][elm]
    scheme.__outputs__ = outs
    return (distr, matrix)


# simultaneous estimation of all stats for subscheme
# random input - all possible values of output errors
def subscheme_stats(scheme, inp_nodes, out_nodes, tests=0):
    matrix = [[0 for _ in range(2**len(out_nodes))] for _ in range(2**len(out_nodes))]
    distr = [0 for i in range(2 ** len(inp_nodes))]
    outs = copy.copy(scheme.__outputs__)
    scheme.__outputs__ += inp_nodes
    scheme.__outputs__ += out_nodes
    # MonteCarlo or BruteForce?
    if tests == 0 or tests > 2 ** scheme.inputs():
        tests = 2 ** scheme.inputs()
    for test in range(tests):
        if tests == 2 ** scheme.inputs():
            input_num = test
        else:
            input_num = random.randrange(2 ** scheme.inputs())
        input_values = num2vec(input_num, scheme.inputs())

        out = (scheme.process(input_values))
        distr[vec2num(out[len(outs):len(outs)+len(inp_nodes)])] += 1/(tests)
        ind1 = vec2num(out[len(outs)+len(inp_nodes):])

        matrix[ind1][ind1] += 1

        error = [0 for _ in scheme.element_labels()]
        #print('input - ', input_values, 'error vector - ', error)
        for err_pos in range(2**len(out_nodes)):
            err_val = num2vec(err_pos, len(out_nodes))

            for node in out_nodes:
                ind = sorted(scheme.__elements__.keys()).index(node)
                error[ind] = err_val[out_nodes.index(node)]

            #print('input - ', input_values, 'error vector - ', error)

            out_err = (scheme.process(input_values, error))
            if out[:len(outs)] != out_err[:len(outs)]:
                ind2 = vec2num(out_err[len(outs)+len(inp_nodes):])
                matrix[ind1][ind2] += 1
    #out[:len(outs)]
    #out[len(outs):len(outs)+len(inp_nodes)]
    #out[len(outs)+len(inp_nodes):]

    for line in range(len(matrix)):
        norma = matrix[line][line]
        for elm in range(len(matrix[line])):
            if norma != 0:
                matrix[line][elm] /= norma
    scheme.__outputs__ = outs
    return (distr, matrix)


def vul_map(sch, tests=0):
    err_pos = 0
    vulnerability = {}
    if tests == 0 or tests > 2 ** sch.inputs():
        tests = 2 ** sch.inputs()
    for element in sorted(sch.__elements__.keys()):
        vulnerability[element] = 0
        error_values = [0 for _ in range(sch.elements())]
        error_values[err_pos] = 1

        for test in range(tests):
            if tests == (2 ** sch.inputs()):
                input_num = test
            else:
                input_num = random.randrange(2 ** sch.inputs())
            input_values = num2vec(input_num, sch.inputs())
            if sch.process(input_values) != sch.process(input_values, error_values):
                vulnerability[element] += 1/(tests)
        err_pos += 1
    return vulnerability


def vul_map_uneven(sch, arr, tests=0):
    err_pos = 0
    vulnerability = {}
    if tests == 0 or tests > 2 ** sch.inputs():
        tests = 2 ** sch.inputs()
    arr_norm = __normalize_array(arr)
    for element in sorted(sch.__elements__.keys()):
        vulnerability[element] = 0
        error_values = [0 for _ in range(sch.elements())]
        error_values[err_pos] = 1
        for test in range(tests):
            if tests == (2 ** sch.inputs()):
                input_num = test
            else:
                input_num = random.randrange(2 ** sch.inputs())
            input_values = num2vec(input_num, sch.inputs())
            if sch.process(input_values) != sch.process(input_values, error_values):
                vulnerability[element] += arr_norm[input_num]/(tests)
        err_pos += 1
    return vulnerability


def vul(sch, nodes, tests=0):
    err_pos_sub = 0
    vulnerability = 0
    count = 0
    tot = 0
    sub = sch.subscheme_by_outputs(nodes)
    if tests == 0 or tests > 2 ** sch.inputs():
        tests = 2 ** sch.inputs()
    for element in sorted(sub.__elements__.keys()):
        #vulnerability = 0
        error_values_sub = [0 for _ in range(sub.elements())]
        error_values_sub[err_pos_sub] = 1
        err_pos_sch = sorted(sch.__elements__.keys()).index(element)
        error_values_sch = [0 for _ in range(sch.elements())]
        error_values_sch[err_pos_sch] = 1

        for test in range(tests):
            tot += 1
            if tests == (2 ** sch.inputs()):
                input_num = test
            else:
                input_num = random.randrange(2 ** sch.inputs())
            input_values = num2vec(input_num, sch.inputs())
            input_values_sub = []
            #generating inputs for subcircuit
            for inp in sub.__inputs__:
                input_values_sub.append(input_values[sch.__inputs__.index(inp)])
            if (sub.process(input_values_sub) != sub.process(input_values_sub, error_values_sub)):
                count += 1
                if sch.process(input_values) != sch.process(input_values, error_values_sch):
                    vulnerability += 1

        err_pos_sub += 1
        print('out_errors = ', vulnerability)
        print('sub_errors = ', count)
        print('total tests = ', tot)
        print('=============================')
    return vulnerability/tot


def reliability_uneven(scheme, arr, tests=0):
    """
    :param scheme: Input scheme.
    :param tests: Number of tests. If 0 all possible tests will be performed.
    :return: Scheme COF characteristics.
    """
    if sum(arr) == 0:
        return external_reliability(scheme, tests-1)
    reliability = 0.0
    if tests == 0 or tests > 2 ** scheme.inputs():
        tests = 2 ** scheme.inputs()
    if len(arr) != 2 ** (scheme.inputs()):
        return 0
    for elem in range(scheme.elements()):
        error_number = 2 ** elem
        error = num2vec(error_number, scheme.elements())
        error_count = 0.0
        for test in range(tests):
            if tests == 2 ** scheme.inputs():
                input_num = test
            else:
                input_num = random.randrange(2 ** scheme.inputs())
            input_values = num2vec(input_num, scheme.inputs())
            if error_test(scheme, input_values, error):

                error_count += arr[input_num]
        reliability += error_count
    return reliability


def reliability_uneven2(scheme, sub_stats, tests=0):
    (distr, matrix) = sub_stats
    if sum(distr) == 0:
        return external_reliability(scheme, tests-1)
    reliability = 0.0
    if tests == 0 or tests > 2 ** scheme.inputs():
        tests = 2 ** scheme.inputs()
    if len(distr) != 2 ** (scheme.inputs()):
        return 0
    for elem in range(scheme.elements()):
        error_number = 2 ** elem
        error = num2vec(error_number, scheme.elements())
        error_count = 0.0
        for test in range(tests):
            if tests == 2 ** scheme.inputs():
                input_num = test
            else:
                input_num = random.randrange(2 ** scheme.inputs())
            input_values = num2vec(input_num, scheme.inputs())
            etalon = scheme.process(input_values)
            with_err = scheme.process(input_values, error)
            if etalon != with_err:

                error_count += distr[input_num]*matrix[vec2num(etalon)][vec2num(with_err)]
                # print("Input vec: {}, Etalon vec: {}, Err vec: {}, Distr: {} Matrix: {}".format(input_num, vec2num(etalon), vec2num(with_err), distr[input_num], matrix[vec2num(etalon)][vec2num(with_err)]))
                #print(arr[input_num], '*', matrix[vec2num(etalon)][vec2num(with_err)])
                #print('+')
        reliability += error_count
    return reliability


def error_stat_uneven(scheme, arr, tests=0):
    statistic = {}
    if sum(arr) == 0:
        arr = [1 for _ in arr]
    if tests == 0 or tests > 2 ** scheme.inputs():
        tests = 2 ** scheme.inputs()
    if len(arr) != 2 ** (scheme.inputs()):
        return 0
    arr_norm = __normalize_array(arr)
    for elem in range(scheme.elements()):
        error_number = 2 ** elem
        error = num2vec(error_number, scheme.elements())
        error_count = 0.0
        for test in range(tests):
            if tests == 2 ** scheme.inputs():
                input_num = test
            else:
                input_num = random.randrange(2 ** scheme.inputs())
            input_values = num2vec(input_num, scheme.inputs())
            etalon = scheme.process(input_values)
            with_error = scheme.process(input_values, error)
            if (etalon != with_error) & (arr_norm[input_num] != 0):
                if (etalon, with_error) in statistic:
                    statistic[(etalon, with_error)] += arr_norm[input_num]/tests
                else:
                    statistic[(etalon, with_error)] = arr_norm[input_num]/tests

    return statistic


def compensate(scheme, err_stat, tests=0):
    res = []
    mask_stat = {i:0 for i in err_stat}
    main_inps = len(next(iter(err_stat))[0])
    rest_inps = scheme.inputs() - main_inps
    if tests == 0 or tests > 2 ** rest_inps:
        tests = 2 ** rest_inps
    for probe in err_stat:
        for test in range(tests):
            if tests == 2 ** rest_inps:
                input_num = test
            else:
                input_num = random.randrange(2 ** rest_inps)
            input_values = tuple(num2vec(input_num, rest_inps))
            etalon = scheme.process(probe[0] + input_values)
            with_error = scheme.process(probe[1] + input_values)
            if etalon != with_error:
                mask_stat[probe] += 1
        mask_stat[probe] /= tests
        res.append(mask_stat[probe]*err_stat[probe])
    #print(mask_stat)
    return (sum(res))


def subscheme_by_inputs(scheme, nodes):
    sub = sa.scheme_alt()
    sub.__inputs__ = copy.copy(nodes)
    interarr = copy.copy(nodes)
    input_nodes = []

    while interarr != []:
        label = interarr.pop()
        if (label in scheme.__outputs__) & (label not in sub.__outputs__):
            sub.__outputs__.append(label)
        for element in scheme.__elements__:
            if label in scheme.__elements__[element][1]:
                sub.__elements__[element] = copy.deepcopy(scheme.__elements__[element])
                input_nodes.append(sub.__elements__[element][1][0])
                if sub.__elements__[element][0] not in ['INV', 'BUF', 'VCC', 'GND']:
                    input_nodes.append(sub.__elements__[element][1][1])
                interarr.append(element)

    for input in input_nodes:
        if input not in sub.all_labels():
            sub.__inputs__.append(input)

    return sub


def eof(scheme, tests=10000, prob=None):
    """
    :param scheme: Input scheme.
    :param tests: Number of tests.
    :param prob: Probability of error in single element. If None, prob will be set on 1 / scheme.elements().
    :return: Probability of scheme failure.
    """
    if prob is None:
        prob = 1 / scheme.elements()
    elements_number = scheme.elements()
    error_count = 0

    start = time.time()
    speed = 0
    while (time.time() - start) < 1:
        error = rand_bit_vec(elements_number, prob)
        input_values = rand_bit_vec(scheme.inputs())
        error_test(scheme, input_values, error)
        speed += 1

    print("estimated test time: ", tests / speed)

    for test in range(tests):
        error = rand_bit_vec(elements_number, prob)
        input_values = rand_bit_vec(scheme.inputs())
        if error_test(scheme, input_values, error):
            error_count += 1
    eof = error_count / tests

    return eof


def cof(scheme, tests=10000, prob=None):
    """
    :param scheme: Input scheme.
    :param tests: Number of tests.
    :param prob: Probability of error in single element. If None, prob will be set on 1 / scheme.elements().
    :return: Probability of scheme non-failure.
    """
    return 1 - eof(scheme, tests, prob)


def transition_table_p(sch, indexes=None, max_degree=None, debug=False):
    """
    :param sch: Input scheme.
    :param indexes: Indexes of scheme outputs.
    :return: Table of probabilities (k coefficient in k*p + O(p)) of transition form one output combination to another.
    """
    n = sch.inputs()
    l = sch.elements()
    m = sch.outputs()

    if indexes is None:
        ttable_size = 2 ** sch.outputs()
        indexes = range(m)
    else:
        ttable_size = 2 ** len(indexes)

    if max_degree is None or max_degree > l:
        max_degree = l

    ttable = [[[0 for _ in range(max_degree + 1)] for _ in range(ttable_size)] for _ in range(ttable_size)]
    nonerror = [0] * l

    tests = 2 ** n
    errors = 2 ** l

    sch_process = d.make_process_func(sch)

    start = time.time()
    counter = 0
    while time.time() - start < 5:
        output_true = sch_process((0,) * n, (0,) * l)
        vec2num(output_true)
        vec2num(output_true)
        counter += 1
    process_time = (time.time() - start) / counter

    inputs = 2 ** n
    errors = sum(choose(l, degree) for degree in range(max_degree + 1))
    estimated_time = process_time * inputs * errors
    print('Estimated time: ', estimated_time)

    for input_values in product(range(2), repeat=n):
        if debug:
            print(input_values)
        output_true = sch_process(input_values, nonerror)
        if len(indexes) < m:
            output_true = [output_true[index] for index in indexes]
        for degree in range(max_degree + 1):
            for error_comb in combinations(range(l), degree):
                error_vec = [0] * l
                for i in error_comb:
                    error_vec[i] = 1
                if len(indexes) < m:
                    output_error = [sch_process(input_values, error_vec)[index] for index in indexes]
                else:
                    output_error = sch_process(input_values, error_vec)
                true_index = vec2num(output_true)
                error_index = vec2num(output_error)
                for i in range(degree, max_degree + 1):
                    ttable[true_index][error_index][i] += choose(l - degree, i - degree) * (-1) ** (i - degree) / (
                        2 ** n)

    return ttable


def min_transition_table_p(sch, indexes=None, max_degree=None, debug=False):
    """
    :param sch: Input scheme.
    :param indexes: Indexes of scheme outputs.
    :return: Table of probabilities (k coefficient in k*p + O(p)) of transition form one output combination to another.
    """
    n = sch.inputs()
    l = sch.elements()
    m = sch.outputs()

    if indexes is None:
        ttable_size = 2 ** sch.outputs()
        indexes = range(m)
    else:
        ttable_size = 2 ** len(indexes)

    if max_degree is None or max_degree > l:
        max_degree = l

    ttable = [[[0 for i in range(l + 1)] for x in range(ttable_size)] for y in range(ttable_size)]
    nonerror = [0] * l

    tests = 2 ** n
    errors = 2 ** l

    sch_process = d.make_process_func(sch)

    start = time.time()
    counter = 0
    while time.time() - start < 5:
        output_true = sch_process((0,) * n, (0,) * l)
        vec2num(output_true)
        vec2num(output_true)
        counter += 1
    process_time = (time.time() - start) / counter

    inputs = 2 ** n
    errors = sum(choose(l, degree) for degree in range(max_degree + 1))
    estimated_time = process_time * inputs * errors
    print('Estimated time: ', estimated_time)

    for input_values in product(range(2), repeat=n):
        if debug:
            print(input_values)
        output_true = sch_process(input_values, nonerror)
        if len(indexes) < m:
            output_true = [output_true[index] for index in indexes]
        for degree in range(max_degree):
            for error_comb in combinations(range(l), degree):
                error_vec = [0] * l
                for i in error_comb:
                    error_vec[i] = 1
                if len(indexes) < m:
                    output_error = [sch_process(input_values, error_vec)[index] for index in indexes]
                else:
                    output_error = sch_process(input_values, error_vec)
                true_index = vec2num(output_true)
                error_index = vec2num(output_error)
                for i in range(degree, l):
                    ttable[true_index][error_index][i] += choose(l - degree, i - degree) * (-1) ** (i - degree) / (
                        2 ** n)

    return ttable


def max_transition_table_p(sch, indexes=None, max_degree=None, debug=False):
    """
    :param sch: Input scheme.
    :param indexes: Indexes of scheme outputs.
    :return: Table of probabilities (k coefficient in k*p + O(p)) of transition form one output combination to another.
    """
    n = sch.inputs()
    l = sch.elements()
    m = sch.outputs()

    if indexes is None:
        ttable_size = 2 ** sch.outputs()
        indexes = range(m)
    else:
        ttable_size = 2 ** len(indexes)

    if max_degree is None or max_degree > l:
        max_degree = l

    ttable = [[[0 for i in range(l + 1)] for x in range(ttable_size)] for x in range(ttable_size)]
    nonerror = [0] * l

    tests = 2 ** n
    errors = 2 ** l

    sch_process = d.make_process_func(sch)

    start = time.time()
    counter = 0
    while time.time() - start < 5:
        output_true = sch_process((0,) * n, (0,) * l)
        vec2num(output_true)
        vec2num(output_true)
        counter += 1
    process_time = (time.time() - start) / counter

    inputs = 2 ** n
    errors = sum(choose(l, degree) for degree in range(max_degree + 1))
    estimated_time = process_time * inputs * errors
    print('Estimated time: ', estimated_time)

    for input_values in product(range(2), repeat=n):
        if debug:
            print(input_values)
        output_true = sch_process(input_values, nonerror)
        if len(indexes) < m:
            output_true = [output_true[index] for index in indexes]
        for degree in range(max_degree):
            for error_comb in combinations(range(l), degree):
                error_vec = [0] * l
                for i in error_comb:
                    error_vec[i] = 1
                if len(indexes) < m:
                    output_error = [sch_process(input_values, error_vec)[index] for index in indexes]
                else:
                    output_error = sch_process(input_values, error_vec)
                true_index = vec2num(output_true)
                error_index = vec2num(output_error)
                for i in range(degree, max_degree + 1):
                    ttable[true_index][error_index][i] += choose(l - degree, i - degree) * (-1) ** (i - degree) / (
                        2 ** n)
        for degree in range(max_degree, l + 1):
            pass
    return ttable


def transition_table(sch, tests=100000, prob=0.001, indexes=None):
    """
    :param sch: Input scheme.
    :param tests: Number of tests.
    :param prob: Probability of error in single element.
    :param indexes: Indexes of scheme outputs.
    :return: Table of probabilities (k coefficient in k*p + O(p)) of transition form one output combination to another.
    """
    if indexes is None:
        n = 2 ** sch.outputs()
    else:
        n = 2 ** len(indexes)

    ttable = [[0 for x in range(n)] for x in range(n)]
    nonerror = [0] * sch.elements()

    for test in range(tests):
        input_values = rand_bit_vec(sch.inputs())

        error = rand_bit_vec(sch.elements(), prob)
        output_true = vec2num(sch.process(input_values, nonerror))
        output_error = vec2num(sch.process(input_values, error))

        if indexes is not None:
            output_true = number_bits(output_true, indexes, sch.outputs())
            output_error = number_bits(output_error, indexes, sch.outputs())

        ttable[output_true][output_error] += 1 / tests

    return ttable


def __allowed_transitions_probability(ttable):
    prob = 0
    allowed = [i for i in range(len(ttable)) if sum(ttable[i]) > 0]
    for i in allowed:
        for j in allowed:
            if i != j:
                prob += ttable[i][j]
    return prob


def eof_p(sch, max_degree=None, debug=False):
    """
    :param sch: Input scheme.
    :param max_degree: Max degree of result polinomial.
    :param debug: If True debug information will be printed due to process.
    :return: First max_degree+1 members of polinomial EOF(p) for input scheme.
    """
    n = sch.inputs()
    m = sch.elements()

    nonerror = (0,) * m

    if max_degree is None:
        max_degree = m

    sch_process = d.make_process_func(sch)
    if debug:
        start = time.time()
        counter = 0
        while time.time() - start < 1:
            output_true = sch_process((0,) * n, (0,) * m)
            vec2num(output_true)
            vec2num(output_true)
            counter += 1
        process_time = (time.time() - start) / counter

        inputs = 2 ** n
        errors = sum(choose(m, degree) for degree in range(max_degree + 1))
        estimated_time = process_time * inputs * errors
        print('Estimated time eof_p: ', estimated_time)

    polynomial = [Fraction(0, 1)] * (max_degree + 1)
    sch_process = d.make_process_func(sch)
    for input_values in product(range(2), repeat=n):
        if debug:
            print(input_values)
        for degree in range(max_degree + 1):
            for error_comb in combinations(range(m), r=degree):
                error_vec = [0] * m
                for i in error_comb:
                    error_vec[i] = 1
                if sch_process(input_values, error_vec) != sch_process(input_values, nonerror):
                    for i in range(degree, max_degree + 1):
                        polynomial[i] += choose(m - degree, i - degree) * (-1) ** (i - degree)
    polynomial = [coeff / 2 ** n for coeff in polynomial]
    while not polynomial[-1]:
        polynomial.pop()
    return polynomial


def max_eof_p(sch, max_degree=None, debug=False, max_tests=None):
    """
    :param sch: Input scheme.
    :param max_degree: Max degree of result polinomial.
    :param debug: If True debug information will be printed due to process.
    :return:  Upper bound of probability of failure with up to max_degree-1 errors in scheme.
    """
    n = sch.inputs()
    m = sch.elements()

    nonerror = (0,) * m

    if max_degree is None:
        max_degree = m

    sch_process = d.make_process_func(sch)
    if debug:
        start = time.time()
        counter = 0
        while time.time() - start < 1:
            output_true = sch_process((0,) * n, (0,) * m)
            vec2num(output_true)
            vec2num(output_true)
            counter += 1
        process_time = (time.time() - start) / counter

        inputs = 2 ** n
        errors = sum(choose(m, degree) for degree in range(max_degree + 1))
        estimated_time = process_time * inputs * errors
        print('Estimated time eof_p: ', estimated_time)

    polinomial = [Fraction(0, 1)] * (m + 1)
    sch_process = d.make_process_func(sch)
    for input_values in product(range(2), repeat=n):
        if debug:
            print(input_values)
        for degree in range(max_degree):
            for error_comb in combinations(range(m), degree):
                error_vec = [0] * m
                for i in error_comb:
                    error_vec[i] = 1
                if sch_process(input_values, error_vec) != sch_process(input_values, nonerror):
                    for i in range(degree, m + 1):
                        polinomial[i] += choose(m - degree, i - degree) * (-1) ** (i - degree)
    polinomial = [coeff / 2 ** n for coeff in polinomial]
    for degree in range(max_degree, m + 1):
        for i in range(degree, m + 1):
            polinomial[i] += choose(m, degree) * choose(m - degree, i - degree) * (-1) ** (i - degree)

    return polinomial


def min_eof_p(sch, max_degree=None, debug=False):
    """
    :param sch: Input scheme.
    :param max_degree: Max degree of result polinomial.
    :param debug: If True debug information will be printed due to process.
    :return: Lower bound of probability of failure with up to max_degree-1 errors in scheme.
    """
    n = sch.inputs()
    m = sch.elements()

    nonerror = (0,) * m

    if max_degree is None:
        max_degree = m

    sch_process = d.make_process_func(sch)
    if debug:
        start = time.time()
        counter = 0
        while time.time() - start < 1:
            output_true = sch_process((0,) * n, (0,) * m)
            vec2num(output_true)
            vec2num(output_true)
            counter += 1
        process_time = (time.time() - start) / counter

        inputs = 2 ** n
        errors = sum(choose(m, degree) for degree in range(max_degree + 1))
        estimated_time = process_time * inputs * errors
        print('Estimated time eof_p: ', estimated_time)

    polinomial = [Fraction(0, 1)] * (m + 1)
    sch_process = d.make_process_func(sch)
    for input_values in product(range(2), repeat=n):
        if debug:
            print(input_values)
        for degree in range(max_degree):
            for error_comb in combinations(range(m), r=degree):
                error_vec = [0] * m
                for i in error_comb:
                    error_vec[i] = 1
                if sch_process(input_values, error_vec) != sch_process(input_values, nonerror):
                    for i in range(degree, m + 1):
                        polinomial[i] += choose(m - degree, i - degree) * (-1) ** (i - degree)
    polinomial = [coeff / 2 ** n for coeff in polinomial]
    return polinomial


def eof_p_opt(sch, max_degree=None, debug=False, capacity=None):
    """
    :param sch: Input scheme.
    :param max_degree: Max degree of result polinomial.
    :param debug: If True debug information will be printed due to process.
    :return: First max_degree+1 members of polinomial EOF(p) for input scheme.
    """
    n = sch.inputs()
    m = sch.elements()

    if capacity is None:
        capacity = min([2 ** sch.inputs(), 32])

    nonerror = (0,) * m

    if max_degree is None:
        max_degree = m

    sch_process = d.make_process_func(sch, capacity=capacity)

    if debug:
        start = time.time()
        counter = 0
        while time.time() - start < 1:
            output_true = sch_process((0,) * n, (0,) * m)
            vec2num(output_true)
            vec2num(output_true)
            counter += 1
        process_time = (time.time() - start) / counter

        inputs = 2 ** n / capacity
        errors = sum(choose(m, degree) for degree in range(max_degree + 1))
        estimated_time = process_time * inputs * errors
        print('Estimated time eof_p: ', estimated_time)

    poly = Polynomial([Fraction(0, 1)])
    input_prob = Fraction(1, 2 ** n)
    p = Polynomial([Fraction(0, 1), Fraction(1, 1)])
    sum_poly = Polynomial([Fraction(0, 1)])
    for input_values in inputs_combinations(n, capacity=capacity):
        output_true = sch_process(input_values, nonerror)
        if debug:
            print(input_values)
        for degree in range(max_degree + 1):
            error_prob = Polynomial(polypow(p.coef, degree, maxpower=100)) * Polynomial(
                polypow((1 - p).coef, m - degree, maxpower=100))
            # print(error_prob.coef)
            errors_number = 0
            if debug:
                print(len(list(combinations(range(m), r=degree))))
            for error_comb in combinations(range(m), r=degree):
                error_vec = [0] * m
                for i in error_comb:
                    error_vec[i] = 2 ** capacity - 1
                output_error = sch_process(input_values, error_vec)
                errors = [i ^ j for i, j in zip(output_true, output_error)]
                errors_number += ones(reduce(or_, errors))
            if debug:
                print(errors_number)
            if errors_number:
                poly += errors_number * input_prob * error_prob
    result = list(poly.coef)
    # removing trailing zeros
    while not result[-1]:
        result.pop()
    return result


def eof_p_interval(sch, max_degree=None, debug=False, max_tests=None):
    """
    :param sch: Input scheme.
    :param max_degree: Max degree of result polinomial.
    :param debug: If True debug information will be printed due to process.
    :param capacity: Number of bits in used numbers.
    :param max_tests: Maximum number of tests to process.
    :return: First max_degree+1 members of polinomial EOF(p) for input scheme.
    """

    tests_performed = 0

    n = sch.inputs()
    m = sch.elements()

    sch_process = d.make_process_func(sch)

    nonerror = (0,) * m

    min_polynomial = [Fraction(0, 1)] * (m+1)
    max_polynomial = [Fraction(1, 1)] + [Fraction(0, 1)] * m

    if max_degree is None:
        max_degree = m

    if max_tests is None or max_tests >= 2 ** (n + m):
        max_tests = 2 ** (n + m)

    def inputs_generator(rand=False):
        if rand:
            return product(*[random.choice(((0, 1), (1, 0))) for _ in range(n)])
        else:
            return product((0, 1), repeat=n)

    def make_errors_vector(indexes):
        errors_vector = [0] * m
        for index in indexes:
            errors_vector[index] = 1
        return tuple(errors_vector)

    def errors_generator(degree, rand=False):
        if rand:
            return (make_errors_vector(indexes=combination) for combination in combinations(random.sample(list(range(m)), m), r=degree))
        else:
            return (make_errors_vector(indexes=combination) for combination in combinations(list(range(m)), r=degree))

    def update_polynomials(successes, fails, degree):
        for i in range(m+1-degree):
            min_polynomial[i+degree] += Fraction((-1) ** i * choose(m-degree, i) * fails, 2**n)
            max_polynomial[i+degree] -= Fraction((-1) ** i * choose(m-degree, i) * successes, 2**n)

    for degree in range(max_degree+1):
        tests_remained = max_tests - tests_performed
        if debug:
            print(max_tests, tests_remained)
        rand = tests_remained < choose(m, degree) * 2 ** n
        errors_number = choose(m, degree)
        if rand:
            inputs_number = max(1, min(int(tests_remained / errors_number), 2 ** n))
        else:
            inputs_number = 2 ** n

        total_fails = 0
        total_successes = 0

        for errors in errors_generator(degree, rand):
            if not tests_remained:
                return min_polynomial, max_polynomial
            inputs_number = min(inputs_number, tests_remained)
            fails = sum(sch_process(inputs, errors) != sch_process(inputs) for inputs in islice(inputs_generator(rand), inputs_number))
            successes = inputs_number - fails
            total_fails += fails
            total_successes += successes
            tests_remained -= inputs_number
            tests_performed += inputs_number

        update_polynomials(total_successes, total_fails, degree)

    return min_polynomial, max_polynomial


def __transition_table_reduce(ttable, indexes):
    indexes.sort()

    n = floor(log2(len(ttable)))
    m = len(indexes)
    reduced_table = [[0] * (2 ** m) for i in range(2 ** m)]

    for i, row in enumerate(ttable):
        for j, elem in enumerate(row):
            k = number_bits(i, indexes, n)
            l = number_bits(j, indexes, n)
            reduced_table[k][l] += elem

    return reduced_table


def __transition_probability(result, observations, ttable):
    trans_prob = 1
    result_row = ttable[result]
    result_prob = sum(result_row)
    if result_prob == 0:
        return 0
    result_row = [elem / result_prob for elem in result_row]
    for i in observations:
        trans_prob *= result_row[i]

    # print("trans_pr ", trans_prob * result_prob)
    return trans_prob * result_prob


def __observations_probability(observations, ttable):
    observations_prob = 0

    for result, row in enumerate(ttable):
        result_prob = sum(row)
        if result_prob != 0:
            observations_condition_prob = [row[observation] / result_prob for observation in observations]
            observations_condition_prob = reduce(mul, observations_condition_prob, 1)
            observations_prob += result_prob * observations_condition_prob

    # print("observ_pr ", observations_prob)
    return observations_prob


def __most_probable_result(observations, ttable):
    max_probability = 0
    best_result = __major_result(observations)
    observ_prob = __observations_probability(observations, ttable)
    if observ_prob == 0:
        return best_result
    for i, row in enumerate(ttable):
        current_probability = __transition_probability(i, observations, ttable) / observ_prob
        if current_probability > max_probability:
            max_probability = current_probability
            best_result = i
    # print("max_prob: ", max_probability)
    return best_result


def optimal_voter_truth_table(ttable, redundancy):
    """
    :param ttable: Transition table of input scheme.
    :param redundancy: Redundancy of result voter.
    :return: Truth table for optimal voter.
    """
    outputs = floor(log2(len(ttable)))

    output_combinations = 2 ** outputs
    voter_combinations = 2 ** (outputs * redundancy)

    truth_table = [0 for i in range(voter_combinations)]

    for i in range(voter_combinations):
        observations = num2vec(i, redundancy, output_combinations)
        most_prob = __most_probable_result(observations, ttable)
        truth_table[i] = most_prob

    truth_table = [num2vec(elem, outputs) for elem in truth_table]

    return truth_table


def __major_result(observations):
    n = ceil(log2(max(observations) + 1)) + 1

    vec_observations = [num2vec(observation, n) for observation in observations]

    def sum_lists(list1, list2):
        return [x1 + x2 for x1, x2 in zip(list1, list2)]

    result = reduce(sum_lists, vec_observations, [0] * n)

    def more_than(number, threshold):
        if number > threshold:
            return 1
        else:
            return 0

    result = [more_than(number, len(observations) / 2) for number in result]
    result = vec2num(result)

    return result


def standard_voter_truth_table(outputs, redundancy):
    """
    :param redundancy: Redundancy of result voter.
    :return: Truth table for standard major voter.
    """
    output_combinations = 2 ** outputs
    voter_combinations = 2 ** (outputs * redundancy)

    truth_table = [0 for i in range(voter_combinations)]
    for i in range(voter_combinations):
        observations = num2vec(i, redundancy, output_combinations)
        major = __major_result(observations)
        truth_table[i] = major

    truth_table = [num2vec(elem, outputs) for elem in truth_table]

    return truth_table


def __voter_prediction_error_prob(observations, prediction, ttable):
    error_prob = 0
    for result, row in enumerate(ttable):
        if result != prediction:
            result_prob = sum(row)
            if result_prob != 0:
                conditional_probs = [row[observation] / result_prob for observation in observations]
                error_prob += result_prob * reduce(mul, conditional_probs, 1)
    return error_prob


def __voter_error_prob(ttable, truth_table):
    error_prob = 0
    outputs_number = floor(log2(len(ttable)))
    redundancy = floor(log2(len(truth_table)) / outputs_number)
    truth_table = map(vec2num, truth_table)
    for i, prediction in enumerate(truth_table):
        observations = num2vec(i, redundancy, 2 ** outputs_number)
        error_prob += __voter_prediction_error_prob(observations, prediction, ttable)
    return error_prob


def most_connected_outputs(sch, outputs_to_choose, redundancy=3, p=0.001):
    """
    :param sch: Input scheme.
    :param outputs_to_choose: Number of connected outputs.
    :param redundancy: Redundancy.
    :param p: Probability of error in single element.
    :return: Indexes of outputs_to_choose most correlated outputs.
    """
    outputs_number = sch.outputs()
    # lazy implemenatation
    voter_error_min_prob = 1
    best_comb = list(range(outputs_to_choose))
    for outputs_comb in map(list, combinations(range(outputs_number), outputs_to_choose)):
        print(outputs_comb)
        table_reduce = transition_table(sch, tests=1000, prob=p, indexes=outputs_comb)

        opt_tr = optimal_voter_truth_table(table_reduce, redundancy)
        st_tr = standard_voter_truth_table(outputs_to_choose, redundancy)

        voter_error_current_prob = __voter_error_prob(table_reduce, opt_tr)

        if voter_error_current_prob < voter_error_min_prob:
            voter_error_min_prob = voter_error_current_prob
            best_comb = outputs_comb

    table_reduce = transition_table(sch, tests=1000, prob=0.01, indexes=best_comb)
    opt_tr = optimal_voter_truth_table(table_reduce, redundancy)
    st_tr = standard_voter_truth_table(outputs_to_choose, redundancy)
    voter_error_min_prob_st = __voter_error_prob(table_reduce, st_tr)

    print("best combination ", best_comb)
    print("voter_error_min_prob ", voter_error_min_prob)
    print("voter_error_min_prob_st ", voter_error_min_prob_st)
    if voter_error_min_prob != 0:
        print("diff ", voter_error_min_prob_st / voter_error_min_prob)

    return best_comb


def entropy(sch, tests=None):
    """
    :param sch: Input scheme.
    :param tests: Number of tests.
    :return: Entropy of output combinations of scheme.
    """

    def xlog2x(x):
        return x * log2(x)

    if tests is None or tests > 2 ** sch.inputs():
        tests = 2 ** sch.inputs()
        inputs = product([0, 1], repeat=sch.inputs())
    else:
        inputs = (randint(0, 2, sch.inputs()) for _ in range(tests))
    bins = dict()
    for input_values in inputs:
        output = vec2num(sch.process(input_values))
        if output not in bins:
            bins[output] = 1
        else:
            bins[output] += 1

    return -sum([xlog2x(value / tests) for value in bins.values()])


def correlation_multiout(sch1, sch2):  # compares correlation between two circuits (0% - 100%)
    if sch1.inputs() != sch2.inputs():
        return False
    if sch1.outputs() != sch2.outputs():
        return False
    correl = 0
    capacity = min(32, 2 ** sch1.inputs())
    mask = 2 ** capacity - 1
    sch1_func = d.make_process_func(sch1, capacity=capacity)
    sch2_func = d.make_process_func(sch2, capacity=capacity)
    n = sch1.inputs()
    for i in inputs_combinations(sch1.inputs(), capacity=capacity):
        output = (mask ^ out1 ^ out2 for out1, out2 in zip(sch1_func(i), sch2_func(i)))
        correl += sum(map(ones, output))
    correl /= (2 ** n * sch1.outputs())
    return correl


def scheme_cmp(sch1, sch2):  # compares equality of functions of two circuits
    if sch1.inputs() != sch2.inputs():
        return False
    n = sch1.inputs()
    for i in product((0, 1), repeat=n):
        if sch1.process(i) != sch2.process(i):
            return False
    return True
