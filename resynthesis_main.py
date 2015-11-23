# coding: utf-8
__author__ = 'IDM.IPPM (Roman Solovyev)'

MONTE_CARLO_ITER = 5000

from resynthesis.resynthesis_create_subckts import *
from resynthesis.resynthesis_external_stats import *
from resynthesis.resynthesis_logic_minimizer import *
from resynthesis.stats import *
import timeit
import resynthesis as sa

current_milli_time = lambda: int(round(time.time() * 1000))

# Выбирает случайную подсхему из схемы с количеством элементов (или входов) больше или равным limit
# Может вернуть схему меньше, если алгоритм быстро достигнет входов начальной схемы
# type = 0 - limit для элементов, type = 1 - limit для входов
def get_random_subcircuit(cir, limit=3, type=0):
    new = sa.scheme_alt()

    # Выбираем начальный элемент с которого начнем ветвление
    start = random.randint(0, cir.elements()-1)
    node = cir.element_labels()[start]
    cell = cir.__elements__[node]

    # Добавляем элемент в схему
    new.__outputs__.append(copy.deepcopy(node))
    new.__inputs__ = copy.deepcopy(cell[1])
    new.__elements__[node] = copy.deepcopy(cell)

    # Цикл пока не закончится ветвление
    while 1:
        # Выбираем случайный вход в схему (узел и ячейку подключенные к нему)
        inpnum = random.randint(0, new.inputs()-1)
        node = new.__inputs__[inpnum]

        # Если выбранный вход является входным в схему, то завершаем цикл
        if cir.__inputs__.count(node) > 0:
            break

        cell = cir.__elements__[node]
        # Удаляем из списка входов текущий и добавляем все входы от Cell
        try:
            new.__inputs__.remove(node)
        except:
            new.print_circuit_in_file(os.path.join(get_project_directory(), "temp", "debug1.txt"))
            cir.print_circuit_in_file(os.path.join(get_project_directory(), "temp", "debug2.txt"))
            exit(0)
        for inp in cell[1]:
            if new.__inputs__.count(inp) == 0:
                new.__inputs__.append(copy.deepcopy(inp))

        # Добавляем ячейку в список элементов
        new.__elements__[node] = copy.deepcopy(cell)

        # Поскольку к узлу могут быть привязаны входы других элементов,
        # мы также должны добавить эти элементы в нашу подсхему
        for el in cir.__elements__:
            val = cir.__elements__[el]
            for i in val[1]:
                if i == node:
                    if (el not in new.__elements__):
                        # добавляем входы найденного элемента которых ещё не было
                        v1 = cir.__elements__[el]
                        for j in v1[1]:
                            if new.__inputs__.count(j) == 0:
                                if new.__outputs__.count(j) == 0:
                                    if j not in new.__elements__:
                                        new.__inputs__.append(copy.copy(j))
                        # добавляем выходы найденного элемента которых ещё не было
                        if new.__outputs__.count(el) == 0:
                            new.__outputs__.append(copy.deepcopy(el))
                        # добавляем сам найденный элемент
                        new.__elements__[el] = copy.deepcopy(val)
                        # если в списке входов оказался выход добавленного элемента удаляем
                        if new.__inputs__.count(el) > 0:
                            new.__inputs__.remove(el)

        # В некоторых условиях вход и выход могут стать рядовыми узлами подсхемы
        # Удаляем элемент из списка входов если он является выходом одного из элементов
        for i in new.__inputs__:
            if i in new.__elements__:
                new.__inputs__.remove(i)

        # Удаляем элемент из списка выходов если он является входом одного из элементов
        # Так делать нельзя так как от него могут идти связи к другим элементам большой схемы!
        if 0:
            for o in new.__outputs__:
                flag = 0
                for el in new.__elements__:
                    val = new.__elements__[el]
                    for i in val[1]:
                        if i == o:
                            new.__outputs__.remove(o)
                            flag = 1
                            break
                    if flag == 1:
                        break

        if type == 0:
            if new.elements() >= limit:
                break
        else:
            if new.inputs() >= limit:
                break

    # В некоторых условиях промежуточные узлы могут оказаться выходами основной схемы.
    # В этом случае их надо добавить в список выходов для подсхемы
    for o in cir.__outputs__:
        if o not in new.__outputs__:
            if o in new.__elements__:
                new.__outputs__.append(copy.deepcopy(o))

    return new

def get_random_element_based_on_vulnerability(cir, vul):
    total = 0.0
    for el in cir.__elements__:
        total += vul[el]

    dice = random.uniform(0.0, total)
    total = 0.0
    for el in cir.__elements__:
        total += vul[el]
        if dice <= total:
            return el

    print("Check problem in get_random_element_based_on_vulnerability function ({} > {})".format(dice, total))
    start = random.randint(0, cir.elements()-1)
    node = cir.element_labels()[start]
    return node

def get_random_input_based_on_vulnerability(ckt, subckt, vul):
    total = 0.0
    for node in subckt.__inputs__:
        if ckt.__inputs__.count(node) > 0:
            continue
        total += vul[node]

    dice = random.uniform(0.0, total)
    total = 0.0
    for node in subckt.__inputs__:
        if ckt.__inputs__.count(node) > 0:
            continue
        total += vul[node]
        if dice <= total:
            return node

    if total > 0:
        print("Check problem in get_random_input_based_on_vulnerability function ({} > {})".format(dice, total))
    inpnum = random.randint(0, subckt.inputs()-1)
    node = subckt.__inputs__[inpnum]
    return node

# Функция выбирающая с большей вероятностью критические элементы
def get_random_subcircuit_v2(cir, vulnerability_map, limit=3, type=0):
    new = sa.scheme_alt()

    # Выбираем начальный элемент с которого начнем ветвление
    node = get_random_element_based_on_vulnerability(cir, vulnerability_map)
    cell = cir.__elements__[node]

    # Добавляем элемент в схему
    new.__outputs__.append(copy.deepcopy(node))
    new.__inputs__ = copy.deepcopy(cell[1])
    new.__elements__[node] = copy.deepcopy(cell)

    # Цикл пока не закончится ветвление
    while 1:
        node = get_random_input_based_on_vulnerability(cir, new, vulnerability_map)

        # Если выбранный вход является входным в схему, то завершаем цикл
        if cir.__inputs__.count(node) > 0:
            break

        cell = cir.__elements__[node]
        # Удаляем из списка входов текущий и добавляем все входы от Cell
        try:
            new.__inputs__.remove(node)
        except:
            print("Error obtaining random CKT")
            new.print_circuit_in_file(os.path.join(get_project_directory(), "temp", "debug1.txt"))
            cir.print_circuit_in_file(os.path.join(get_project_directory(), "temp", "debug2.txt"))
            exit(0)
        for inp in cell[1]:
            if new.__inputs__.count(inp) == 0:
                new.__inputs__.append(copy.deepcopy(inp))

        # Добавляем ячейку в список элементов
        new.__elements__[node] = copy.deepcopy(cell)

        # Поскольку к узлу могут быть привязаны входы других элементов,
        # мы также должны добавить эти элементы в нашу подсхему
        for el in cir.__elements__:
            val = cir.__elements__[el]
            for i in val[1]:
                if i == node:
                    if (el not in new.__elements__):
                        # добавляем входы найденного элемента которых ещё не было
                        v1 = cir.__elements__[el]
                        for j in v1[1]:
                            if new.__inputs__.count(j) == 0:
                                if new.__outputs__.count(j) == 0:
                                    if j not in new.__elements__:
                                        new.__inputs__.append(copy.copy(j))
                        # добавляем выходы найденного элемента которых ещё не было
                        if new.__outputs__.count(el) == 0:
                            new.__outputs__.append(copy.deepcopy(el))
                        # добавляем сам найденный элемент
                        new.__elements__[el] = copy.deepcopy(val)
                        # если в списке входов оказался выход добавленного элемента удаляем
                        if new.__inputs__.count(el) > 0:
                            new.__inputs__.remove(el)

        # В некоторых условиях вход и выход могут стать рядовыми узлами подсхемы
        # Удаляем элемент из списка входов если он является выходом одного из элементов
        for i in new.__inputs__:
            if i in new.__elements__:
                new.__inputs__.remove(i)

        # Удаляем элемент из списка выходов если он является входом одного из элементов
        # Так делать нельзя так как от него могут идти связи к другим элементам большой схемы!
        if 0:
            for o in new.__outputs__:
                flag = 0
                for el in new.__elements__:
                    val = new.__elements__[el]
                    for i in val[1]:
                        if i == o:
                            new.__outputs__.remove(o)
                            flag = 1
                            break
                    if flag == 1:
                        break

        if type == 0:
            if new.elements() >= limit:
                break
        else:
            if new.inputs() >= limit:
                break

    # В некоторых условиях промежуточные узлы могут оказаться выходами основной схемы.
    # В этом случае их надо добавить в список выходов для подсхемы
    for o in cir.__outputs__:
        if o not in new.__outputs__:
            if o in new.__elements__:
                new.__outputs__.append(copy.deepcopy(o))

    return new

def compare_same_logic_for_circuit_monte_carlo (c1, c2, iternum=1000):
    # Проверяем число входов
    if c1.inputs() != c2.inputs():
        print("Different number of inputs for circuits!")
        exit()
    # Проверяем имена входов
    for c in c1.__inputs__:
        if c not in c2.__inputs__:
            print("There is no node {} in second circuit!".format(c))
            exit()
    # Проверяем число выходов
    if c1.outputs() != c2.outputs():
        print("Different number of outputs for circuits!")
        exit()
    # Проверяем имена выходов
    for c in c1.__outputs__:
        if c not in c2.__outputs__:
            print("There is no node {} in second circuit!".format(c))
            exit()

    for zzz in range(1, iternum):
        vec = list()
        for i in range(0,c1.inputs()):
            vec.append(random.randint(0, 1))
        v1 = c1.process(vec)
        v2 = c2.process(vec)
        if (v1 != v2):
            print("Circuits are not the same!")
            print(vec)
            print(v1)
            print(v2)
            exit()

# Получает значение площади (число элементов в схеме исключая BUF)
def get_area(ckt):
    total = 0
    for el in ckt.__elements__:
        data = ckt.__elements__[el]
        eltype = data[0]
        if eltype != 'BUF':
            total += 1
    return total

# Заменяет имя узла в схеме
def replace_nodename_in_ckt(ckt, oldname, newname):

    newckt = copy.deepcopy(ckt)

    for el in ckt.__elements__:
        inps = newckt.__elements__[el][1]
        for index, item in enumerate(inps):
            if item == oldname:
                inps[index] = newname

    for el in ckt.__elements__:
        if el == oldname:
            newckt.__elements__[newname] = newckt.__elements__[oldname]
            del newckt.__elements__[oldname]

    return newckt

# Избавляемся от ненужных BUF элементов
def cleanCKTFromBUFs(ckt):
    newckt = copy.deepcopy(ckt)
    total = 0
    for el in ckt.__elements__:
        if ckt.__elements__[el][0] == 'BUF':
            node1 = el
            node2 = ckt.__elements__[el][1][0]
            total += 1
            if node1 == node2:
                del newckt.__elements__[node1]
            elif (node1 not in ckt.__inputs__) and (node1 not in ckt.__outputs__):
                del newckt.__elements__[node1]
                newckt = replace_nodename_in_ckt(newckt, node1, node2)
            elif (node2 not in ckt.__inputs__) and (node2 not in ckt.__outputs__):
                del newckt.__elements__[node1]
                newckt = replace_nodename_in_ckt(newckt, node2, node1)
            else:
                print('Cant avoid BUF {} {}'.format(node1, node2))
                total -= 1
    if total > 0:
        print("{} unused BUFs removed!".format(total))

    return newckt

# Функция замены подсхемы (Роман)
def replace_subckt_v1(bigckt, sub, rep):
    global globalElemIndex
    global currentCKTIndex
    try:
        globalElemIndex
    except NameError:
        globalElemIndex = 0
    try:
        currentCKTIndex
    except NameError:
        currentCKTIndex = 0
    currentCKTIndex += 1
    new = copy.deepcopy(bigckt)

    # Проверяем что все элементы sub присутствуют в new
    # Затем удаляем их
    for el in sub.__elements__:
        if el in new.__elements__:
            if new.__elements__[el] != sub.__elements__[el]:
                print('Different elements with same name {} in main ckt and subckt!'.format(el))
                exit()
            del new.__elements__[el]
        else:
            print('No element {} in main ckt!'.format(el))
            exit()

    # Проверяем что входы и выходы rep существуют в new даже после удаления подсхемы
    for i in rep.__inputs__:
        flag = 0
        if i in new.__inputs__:
            continue
        for el in new.__elements__:
            if i == el:
                flag = 1
                break
        for el in new.__elements__:
            if i in new.__elements__[el][1]:
                flag = 1
                break
        if flag == 0:
            print('Input {} can"t be found in main ckt'.format(i))
            exit()
    for o in rep.__outputs__:
        flag = 0
        if o in new.__outputs__:
            continue
        for el in new.__elements__:
            if o == el:
                flag = 1
                break
        for el in new.__elements__:
            if o in new.__elements__[el][1]:
                flag = 1
                break
        if flag == 0:
            print('Output {} can"t be found in main ckt'.format(o))
            exit()

    # Заменяем имена в подсхеме, которые не являются входами и выходами
    for el in rep.__elements__:
        if (el not in rep.__inputs__) and (el not in rep.__outputs__):
            newname = 'NODE_ITER_{}_REP_{}'.format(currentCKTIndex, globalElemIndex)
            globalElemIndex += 1
            rep = replace_nodename_in_ckt(rep, el, newname)

    # Добавляем подсхему rep в new
    for el in rep.__elements__:
        new.__elements__[el] = copy.deepcopy(rep.__elements__[el])

    return new

# Версия Миши
def replace_subckt_v2(bigckt, sub, rep):
    rep.__inputs__.sort()
    rep.__outputs__.sort()
    s = []
    for el in sub.__elements__:
        s.append(el)
    new = copy.deepcopy(bigckt)
    res = new.replace_elements_with_scheme(s, rep, rep.__outputs__)
    if res == None:
        tm = str(time.time())
        print('Replace subckt error, printing error example in files')
        bigckt.print_circuit_in_file(os.path.join(get_project_directory(), 'temp', tm + 'bigckt.txt'))
        sub.print_circuit_in_file(os.path.join(get_project_directory(), 'temp', tm + 'sub.txt'))
        rep.print_circuit_in_file(os.path.join(get_project_directory(), 'temp', tm + 'rep.txt'))
    return new

def check_overall_TMR(in_circ_file):
    main_circuit_etalon = sa.read_scheme(in_circ_file)
    initial_area = get_area(main_circuit_etalon)
    initial_reliability = external_reliability(main_circuit_etalon, 100000)
    tmr_circ = createTMRCirc(main_circuit_etalon)
    new_area = get_area(tmr_circ)
    new_reliability = external_reliability(tmr_circ, 100000)
    print('Initial reliability: {}'.format(initial_reliability))
    print('TMR reliability: {}'.format(new_reliability))
    print('New area: {} Initial Area: {} Growth Percent: {}%'.format(new_area, initial_area, round((100.0*new_area)/initial_area), 2))

def print_distr_in_file(circuit, sub_stats, file_name):
    (distr, matrix) = sub_stats
    f = open(file_name, 'w')  # 'x'
    for d in distr:
        f.write(d.__str__() + " ")
    f.write("\n")
    for i in range(1 << circuit.outputs()):
        for j in range(1 << circuit.outputs()):
            f.write(matrix[i][j].__str__() + " ")
        f.write("\n")
    f.close()

def printInputOutputNumbersInReplaceStats(total, replace):
    print('Stat for input/outputs of selected subcircuits. For all runs:')
    print(total)
    print('Stat for input/outputs of selected subcircuits. With successfull replacements:')
    print(replace)

def printLevelIncreaseStat(r):
    val = 0
    total = 0
    for i in r:
        val += i
        total += 1
    print("Average level increase for every successful replacement: {}%".format(round((100*val/total) - 100, 2)))
    print("Full list of level increase:")
    print(r)

def getMaxLevel(ckt):
    max = 1
    for label in ckt.__outputs__:
        l = ckt.level(label)
        if l > max:
            max = l
    return max

# Если выходной узел всей схемы попал в середину подсхемы
def unsuitableCkt(main_circuit, subckt):
    for out in main_circuit.__outputs__:
        for el in subckt.__elements__:
            for node in subckt.__elements__[el][1]:
                # print(node)
                if node == out:
                    return 1
    return 0


def improve_circuit_by_resynthesis_ver6(in_circ_file, out_circ_file, needed_replacements, max_area_overhead):
    """
    :param in_circ_file: File with input circuit .
    :param out_circ_file: File to store resulted circuit
    :param needed_replacements: Number of successfull replacemnts
    :param max_area_overhead: koeff for defined maximum area of generated circuit related to initial circuit (from 1.0)
    :return: true or false
    """
    overall_start = timeit.default_timer()
    calc_type = 1
    print("Start processing circuit:")
    main_circuit_etalon = sa.read_scheme(in_circ_file)
    initial_area = get_area(main_circuit_etalon)
    initial_circ_delay = getMaxLevel(main_circuit_etalon)
    main_circuit = sa.read_scheme(in_circ_file)
    (initial_reliability, vulnerability_map) = external_vulnerability_map(main_circuit, MONTE_CARLO_ITER)
    latest_reliability = initial_reliability
    success_replacements_part1 = 0
    success_replacements = 0
    between_replacements = 0
    iterations = 50000

    bestFunction = [0] * 6
    bestFunctionReplace = [0] * 6
    inputOutputTotal = dict()
    inputOutputReplacements = dict()
    replacementLevelIncrease = []

    for zzz in range(1, iterations):
        print("\n|||||||||||||| Iteration "+ zzz.__str__() + " ||||||||||||||")
        # main_circuit = cleanCKTFromBUFs(main_circuit)
        if calc_type == 1:
            rnd1 = get_random_subcircuit_v2(main_circuit, vulnerability_map, random.randint(2,6), 1)
        else:
            rnd1 = get_random_subcircuit(main_circuit, random.randint(2,6), 1)

        if rnd1.inputs() < 2:
            print("Too small subckt")
            continue
        if rnd1.inputs() > 9:
            print("Too big subckt")
            continue
        if rnd1.outputs() > 11:
            print("Too many outputs subckt")
            continue

        if (rnd1.inputs(), rnd1.outputs()) in inputOutputTotal:
            inputOutputTotal[rnd1.inputs(), rnd1.outputs()] += 1
        else:
            inputOutputTotal[rnd1.inputs(), rnd1.outputs()] = 1

        between_replacements += 1
        print("OK subckt [Inputs: {} Outputs: {}]".format(rnd1.inputs(), rnd1.outputs()))
        trtable = create_truth_table(rnd1)
        data = goEspresso_external(trtable, rnd1)

        # Здесь добавляем произвольный набор схем претендентов на замену
        t1 = current_milli_time()
        subckt = []
        subckt.append(createSubckt_method1(data, rnd1))
        subckt.append(createSubckt_method2(data, rnd1))
        subckt.append(createSubckt_method3(data, rnd1))
        yosys_subckt = create_circuit_external_yosys(rnd1)
        if yosys_subckt != None:
            subckt.append(yosys_subckt)
        if 0:
            tmrSubCkt = createTMRCirc(rnd1)
            # Проверяем что троирование не приведет к увеличению схемы сверх указанного
            if (get_area(main_circuit) - get_area(rnd1) + get_area(tmrSubCkt)) < initial_area*max_area_overhead:
                subckt.append(tmrSubCkt)
            else:
                print('TMR SUBCKT skipped due to large area growth')
        t2 = current_milli_time()
        # print('Gen {} subckt OK. Generation time: {}'.format(len(subckt), round((t2-t1)/1000, 3)))

        # Проверяем что все сгенерированные подсхемы работают одинаково
        # Это можно будет убрать после полноценного тестирования
        for s in subckt:
            try:
                cmp = scheme_cmp(rnd1, s)
                if cmp == False:
                    print('Subckt have less inputs. Skip for now')
                    continue
                elif cmp < 0.99999:
                    print('Error with subckt it works incorrect check it')
                    exit(0)
            except:
                print(rnd1)
                print(s)
                main_circuit.print_circuit_in_file(os.path.join(get_project_directory(), 'temp', 'main_circuit_io_problem.txt'))
                rnd1.print_circuit_in_file(os.path.join(get_project_directory(), 'temp', 'rnd1_io_problem.txt'))
                s.print_circuit_in_file(os.path.join(get_project_directory(), 'temp', 'subckt_io_problem.txt'))
                print('Input/output problem')
                exit()
                continue

        # Рассчитываем вероятности комбинаций на входах подсхемы
        iternum = pow(2, rnd1.inputs())*1000
        t1 = current_milli_time()
        distr = distribution_estim_external(main_circuit, rnd1.input_labels(), rnd1.output_labels(), iternum)
        t2 = current_milli_time()
        # print('Distribution Estim C: {} seconds'.format(round((t2-t1)/1000, 3)))
        t1 = current_milli_time()
        subckt_reliability = external_reliability_uneven(rnd1, distr)
        t2 = current_milli_time()
        # print('Reliability uneven: {} seconds'.format(round((t2-t1)/1000, 3)))
        bestval = subckt_reliability + 1000000

        # Из набора подсхем выбираем самую надежную
        t1 = current_milli_time()
        subCKTNum = 0
        bestCKTIndex = 0
        allVals = []
        for s in subckt:
            subCKTNum += 1
            if s.input_labels() != rnd1.input_labels():
                print('Invalid input order in subckt')
                print(s.input_labels())
                print(rnd1.input_labels())
                exit()

            val2 = external_reliability_uneven(s, distr)
            allVals.append(val2)
            if val2 < bestval:
                bestckt = copy.deepcopy(s)
                bestval = val2
                bestCKTIndex = subCKTNum

        bestFunction[bestCKTIndex] += 1
        t2 = current_milli_time()
        # print('Get best CKT {}: {} seconds'.format(bestCKTIndex, round((t2-t1)/1000, 3)))

        print('Array of reliability: {}'.format(allVals))
        if subckt_reliability > bestval + 0.05:
            print("Success (Stage 1) {} > {} (CKT Index {})! =)".format(subckt_reliability, bestval, bestCKTIndex))
            success_replacements_part1 += 1
            t1 = current_milli_time()
            main_circuit_new = replace_subckt_v2(main_circuit, rnd1, bestckt)
            t2 = current_milli_time()
            # print('Replace subckt: {} seconds'.format(round((t2-t1)/1000, 3)))
            t1 = current_milli_time()
            (val_main_circuit_new, vulnerability_new) = external_vulnerability_map(main_circuit_new, MONTE_CARLO_ITER)
            compare_same_logic_for_circuit_monte_carlo(main_circuit, main_circuit_new, 10)
            if latest_reliability > val_main_circuit_new:
                print("Success (Stage 2) {} > {} ! =)".format(latest_reliability, val_main_circuit_new))
                # Заменяем карту уязвимостей
                vulnerability_map = copy.deepcopy(vulnerability_new)
                main_circuit = copy.deepcopy(main_circuit_new)
                latest_reliability = val_main_circuit_new
                cur_area = get_area(main_circuit_new)
                print('New area: {} Initial Area: {} Growth Percent: {}%'.format(cur_area, initial_area, round((100.0*cur_area)/initial_area), 2))
                success_replacements += 1
                between_replacements = 0
                # Статистика по входам выходам замененной подсхемы
                if (rnd1.inputs(), rnd1.outputs()) in inputOutputReplacements:
                    inputOutputReplacements[rnd1.inputs(), rnd1.outputs()] += 1
                else:
                    inputOutputReplacements[rnd1.inputs(), rnd1.outputs()] = 1
                # Сохраняем значение увеличения уровней подсхемы
                levelRnd1 = getMaxLevel(rnd1)
                levelBestCkt = getMaxLevel(bestckt)
                replacementLevelIncrease.append(levelBestCkt/levelRnd1)
                bestFunctionReplace[bestCKTIndex] += 1
            else:
                print("Fail (Stage 2) {} < {} ! =(".format(latest_reliability, val_main_circuit_new))
                # Для тестирования ошибок во внешней проге
                rnd1.print_circuit_in_file(os.path.join(get_project_directory(), 'temp', 'rnd1.txt'))
                bestckt.print_circuit_in_file(os.path.join(get_project_directory(), 'temp', 'subckt.txt'))
                main_circuit.print_circuit_in_file(os.path.join(get_project_directory(), 'temp', 'main_circuit.txt'))
                main_circuit_new.print_circuit_in_file(os.path.join(get_project_directory(), 'temp', 'main_circuit_new.txt'))

            t2 = current_milli_time()
            print('External reliability: {} seconds'.format(round((t2-t1)/1000, 3)))
            if success_replacements >= needed_replacements:
                break
        else:
            print("Fail (Stage 1)! =( " + subckt_reliability.__str__() + " <= " + bestval.__str__())

        # Если за тысячу итераций не было успешных замен выходим
        if between_replacements > 1000:
            break

    endpoint_reliability = external_reliability(main_circuit, MONTE_CARLO_ITER)
    print("Total Iterations : " + zzz.__str__())
    print("Success replacements (P1): " + success_replacements_part1.__str__())
    print("Success replacements (P2): " + success_replacements.__str__())
    if success_replacements_part1 == 0:
        percent = 100
    else:
        percent = round((100*success_replacements)/success_replacements_part1, 2)
    print("Success rate: ", percent.__str__())
    print("Initial  reliability: " + initial_reliability.__str__())
    print("Endpoint reliability: " + endpoint_reliability.__str__())
    print("Initial number of elements: {}".format(initial_area))
    print("Endpoint number of elements: {}".format(get_area(main_circuit)))
    print("Best subckt generators: {}".format(bestFunction))
    overall_end = timeit.default_timer()
    print("Total runtime: {} seconds".format((overall_end - overall_start)))
    main_circuit.print_circuit_in_file(out_circ_file)
    compare_same_logic_for_circuit_monte_carlo(main_circuit_etalon, main_circuit, 1000)
    printInputOutputNumbersInReplaceStats(inputOutputTotal, inputOutputReplacements)
    printLevelIncreaseStat(replacementLevelIncrease)
    print("Best CKT for replace")
    print(bestFunctionReplace)
    resynt_circ_delay = getMaxLevel(main_circuit)
    circ_delay_percent = round((100*resynt_circ_delay)/initial_circ_delay, 2)
    print("Levels in circ. Initial: {}, Resyntesized: {}, Percent: {}".format(initial_circ_delay, resynt_circ_delay, circ_delay_percent))

if __name__ == '__main__':
    improve_circuit_by_resynthesis_ver6('./circuits/ISCAS/c432_initial.txt', './temp/c432_resynth.txt', 1000, 1.5)
