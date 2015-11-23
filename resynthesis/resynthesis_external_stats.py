# coding: utf-8
__author__ = 'IDM.IPPM (Roman Solovyev)'

import subprocess
import re
import os
import sys

def get_project_directory():
    project_directory = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return project_directory

# Call external program (very fast) to calculate vulnerability map for circuit
# If iter1 == -1 then use full search. Give an error if number of inputs > 31
def external_vulnerability_map(circuit, iter1 = 10000):
    """
    :param circuit_file: File with logic scheme
    :param iter1: Iteration number.
    :return: Reliability value for every cell in circuit as float.
    """
    dfile = get_project_directory()
    circuit_file = os.path.join(dfile, "temp", "tmp_vmap_scheme.txt")
    if os.path.isfile(circuit_file):
        os.remove(circuit_file)
    vulner_file = os.path.join(dfile, "temp", "tmp_vmap_values.txt")
    if os.path.isfile(vulner_file):
        os.remove(vulner_file)
    circuit.print_circuit_in_file(circuit_file)
    if 2**circuit.inputs() < iter1:
        iter1 = -1

    vulnerability = {}
    ostype = "win32"
    exe = os.path.join(dfile, "utils", "bin", ostype, "vulnerability_map.exe") + " " + circuit_file + " " + vulner_file + " " + iter1.__str__()
    try:
        ret = subprocess.check_output(exe, shell=True).decode('UTF-8')
        r = re.compile('[ \t\n\r]+')
        f = open(vulner_file, 'r')
        reli = float(f.readline())
        num_lines = int(f.readline())
        for i in range(num_lines):
            dt = f.readline().split()
            vulnerability[dt[0]] = float(dt[1])

        f.close()
    except:
        reli = 100000000000.0

    return reli, vulnerability

# Call external program (very fast) to calculate reliability
# If iter1 == -1 then use full search. Give an error if number of inputs > 31
def external_reliability(circuit, iter1 = 10000):
    """
    :param circuit_file: File with logic scheme
    :param iter: Iteration number.
    :return: Reliability value for circuit as float.
    """
    val = external_vulnerability_map(circuit, iter1)
    if val[0]:
        return val[0]
    else:
        return 100000000000.0

def distribution_estim_external(circuit, inputs1, outputs1, iter1 = 10000):
    """
    :param circuit_file: File with logic scheme
    :param iter: Iteration number.
    :return: Reliability value for circuit as float.
    """

    if len(outputs1) > 12:
        print("Too many outputs! {}".format(len(outputs1)))
        return ([], [])

    # suffix = uuid.uuid4().__str__()
    dfile = get_project_directory()
    suffix = "_"
    circuit_file = os.path.join(dfile, "temp", "tmp" + suffix + ".txt")
    nodes_file = os.path.join(dfile, "temp", "tmp_internal_nodes" + suffix + ".txt")
    output_vals_file = os.path.join(dfile, "temp", "tmp_distr_result" + suffix + ".txt")

    if os.path.isfile(circuit_file):
        os.remove(circuit_file)
    if os.path.isfile(nodes_file):
        os.remove(nodes_file)
    if os.path.isfile(output_vals_file):
        os.remove(output_vals_file)

    circuit.print_circuit_in_file(circuit_file)
    f = open(nodes_file, 'w')
    f.write(str(len(inputs1)) + ' ' + ' '.join(inputs1) + '\n')
    f.write(str(len(outputs1)) + ' ' + ' '.join(outputs1) + '\n')
    f.close()

    # Choose exe file to run
    default_exe = "distrib_estim_mt.exe"
    if sys.maxsize > 2**32:
        default_exe = "distrib_estim_mt.exe"
    else:
        default_exe = "distrib_estim_mt.exe"

    ostype = "win32"
    exe = os.path.join(dfile, "utils", "bin", ostype, default_exe) + " " + circuit_file + " " + nodes_file + " " + output_vals_file + " " + iter1.__str__()
    try:
        ret = subprocess.check_output(exe, shell=True).decode('UTF-8')
        r = re.compile('[ \t\n\r]+')
        f = open(output_vals_file, 'r')
        distr = f.readline().split()
        distr = list(map(float, distr))
        matrix = [[] for i in range(1 << len(outputs1))]
        for i in range(1 << len(outputs1)):
            matrix[i] = f.readline().split()
            matrix[i] = list(map(float, matrix[i]))

        f.close()
    except:
        r = 'FAIL'
        for i in range(0,1 << len(inputs1)):
            distr.append(0.0)
        matrix = [[] for i in range(1 << len(outputs1))]
        for i in range(1 << len(outputs1)):
            matrix[i] = [0 for i in range(1 << len(outputs1))]

    # os.remove(circuit_file)
    # os.remove(nodes_file)
    # os.remove(output_vals_file)
    return (distr, matrix)

# Call external program (very fast) to calculate reliability_uneven
# If iter1 == -1 then use full search. Only suitable for small circuits
def external_reliability_uneven(circuit, sub_stats, iter1 = -1):
    """
    :param circuit_file: File with logic scheme
    :param sub_stats: Distribution of inputs and error matrix for outputs
    :param iter: Iteration number (Default: full search)
    :return: Reliability value for circuit as float.
    """
    dfile = get_project_directory()

    circuit_file = os.path.join(dfile, "temp" , "tmp_scheme.txt")
    circuit.print_circuit_in_file(circuit_file)
    if 2**circuit.inputs() < iter1:
        iter1 = -1

    (distr, matrix) = sub_stats
    stats_file = os.path.join(dfile, "temp", "tmp_stats.txt")
    f = open(stats_file, 'w')  # 'x'
    for d in distr:
        f.write(d.__str__() + " ")
    f.write("\n")
    for i in range(1 << circuit.outputs()):
        for j in range(1 << circuit.outputs()):
            f.write(matrix[i][j].__str__() + " ")
        f.write("\n")
    f.close()

    ostype = "win32"
    exe = os.path.join(dfile, "utils", "bin", ostype, "reliability_uneven.exe") + " " + circuit_file + " " + stats_file + " " + iter1.__str__()
    try:
        ret = subprocess.check_output(exe, shell=True).decode('UTF-8')
        r = re.compile('[ \t\n\r]+')
        relval = r.split(ret)
    except:
        relval = [100000000000.0]
    return float(relval[0])
