# coding: utf-8
__author__ = 'IDM.IPPM (Roman Solovyev)'

import os
import subprocess
import re
import random
from resynthesis.resynthesis_external_stats import get_project_directory
import resynthesis as sa

# Получает список уникальных имен узлов из структуры merge
def getUniqueNames(m):
    lst = []
    for o in m:
        for term in m[o]:
            for name in term:
                if lst.count(name) == 0:
                    lst.append(name)
    return lst

def createMergeStructure(q, ckt):
    merge = dict()
    for o in q:
        oname = ckt.__outputs__[o]
        merge[oname] = []
        for term in q[o]:
            lst = []
            for i in range(0, ckt.inputs()):
                if (term[i] == '1'):
                    lst.append(ckt.__inputs__[i])
                elif (term[i] == '0'):
                    lst.append("!" + ckt.__inputs__[i])
            merge[oname].append(lst)
    return merge


# q - reduced truth table, ckt - initial ckt
# Method 1: сначала объединяем наиболее частые AND пары,
# потом все это объединяем через OR

def createSubckt_method1(q, ckt):
    sckt = sa.scheme_alt()
    for i in ckt.__inputs__:
        sckt.__inputs__.append(i)
    for o in ckt.__outputs__:
        sckt.__outputs__.append(o)

    # Делаем подходящую структуру данных
    merge = createMergeStructure(q, ckt)
    # print(merge)

    # Ищем самые часто встречающиеся пары и заменяем их
    # Приоритет парам либо с отрицаниями, либо без них
    # Цикл заканчивается когда все термы сжимаются до одного элемента
    num = 0
    while (1):
        uniqueList = getUniqueNames(merge)
        total = len(uniqueList)

        # Создаем проверочный массив
        check = [0] * total
        for i in range(total):
            check[i] = [0] * total

        # Считаем пары
        for i in range(0, total):
            for j in range(i+1, total):
                n1 = uniqueList[i]
                n2 = uniqueList[j]
                check[i][j] = 0
                for o in merge:
                    for term in merge[o]:
                        if term.count(n1) > 0 and term.count(n2) > 0:
                            check[i][j] = check[i][j] + 1

        # Выбираем самую частую пару
        max = 0
        maxi = -1
        maxj = -1
        for i in range(0, total):
            for j in range(i+1, total):
                if check[i][j] > 0:
                    if check[i][j] > max:
                        max = check[i][j]
                        maxi = i
                        maxj = j
                    elif check[i][j] == max:
                        if (uniqueList[i][0] != '!' and uniqueList[j][0] != '!') or (uniqueList[i][0] == '!' and uniqueList[j][0] == '!'):
                            maxi = i
                            maxj = j

        # Если пары ещё есть добавляем элемент в схемы и заменяем пару в списке на один элемент
        # Если пар нет выходим из цикла
        if (max > 0):
            n1 = uniqueList[maxi]
            n2 = uniqueList[maxj]

            newname = "INT_{0}".format(num)
            num = num + 1
            if (n1[0] != '!' and n2[0] != '!'):
                sckt.__elements__[newname] = ('AND', [n1, n2])
            elif (n1[0] == '!' and n2[0] == '!'):
                sckt.__elements__[newname] = ('NOR', [n1[1:], n2[1:]])
            elif (n1[0] == '!'):
                newname1 = "INT_{0}".format(num)
                num = num + 1
                sckt.__elements__[newname1] = ('INV', [n1[1:]])
                sckt.__elements__[newname] = ('AND', [newname1, n2])
            elif (n2[0] == '!'):
                newname1 = "INT_{0}".format(num)
                num = num + 1
                sckt.__elements__[newname1] = ('INV', [n2[1:]])
                sckt.__elements__[newname] = ('AND', [newname1, n1])

            # Заменяем пары в термах
            for o in merge:
                for term in merge[o]:
                    if term.count(n1) > 0 and term.count(n2) > 0:
                        term.remove(n1)
                        term.remove(n2)
                        term.append(newname)

        else:
            break

        check = []

    # print(sckt)
    # print(merge)

    # Цикл, который попарно объединяет термы в рамках каждого выхода
    while (1):
        uniqueList = getUniqueNames(merge)
        total = len(uniqueList)

        # Создаем проверочный массив
        check = [0] * total
        for i in range(total):
            check[i] = [0] * total

        # Считаем пары (надо проверить какая пара чаще встречается среди всех выходов)
        for i in range(0, total):
            for j in range(i+1, total):
                n1 = uniqueList[i]
                n2 = uniqueList[j]
                check[i][j] = 0
                for o in merge:
                    flag = 0
                    for term in merge[o]:
                        if term.count(n1) > 0:
                            flag = flag + 1
                    for term in merge[o]:
                        if term.count(n2) > 0:
                            flag = flag + 1
                    if flag == 2:
                        check[i][j] = check[i][j] + 1

        # Выбираем самую частую пару
        max = 0
        maxi = -1
        maxj = -1
        for i in range(0, total):
            for j in range(i+1, total):
                if check[i][j] > 0:
                    if check[i][j] > max:
                        max = check[i][j]
                        maxi = i
                        maxj = j
                    elif check[i][j] == max:
                        if (uniqueList[i][0] != '!' and uniqueList[j][0] != '!') or (uniqueList[i][0] == '!' and uniqueList[j][0] == '!'):
                            maxi = i
                            maxj = j

        # Если пары ещё есть добавляем элемент в схемы и заменяем пару в списке на один элемент
        # Если пар нет выходим из цикла
        if (max > 0):
            n1 = uniqueList[maxi]
            n2 = uniqueList[maxj]

            newname = "INT_{0}".format(num)
            num = num + 1
            if (n1[0] != '!' and n2[0] != '!'):
                sckt.__elements__[newname] = ('OR', [n1, n2])
            elif (n1[0] == '!' and n2[0] == '!'):
                sckt.__elements__[newname] = ('NAND', [n1[1:], n2[1:]])
            elif (n1[0] == '!'):
                newname1 = "INT_{0}".format(num)
                num = num + 1
                sckt.__elements__[newname1] = ('INV', [n1[1:]])
                sckt.__elements__[newname] = ('OR', [newname1, n2])
            elif (n2[0] == '!'):
                newname1 = "INT_{0}".format(num)
                num = num + 1
                sckt.__elements__[newname1] = ('INV', [n2[1:]])
                sckt.__elements__[newname] = ('OR', [newname1, n1])

            # print('N1: ' + n1)
            # print('N2: ' + n2)

            # Заменяем пары в термах
            for o in merge:
                flag = 0
                for term in merge[o]:
                    if term.count(n1) > 0:
                        flag = flag + 1
                    if term.count(n2) > 0:
                        flag = flag + 1
                if (flag == 2):
                    for term in merge[o]:
                        if term.count(n1) > 0:
                            term.remove(n1)
                            continue
                        if term.count(n2) > 0:
                            term.remove(n2)
                            continue
                    merge[o].append([newname])

            # Чистим список от пустых записей
            for o in merge:
                for term in merge[o]:
                    while (merge[o].count([]) > 0):
                        merge[o].remove([])

        else:
            break

        check = []

    # Теперь требуется заменить имена промежуточных узлов на имена реальных выходов
    for o in merge:
        find = merge[o][0][0]
        replace = o
        # Сначала меняем в поле ключей
        if find in sckt.__elements__:
            sckt.__elements__[replace] = sckt.__elements__[find]
            del sckt.__elements__[find]
        # Затем меняем в элементах
        for el in sckt.__elements__:
            lst = sckt.__elements__[el][1]
            for key,i in enumerate(lst):
                if i == find:
                    lst[key] = replace

    # Фикс для случая когда у нас несколько выходов имеют единую логическую функцию (и часть выходов пропала при замене)
    # В этом случае добавляем буферы
    fix_happened = 0
    for o in merge:
        if o not in sckt.__elements__:
            flag = 0
            for el in sckt.__elements__:
                lst = sckt.__elements__[el][1]
                for key,i in enumerate(lst):
                    if i == o:
                         flag += 1
            if flag == 0:
                f1 = merge[o][0][0]
                fname = ''
                for o1 in merge:
                    if o1 in sckt.__elements__:
                        f2 = merge[o1][0][0]
                        if f1 == f2:
                            fname = o1
                if fname == '':
                    print('Some unexpected error here')
                    break
                sckt.__elements__[o] = ('BUF', [fname])
                fix_happened += 1

    # Фикс для случая когда выход полностью повторяет вход или его инверсию (и он теряется)
    # Необходимо добавить буфер типа (BUF вход выход) или (INV вход выход)
    for o in merge:
        if (len(merge[o]) == 1) & (len(merge[o][0]) == 1):
            if (merge[o][0][0][0] != '!') & (merge[o][0][0] in ckt.__inputs__):
                sckt.__elements__[o] = ('BUF', merge[o][0])
            if (merge[o][0][0][0] == '!') & (merge[o][0][0][1:] in ckt.__inputs__):
                sckt.__elements__[o] = ('INV', [merge[o][0][0][1:]])

    # if fix_happened > 0:
        # print('Merge:')
        # print(merge)
        # print(sckt)
        # exit()

    return sckt

# q - reduced truth table, ckt - initial ckt
# Method 2: сначала объединяем наиболее частые AND пары,
# потом все это объединяем через OR
# Заменяем X&~Y слчайным образом на INV + AND или INV + NOR
# Заменяем ~X&Y слчайным образом на INV + OR или INV + NAND

def createSubckt_method2(q, ckt):
    sckt = sa.scheme_alt()
    for i in ckt.__inputs__:
        sckt.__inputs__.append(i)
    for o in ckt.__outputs__:
        sckt.__outputs__.append(o)

    # Делаем подходящую структуру данных
    merge = createMergeStructure(q, ckt)

    # Ищем самые часто встречающиеся пары и заменяем их
    # Приоритет парам либо с отрицаниями, либо без них
    # Цикл заканчивается когда все термы сжимаются до одного элемента
    num = 0
    while (1):
        uniqueList = getUniqueNames(merge)
        total = len(uniqueList)

        # Создаем проверочный массив
        check = [0] * total
        for i in range(total):
            check[i] = [0] * total

        # Считаем пары
        for i in range(0, total):
            for j in range(i+1, total):
                n1 = uniqueList[i]
                n2 = uniqueList[j]
                check[i][j] = 0
                for o in merge:
                    for term in merge[o]:
                        if term.count(n1) > 0 and term.count(n2) > 0:
                            check[i][j] = check[i][j] + 1

        # Выбираем самую частую пару
        max = 0
        maxi = -1
        maxj = -1
        for i in range(0, total):
            for j in range(i+1, total):
                if check[i][j] > 0:
                    if check[i][j] > max:
                        max = check[i][j]
                        maxi = i
                        maxj = j
                    elif check[i][j] == max:
                        if (uniqueList[i][0] != '!' and uniqueList[j][0] != '!') or (uniqueList[i][0] == '!' and uniqueList[j][0] == '!'):
                            maxi = i
                            maxj = j

        # Если пары ещё есть добавляем элемент в схемы и заменяем пару в списке на один элемент
        # Если пар нет выходим из цикла
        if (max > 0):
            n1 = uniqueList[maxi]
            n2 = uniqueList[maxj]

            newname = "INT_{0}".format(num)
            num = num + 1
            if (n1[0] != '!' and n2[0] != '!'):
                sckt.__elements__[newname] = ('AND', [n1, n2])
            elif (n1[0] == '!' and n2[0] == '!'):
                sckt.__elements__[newname] = ('NOR', [n1[1:], n2[1:]])
            elif (n1[0] == '!'):
                newname1 = "INT_{0}".format(num)
                num = num + 1
                if random.randint(0, 1) == 0:
                    sckt.__elements__[newname1] = ('INV', [n1[1:]])
                    sckt.__elements__[newname] = ('AND', [newname1, n2])
                else:
                    sckt.__elements__[newname1] = ('INV', [n2])
                    sckt.__elements__[newname] = ('NOR', [newname1, n1[1:]])
            elif (n2[0] == '!'):
                newname1 = "INT_{0}".format(num)
                num = num + 1
                if random.randint(0, 1) == 0:
                    sckt.__elements__[newname1] = ('INV', [n2[1:]])
                    sckt.__elements__[newname] = ('AND', [newname1, n1])
                else:
                    sckt.__elements__[newname1] = ('INV', [n1])
                    sckt.__elements__[newname] = ('NOR', [newname1, n2[1:]])

            # Заменяем пары в термах
            for o in merge:
                for term in merge[o]:
                    if term.count(n1) > 0 and term.count(n2) > 0:
                        term.remove(n1)
                        term.remove(n2)
                        term.append(newname)

        else:
            break

        check = []

    # print(sckt)
    # print(merge)

    # Цикл, который попарно объединяет термы в рамках каждого выхода
    while (1):
        uniqueList = getUniqueNames(merge)
        total = len(uniqueList)

        # Создаем проверочный массив
        check = [0] * total
        for i in range(total):
            check[i] = [0] * total

        # Считаем пары (надо проверить какая пара чаще встречается среди всех выходов)
        for i in range(0, total):
            for j in range(i+1, total):
                n1 = uniqueList[i]
                n2 = uniqueList[j]
                check[i][j] = 0
                for o in merge:
                    flag = 0
                    for term in merge[o]:
                        if term.count(n1) > 0:
                            flag = flag + 1
                    for term in merge[o]:
                        if term.count(n2) > 0:
                            flag = flag + 1
                    if flag == 2:
                        check[i][j] = check[i][j] + 1

        # Выбираем самую частую пару
        max = 0
        maxi = -1
        maxj = -1
        for i in range(0, total):
            for j in range(i+1, total):
                if check[i][j] > 0:
                    if check[i][j] > max:
                        max = check[i][j]
                        maxi = i
                        maxj = j
                    elif check[i][j] == max:
                        if (uniqueList[i][0] != '!' and uniqueList[j][0] != '!') or (uniqueList[i][0] == '!' and uniqueList[j][0] == '!'):
                            maxi = i
                            maxj = j

        # Если пары ещё есть добавляем элемент в схемы и заменяем пару в списке на один элемент
        # Если пар нет выходим из цикла
        if (max > 0):
            n1 = uniqueList[maxi]
            n2 = uniqueList[maxj]

            newname = "INT_{0}".format(num)
            num = num + 1
            if (n1[0] != '!' and n2[0] != '!'):
                sckt.__elements__[newname] = ('OR', [n1, n2])
            elif (n1[0] == '!' and n2[0] == '!'):
                sckt.__elements__[newname] = ('NAND', [n1[1:], n2[1:]])
            elif (n1[0] == '!'):
                newname1 = "INT_{0}".format(num)
                num = num + 1
                if random.randint(0, 1) == 0:
                    sckt.__elements__[newname1] = ('INV', [n1[1:]])
                    sckt.__elements__[newname] = ('OR', [newname1, n2])
                else:
                    sckt.__elements__[newname1] = ('INV', [n2])
                    sckt.__elements__[newname] = ('NAND', [newname1, n1[1:]])
            elif (n2[0] == '!'):
                newname1 = "INT_{0}".format(num)
                num = num + 1
                if random.randint(0, 1) == 0:
                    sckt.__elements__[newname1] = ('INV', [n2[1:]])
                    sckt.__elements__[newname] = ('OR', [newname1, n1])
                else:
                    sckt.__elements__[newname1] = ('INV', [n1])
                    sckt.__elements__[newname] = ('NAND', [newname1, n2[1:]])

            # print('N1: ' + n1)
            # print('N2: ' + n2)

            # Заменяем пары в термах
            for o in merge:
                flag = 0
                for term in merge[o]:
                    if term.count(n1) > 0:
                        flag = flag + 1
                    if term.count(n2) > 0:
                        flag = flag + 1
                if (flag == 2):
                    for term in merge[o]:
                        if term.count(n1) > 0:
                            term.remove(n1)
                            continue
                        if term.count(n2) > 0:
                            term.remove(n2)
                            continue
                    merge[o].append([newname])

            # Чистим список от пустых записей
            for o in merge:
                for term in merge[o]:
                    while (merge[o].count([]) > 0):
                        merge[o].remove([])

        else:
            break

        check = []

    # Теперь требуется заменить имена промежуточных узлов на имена реальных выходов
    for o in merge:
        find = merge[o][0][0]
        replace = o
        # Сначала меняем в поле ключей
        if find in sckt.__elements__:
            sckt.__elements__[replace] = sckt.__elements__[find]
            del sckt.__elements__[find]
        # Затем меняем в элементах
        for el in sckt.__elements__:
            lst = sckt.__elements__[el][1]
            for key,i in enumerate(lst):
                if i == find:
                    lst[key] = replace

    # Фикс для случая когда у нас несколько выходов имеют единую логическую функцию (и часть выходов пропала при замене)
    # В этом случае добавляем буферы
    fix_happened = 0
    for o in merge:
        if o not in sckt.__elements__:
            flag = 0
            for el in sckt.__elements__:
                lst = sckt.__elements__[el][1]
                for key,i in enumerate(lst):
                    if i == o:
                         flag += 1
            if flag == 0:
                f1 = merge[o][0][0]
                fname = ''
                for o1 in merge:
                    if o1 in sckt.__elements__:
                        f2 = merge[o1][0][0]
                        if f1 == f2:
                            fname = o1
                if fname == '':
                    print('Some unexpected error here')
                    break
                sckt.__elements__[o] = ('BUF', [fname])
                fix_happened += 1

    # Фикс для случая когда выход полностью повторяет вход или его инверсию (и он теряется)
    # Необходимо добавить буфер типа (BUF вход выход) или (INV вход выход)
    for o in merge:
        if (len(merge[o]) == 1) & (len(merge[o][0]) == 1):
            if (merge[o][0][0][0] != '!') & (merge[o][0][0] in ckt.__inputs__):
                sckt.__elements__[o] = ('BUF', merge[o][0])
            if (merge[o][0][0][0] == '!') & (merge[o][0][0][1:] in ckt.__inputs__):
                sckt.__elements__[o] = ('INV', [merge[o][0][0][1:]])

    return sckt

# q - reduced truth table, ckt - initial ckt
# Method 3: объединяем произвольные AND пары,
# потом все это объединяем через произвольные OR пары

def createSubckt_method3(q, ckt):
    sckt = sa.scheme_alt()
    for i in ckt.__inputs__:
        sckt.__inputs__.append(i)
    for o in ckt.__outputs__:
        sckt.__outputs__.append(o)

    # Делаем подходящую структуру данных
    merge = createMergeStructure(q, ckt)

    # Ищем самые часто встречающиеся пары и заменяем их
    # Приоритет парам либо с отрицаниями, либо без них
    # Цикл заканчивается когда все термы сжимаются до одного элемента
    num = 0
    while (1):
        uniqueList = getUniqueNames(merge)
        total = len(uniqueList)

        # Создаем проверочный массив
        check = [0] * total
        for i in range(total):
            check[i] = [0] * total

        # Считаем пары
        for i in range(0, total):
            for j in range(i+1, total):
                n1 = uniqueList[i]
                n2 = uniqueList[j]
                check[i][j] = 0
                for o in merge:
                    for term in merge[o]:
                        if term.count(n1) > 0 and term.count(n2) > 0:
                            check[i][j] = check[i][j] + 1

        # Выбираем случайную пару
        count = 0
        for i in range(0, total):
            for j in range(i+1, total):
                if check[i][j] > 0:
                    count += 1
        if count == 0:
            break

        numPair = random.randint(0, count-1)
        count = 0
        for i in range(0, total):
            for j in range(i+1, total):
                if check[i][j] > 0:
                    if count == numPair:
                        n1 = uniqueList[i]
                        n2 = uniqueList[j]
                        break
                    count += 1

        newname = "INT_{0}".format(num)
        num = num + 1
        if (n1[0] != '!' and n2[0] != '!'):
            sckt.__elements__[newname] = ('AND', [n1, n2])
        elif (n1[0] == '!' and n2[0] == '!'):
            sckt.__elements__[newname] = ('NOR', [n1[1:], n2[1:]])
        elif (n1[0] == '!'):
            newname1 = "INT_{0}".format(num)
            num = num + 1
            if random.randint(0, 1) == 0:
                sckt.__elements__[newname1] = ('INV', [n1[1:]])
                sckt.__elements__[newname] = ('AND', [newname1, n2])
            else:
                sckt.__elements__[newname1] = ('INV', [n2])
                sckt.__elements__[newname] = ('NOR', [newname1, n1[1:]])
        elif (n2[0] == '!'):
            newname1 = "INT_{0}".format(num)
            num = num + 1
            if random.randint(0, 1) == 0:
                sckt.__elements__[newname1] = ('INV', [n2[1:]])
                sckt.__elements__[newname] = ('AND', [newname1, n1])
            else:
                sckt.__elements__[newname1] = ('INV', [n1])
                sckt.__elements__[newname] = ('NOR', [newname1, n2[1:]])

        # Заменяем пары в термах
        for o in merge:
            for term in merge[o]:
                if term.count(n1) > 0 and term.count(n2) > 0:
                    term.remove(n1)
                    term.remove(n2)
                    term.append(newname)

    # Цикл, который попарно объединяет термы в рамках каждого выхода
    while (1):
        uniqueList = getUniqueNames(merge)
        total = len(uniqueList)

        # Создаем проверочный массив
        check = [0] * total
        for i in range(total):
            check[i] = [0] * total

        # Считаем пары (надо проверить какая пара чаще встречается среди всех выходов)
        for i in range(0, total):
            for j in range(i+1, total):
                n1 = uniqueList[i]
                n2 = uniqueList[j]
                check[i][j] = 0
                for o in merge:
                    flag = 0
                    for term in merge[o]:
                        if term.count(n1) > 0:
                            flag = flag + 1
                    for term in merge[o]:
                        if term.count(n2) > 0:
                            flag = flag + 1
                    if flag == 2:
                        check[i][j] = check[i][j] + 1

        # Выбираем случайную пару
        count = 0
        for i in range(0, total):
            for j in range(i+1, total):
                if check[i][j] > 0:
                    count += 1

        if count == 0:
            break

        numPair = random.randint(0, count-1)
        count = 0
        for i in range(0, total):
            for j in range(i+1, total):
                if check[i][j] > 0:
                    if count == numPair:
                        n1 = uniqueList[i]
                        n2 = uniqueList[j]
                        break
                    count += 1

        # Если пары ещё есть добавляем элемент в схемы и заменяем пару в списке на один элемент
        newname = "INT_{0}".format(num)
        num = num + 1
        if (n1[0] != '!' and n2[0] != '!'):
            sckt.__elements__[newname] = ('OR', [n1, n2])
        elif (n1[0] == '!' and n2[0] == '!'):
            sckt.__elements__[newname] = ('NAND', [n1[1:], n2[1:]])
        elif (n1[0] == '!'):
            newname1 = "INT_{0}".format(num)
            num = num + 1
            if random.randint(0, 1) == 0:
                sckt.__elements__[newname1] = ('INV', [n1[1:]])
                sckt.__elements__[newname] = ('OR', [newname1, n2])
            else:
                sckt.__elements__[newname1] = ('INV', [n2])
                sckt.__elements__[newname] = ('NAND', [newname1, n1[1:]])
        elif (n2[0] == '!'):
            newname1 = "INT_{0}".format(num)
            num = num + 1
            if random.randint(0, 1) == 0:
                sckt.__elements__[newname1] = ('INV', [n2[1:]])
                sckt.__elements__[newname] = ('OR', [newname1, n1])
            else:
                sckt.__elements__[newname1] = ('INV', [n1])
                sckt.__elements__[newname] = ('NAND', [newname1, n2[1:]])

        # Заменяем пары в термах
        for o in merge:
            flag = 0
            for term in merge[o]:
                if term.count(n1) > 0:
                    flag = flag + 1
                if term.count(n2) > 0:
                    flag = flag + 1
            if (flag == 2):
                for term in merge[o]:
                    if term.count(n1) > 0:
                        term.remove(n1)
                        continue
                    if term.count(n2) > 0:
                        term.remove(n2)
                        continue
                merge[o].append([newname])

        # Чистим список от пустых записей
        for o in merge:
            for term in merge[o]:
                while (merge[o].count([]) > 0):
                    merge[o].remove([])

    # Теперь требуется заменить имена промежуточных узлов на имена реальных выходов
    for o in merge:
        find = merge[o][0][0]
        replace = o
        # Сначала меняем в поле ключей
        if find in sckt.__elements__:
            sckt.__elements__[replace] = sckt.__elements__[find]
            del sckt.__elements__[find]
        # Затем меняем в элементах
        for el in sckt.__elements__:
            lst = sckt.__elements__[el][1]
            for key,i in enumerate(lst):
                if i == find:
                    lst[key] = replace

    # Фикс для случая когда у нас несколько выходов имеют единую логическую функцию (и часть выходов пропала при замене)
    # В этом случае добавляем буферы
    fix_happened = 0
    for o in merge:
        if o not in sckt.__elements__:
            flag = 0
            for el in sckt.__elements__:
                lst = sckt.__elements__[el][1]
                for key,i in enumerate(lst):
                    if i == o:
                         flag += 1
            if flag == 0:
                f1 = merge[o][0][0]
                fname = ''
                for o1 in merge:
                    if o1 in sckt.__elements__:
                        f2 = merge[o1][0][0]
                        if f1 == f2:
                            fname = o1
                if fname == '':
                    print('Some unexpected error here')
                    break
                sckt.__elements__[o] = ('BUF', [fname])
                fix_happened += 1

    # Фикс для случая когда выход полностью повторяет вход или его инверсию (и он теряется)
    # Необходимо добавить буфер типа (BUF вход выход) или (INV вход выход)
    for o in merge:
        if (len(merge[o]) == 1) & (len(merge[o][0]) == 1):
            if (merge[o][0][0][0] != '!') & (merge[o][0][0] in ckt.__inputs__):
                sckt.__elements__[o] = ('BUF', merge[o][0])
            if (merge[o][0][0][0] == '!') & (merge[o][0][0][1:] in ckt.__inputs__):
                sckt.__elements__[o] = ('INV', [merge[o][0][0][1:]])

    return sckt

def createTMRCirc(ckt):
    out = sa.scheme_alt()
    out.__inputs__ = ckt.__inputs__
    out.__outputs__ = ckt.__outputs__

    # Делаем 3 копии схемы
    for copy in range(1,4):
        for el in ckt.__elements__:
            el1 = "{}_COPY_{}".format(el, copy)
            data = ckt.__elements__[el]
            eltype = data[0]
            lst = []
            for d in data[1]:
                if d not in ckt.__inputs__:
                    lst.append("{}_COPY_{}".format(d, copy))
                else:
                    lst.append(d)

            out.__elements__[el1] = (eltype, lst)

    # Элемент голосования на каждом выходе
    for o in ckt.__outputs__:
        out.__elements__["{}_AND1".format(o)] = ('AND', ["{}_COPY_1".format(o), "{}_COPY_2".format(o)])
        out.__elements__["{}_AND2".format(o)] = ('AND', ["{}_COPY_2".format(o), "{}_COPY_3".format(o)])
        out.__elements__["{}_AND3".format(o)] = ('AND', ["{}_COPY_1".format(o), "{}_COPY_3".format(o)])
        out.__elements__["{}_OR1".format(o)] = ('OR', ["{}_AND1".format(o), "{}_AND2".format(o)])
        out.__elements__[o] = ('OR', ["{}_AND3".format(o), "{}_OR1".format(o)])

    return out

def get_verilog_type(tp):
    if tp == 'INV':
        return 'not'
    if tp == 'BUF':
        return 'buf'
    if tp == 'AND':
        return 'and'
    if tp == 'NAND':
        return 'nand'
    if tp == 'OR':
        return 'or'
    if tp == 'NOR':
        return 'nor'
    if tp == 'XOR':
        return 'xor'
    if tp == 'XNOR':
        return 'xnor'
    return 'UNKNOWN'

def print_circuit_in_verilog_file(circ, circname, file_name):
    f = open(file_name, 'w')  # 'x'

    str = 'module ' + circname + ' ('
    for i in range(circ.inputs()):
        str += (circ.__inputs__[i] + ', ')
    for i in range(circ.outputs()):
        if i > 0:
            str += ', '
        str += circ.__outputs__[i]
    str += ');\n'
    f.write(str)

    for i in range(circ.inputs()):
        f.write("\tinput " + circ.__inputs__[i] + ';\n')
    for i in range(circ.outputs()):
        f.write("\toutput " + circ.__outputs__[i] + ';\n')

    wires = []
    # Добавляем необъявленные выходы в список WIRE
    for el in circ.__elements__:
        out = el
        if out in circ.__inputs__:
            continue
        if out in circ.__outputs__:
            continue
        if out in wires:
            continue
        wires.append(out)

    # Добавляем необъявленные входы элементов в список WIRE
    for el in circ.__elements__:
        inps = circ.__elements__[el][1]
        for inp in inps:
            if inp in circ.__inputs__:
                continue
            if inp in circ.__outputs__:
                continue
            if inp in wires:
                continue
            wires.append(inp)

    for w in wires:
        f.write("\twire " + w + ';\n')

    elindex = 0
    for el in circ.__elements__:
        out = el
        type = get_verilog_type(circ.__elements__[el][0])
        inps = circ.__elements__[el][1]
        str = "\t" + type + " " + "e" + elindex.__str__() + " ("
        str += out
        for inp in inps:
            str += ', ' + inp
        str += ');\n'
        f.write(str)
        elindex += 1

    f.write('endmodule')

    f.close()

def print_run_file(run_file, verilog_file, synth_file, graph):
    f = open(run_file, 'w')
    f.write('read_verilog ' + verilog_file + '\n')
    f.write('synth -top circ\n')
    f.write('dfflibmap -liberty std.lib\n')
    f.write('abc -liberty std.lib\n')
    f.write('clean\n')
    f.write('write_verilog ' + synth_file + '\n')
    # f.write('show -format svg -prefix ' + graph + '\n')
    f.close()

def convert_file_to_relic_format(circuit, synth_file, converted_circuit_file):
    f = open(converted_circuit_file, 'w')
    f.write(circuit.inputs().__str__())
    for inp in circuit.__inputs__:
        f.write(' ' + inp)
    f.write('\n')
    f.write(circuit.outputs().__str__())
    for out in circuit.__outputs__:
        f.write(' ' + out)
    f.write('\n')

    f1 = open(synth_file, 'r')
    content = f1.read()
    # Все элементы
    matches = re.findall(r"\s*?(INV|BUF|AND|NAND|OR|NOR|XOR|XNOR) (.*?) \((.*?);", content, re.DOTALL)
    # Все assign
    matches2 = re.findall(r"\s*?assign (.*?) = (.*?);", content, re.DOTALL)
    total = len(matches) + len(matches2)

    f.write(total.__str__() + '\n')
    for m in matches:
        # print(m[2])
        cell_type = m[0]
        nodes = re.search("\.Y\((.*?)\)", m[2], re.M)
        if nodes is None:
            print('Error converting verilog file (3)')
        out = nodes.group(1)

        nodes = re.search("\.A\((.*?)\)", m[2], re.M)
        if nodes is None:
            print('Error converting verilog file (1)')
        node1 = nodes.group(1)

        if (cell_type != 'INV' and cell_type != 'buf'):
            nodes = re.search("\.B\((.*?)\)", m[2], re.M)
            if nodes is None:
                print('Error converting verilog file (2)')
            node2 = nodes.group(1)

            f.write(cell_type + ' ' + node1 + ' ' + node2 + ' ' + out + '\n')
        else:
            f.write(cell_type + ' ' + node1 + ' ' + out + '\n')

    for m in matches2:
        f.write('BUF ' + m[1] + ' ' + m[0] + '\n')

    f.close()
    f1.close()

# Функция для синтеза схемы с помощью открытого логического синтезатора YOSYS:
# http://www.clifford.at/yosys/about.html

def create_circuit_external_yosys (circuit):
    dfile = get_project_directory()
    run_path = os.path.join(dfile, "utils", "bin", "win32", "yosys")
    yosys_exe = os.path.join(run_path, "yosys.exe")
    circuit_file = os.path.join(dfile, "temp", "tmp_sheme_yosys.v")
    run_file = os.path.join(dfile, "temp", "tmp_runfile_yosys.txt")
    synth_file = os.path.join(dfile, "temp", "tmp_synth.v")
    converted_circuit_file = os.path.join(dfile, "temp", "tmp_synth_conv.txt")
    graph_file = os.path.join(dfile, "temp", "synth.svg")
    debug_file = os.path.join(dfile, "temp", "yosys_fail.txt")

    if os.path.isfile(circuit_file):
        os.remove(circuit_file)
    if os.path.isfile(run_file):
        os.remove(run_file)
    if os.path.isfile(synth_file):
        os.remove(synth_file)
    if os.path.isfile(converted_circuit_file):
        os.remove(converted_circuit_file)

    print_circuit_in_verilog_file(circuit, "circ", circuit_file)
    print_run_file(run_file, circuit_file, synth_file, graph_file)

    exe = yosys_exe + " < " + run_file
    try:
        ret = subprocess.check_output(exe, shell=True, cwd=run_path).decode('UTF-8')
    except:
        ret = 'Error'

    if not os.path.isfile(synth_file):
        # Если была проблема с Yosys выводим схему для последующего дебага
        circuit.print_circuit_in_file(debug_file)
        print('Yosys error')
        return None

    convert_file_to_relic_format(circuit, synth_file, converted_circuit_file)
    if os.path.isfile(converted_circuit_file) == False:
        return None
    new_ckt = sa.read_scheme(converted_circuit_file)
    return new_ckt
