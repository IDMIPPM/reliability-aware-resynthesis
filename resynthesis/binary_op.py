# coding: utf-8
__author__ = 'IDM.IPPM (Mihail Myachikov)'

import itertools
import math

def choose(n, k):
    if 0 <= k <= n:
        ntok = 1
        ktok = 1
        for t in range(1, min(k, n - k) + 1):
            ntok *= n
            ktok *= t
            n -= 1
        return ntok // ktok
    else:
        return 0


def all_are_equal(seq):
    sample = None
    for elem in seq:
        if sample is None:
            sample = elem
        else:
            if elem != sample:
                return False
    return True


def num2vec(number, digits, base=2):
    vec = [0] * digits
    for i in range(digits):
        digit = number % base
        vec[i] = digit
        number //= base
        if not number:
            break
    return vec


def vec2num(vec, base=2):
    number = 0
    for digit in reversed(vec):
        number += digit
        number *= base
    return number // base


def number_bits(number, bits_indexes, N):
    number_vec = num2vec(number, N)
    number_vec = [number_vec[i] for i in bits_indexes]
    number = vec2num(number_vec)
    return number

def inv_32(x):
    return 0xffffffff ^ x

def inputs_combinations(inputs_number, capacity=32):

    degree = math.floor(math.log2(capacity))

    inputs = [[] for _ in range(degree)]

    for comb in itertools.product((0, 1), repeat=degree):
        for j in range(degree):
            inputs[-j-1].append(comb[j])

    inputs = list(map(lambda x: (vec2num(list(reversed(x))),), inputs))
    ones_capacity = 2 ** capacity - 1  # const 0b111..11

    if inputs_number > degree:
        inputs.extend([(0, ones_capacity)] * (inputs_number-degree))

    return itertools.product(*tuple(inputs[:inputs_number]))

def ones(n):
    result = 0
    while n:
        result += 1
        n &= n - 1

    return result
