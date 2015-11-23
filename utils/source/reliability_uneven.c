// Usage: <program.exe> <file with circuit> <file with stat_data> <iteration number>
// Example: reliablity.exe "c432.txt" "stat.txt" 10000
// if <iteration number> == -1 then check all possible input vectors
// Example: reliablity.exe "c432.txt" "stat.txt" -1
// Return values: <Reliability> <Time in seconds>
// Example: "45.364377 7.234"
// Важно: можно использовать только для маленьких схем (из-за полного перебора)!

#include <omp.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <math.h>
#include <assert.h>
#include <time.h>
#include <random>
#include <iostream>

using namespace std;

#define INT_REL unsigned long long
#define ZERO 0ull
#define ONE 1ull
#define MAX_NUMBER_OF_ELEMENTS 100000

struct node {
	char type; // 0 - INPUT, 1 - WIRE, 2 - OUTPUT
	char name[128];
	struct element *fanin; // У узла только один вход
	int oNum;
	struct element **fanout; // У узла может быть много выходов

	// Переменные для параллельных рассчетов (массивы размером numthreads)
	char *proc; // Обработан или не обработан узел (0 - необработан, 1 - обработан)
	INT_REL *valWithoutErr; // Логическое значение 0 или 1
	INT_REL *valWithErr; // Логическое значение 0 или 1
};

struct element {
	char type; // 1 INV 2 AND 3 OR 4 NAND 5 NOR 6 XOR 7 BUF 8 XNOR
	int level;
	struct node *inp1;
	struct node *inp2;
	struct node *out;

	// Переменные для параллельных рассчетов (массивы размером numthreads)
	INT_REL *proc; // Для рассчетов (0 - не обработано, 1 - обработано)
	INT_REL *failure; // (0 - на элементе нет ошибки, 1 - на элементе есть ошибка)
};

/****************************************
GLOBAL VARIABLES START
*****************************************/

struct node *nl;
int nlNum;

struct element *el;
int elNum;

// Массив для быстрого распрастранения сигнала
struct element **elPA;

int inNum;
int outNum;

// Число потоков программы
int numthreads;
// Число одновременно обрабатываемых схем
int simbits;

double *interDistribution;
double **outputMatrixError;

/* Генератор случайных чисел */
#define BITS_PER_CALL_GENERATOR 16
random_device rand_device;   // non-deterministic generator
mt19937 generator(rand_device());
uniform_int_distribution<> uniform_distribution(0, (1 << BITS_PER_CALL_GENERATOR) - 1);

/****************************************
GLOBAL VARIABLES END
*****************************************/

// Поиск узла в общем пуле
struct node *findNode(struct node *n, int nLen, char *str) {
	int i;
	for (i = 0; i < nLen; i++) {
		if (!strcmp(n[i].name, str))
			return &(n[i]);
	}
	return NULL;
}

// Добавить узел
struct node *addNode(
struct node *n,
	int *nLen,
	char *str
	) {
	strcpy(n[(*nLen)].name, str);
	n[*nLen].type = 1;
	n[*nLen].fanin = NULL;
	n[*nLen].fanout = NULL;
	n[*nLen].oNum = 0;
	(*nLen)++;
	return &(n[(*nLen) - 1]);
}

void addNodeFanin(
struct node *n,
struct element *e)
{
	if (n->fanin != NULL)
	{
		fprintf(stderr, "2 cells connected to one node with outputs!\n");
	}
	n->fanin = e;
}

void addNodeFanout(
struct node *n,
struct element *e)
{
	int s = n->oNum + 1;
	n->fanout = (struct element **)realloc(n->fanout, s*sizeof(struct element *));
	n->fanout[n->oNum] = e;
	n->oNum++;
}

void clear_state(int id) {
	int i;
	for (i = 0; i < nlNum; i++) {
		nl[i].proc[id] = 0;
		nl[i].valWithErr[id] = ZERO;
		nl[i].valWithoutErr[id] = ZERO;
	}
	for (i = 0; i < elNum; i++) {
		el[i].failure[id] = ZERO;
		el[i].proc[id] = ZERO;
	}
}

void fill_levels() {
	int i, flag, l1;

	/* Сбрасываем внутренние переменные */
	clear_state(0);
	for (i = 0; i < elNum; i++) {
		el[i].level = -1;
	}
	for (i = 0; i < inNum; i++) {
		nl[i].proc[0] = 1;
	}

	/* Ставим первый уровень */
	for (i = 0; i < elNum; i++) {
		if (el[i].type == 1 || el[i].type == 7) {
			if (el[i].inp1->proc[0] == 1)
				el[i].level = 1;
		}
		else {
			if (el[i].inp1->proc[0] == 1 && el[i].inp2->proc[0] == 1)
				el[i].level = 1;
		}
	}

	flag = 1;
	while (flag) {
		flag = 0;
		for (i = 0; i < elNum; i++) {
			if (el[i].level != -1)
				continue;
			if (el[i].type == 1 || el[i].type == 7) {
				if (el[i].inp1->fanin != NULL)
					if (el[i].inp1->fanin->level != -1) {
						el[i].level = el[i].inp1->fanin->level + 1;
						flag++;
					}
			}
			else {
				l1 = -1;
				if (el[i].inp1->fanin != NULL) {
					if (el[i].inp1->fanin->level != -1) {
						l1 = el[i].inp1->fanin->level + 1;
					}
					else {
						continue;
					}
				}
				if (el[i].inp2->fanin != NULL) {
					if (el[i].inp2->fanin->level != -1) {
						if (el[i].inp2->fanin->level + 1 > l1)
							l1 = el[i].inp2->fanin->level + 1;
					}
					else {
						continue;
					}
				}
				el[i].level = l1;
				flag++;
			}
		}
	}

	// Проверяем что все элементы пронумерованы
	for (i = 0; i < elNum; i++) {
		if (el[i].level == -1) {
			fprintf(stderr, "Unreachable part of circuit (%d %s %s %s)!\n", el[i].type, el[i].inp1->name, el[i].inp2->name, el[i].out->name);
			exit(0);
		}
	}

	// Проверка на обратные связи
	for (i = 0; i < elNum; i++) {
		if (el[i].type == 1 || el[i].type == 7) {
			if (el[i].inp1->fanin != NULL) {
				if (el[i].level <= el[i].inp1->fanin->level) {
					fprintf(stderr, "Found level problem INV or BUF\n");
					exit(0);
				}
			}
		}
		else {
			if (el[i].inp1->fanin != NULL) {
				if (el[i].level <= el[i].inp1->fanin->level) {
					fprintf(stderr, "Found level problem 1 %s %s %s\n", el[i].inp1->name, el[i].inp2->name, el[i].out->name);
					exit(0);
				}
			}
			if (el[i].inp2->fanin != NULL) {
				if (el[i].level <= el[i].inp2->fanin->level) {
					fprintf(stderr, "Found level problem 2 %s %s %s\n", el[i].inp1->name, el[i].inp2->name, el[i].out->name);
					exit(0);
				}
			}
		}
	}
}

INT_REL setbit(INT_REL val, char pos, char bit) {
	INT_REL op1 = (INT_REL)bit;
	INT_REL op2 = (INT_REL)pos;
	val = val | (op1 << op2); 
	return val;
}

char getbit(INT_REL val, char pos) {
	INT_REL op1 = (INT_REL)pos;
	INT_REL op2 = ONE;
	INT_REL res = (val >> op1) & op2;
	return (char) res;
}

void dice(int id) {
	int i;
	INT_REL k;
	INT_REL dt;
	INT_REL rand_variable;

	for (i = 0; i < inNum; i++) {
		if (nl[i].type != 0) {
			fprintf(stderr, "Judge problem 1!\n");
			return;
		}
		nl[i].proc[id] = 1;
		rand_variable = 0;
		for (k = 0; k < simbits; k += BITS_PER_CALL_GENERATOR) {
			// dt = rand() % (ONE << BITS_PER_CALL_GENERATOR);
			dt = uniform_distribution(generator);
			rand_variable += dt << k;
		}
		nl[i].valWithErr[id] = rand_variable;
		nl[i].valWithoutErr[id] = rand_variable;
	}
}

void set_input_vector(int vec, int id) {
	int i;
	char dt;
	char j;

	for (i = 0; i < inNum; i++) {
		if (nl[i].type != 0) {
			fprintf(stderr, "Input problem 1!\n");
			return;
		}
		nl[i].proc[id] = 1;
		for (j = 0; j < simbits; j++) {
			dt = ((vec+j) >> i) & 1;
			nl[i].valWithErr[id] = setbit(nl[i].valWithErr[id], j, dt);
			nl[i].valWithoutErr[id] = setbit(nl[i].valWithoutErr[id], j, dt);
		}
	}
}

void propagate(struct element **eArr, int eLen, int id) {
	int i, flag;
	struct element *e;

	for (i = 0; i < eLen; i++) {
		e = eArr[i];
		if (e->type == 1) {
			// INV
			if (e->inp1->proc[id] == 0) {
				fprintf(stderr, "Problem with propagation (INV)!\n");
			}
			e->out->proc[id] = 1;
			e->out->valWithoutErr[id] = ~(e->inp1->valWithoutErr[id]);
			if (e->failure[id] == ONE) {
				e->out->valWithErr[id] = e->inp1->valWithErr[id];
			} else {
				e->out->valWithErr[id] = ~(e->inp1->valWithErr[id]);
			}
			e->proc[id] = 1;
			flag = 1;

		}
		else if (e->type == 7) {
			// BUF (this cell made with zero error rate)
			if (e->inp1->proc[id] == 0) {
				fprintf(stderr, "Problem with propagation (BUF)!\n");
			}
			e->out->valWithErr[id] = e->inp1->valWithErr[id];
			e->out->valWithoutErr[id] = e->inp1->valWithoutErr[id];
			e->proc[id] = 1;
			e->out->proc[id] = 1;
			flag = 1;

		}
		else {
			if (e->inp1->proc[id] == 0 || e->inp2->proc[id] == 0) {
				fprintf(stderr, "Problem with propagation!\n");
			}
			if (e->type == 2) {
				// AND
				e->out->valWithErr[id] = e->inp1->valWithErr[id] & e->inp2->valWithErr[id];
				e->out->valWithoutErr[id] = e->inp1->valWithoutErr[id] & e->inp2->valWithoutErr[id];
			}
			else if (e->type == 3) {
				// OR
				e->out->valWithErr[id] = e->inp1->valWithErr[id] | e->inp2->valWithErr[id];
				e->out->valWithoutErr[id] = e->inp1->valWithoutErr[id] | e->inp2->valWithoutErr[id];
			}
			else if (e->type == 4) {
				// NAND
				e->out->valWithErr[id] = ~(e->inp1->valWithErr[id] & e->inp2->valWithErr[id]);
				e->out->valWithoutErr[id] = ~(e->inp1->valWithoutErr[id] & e->inp2->valWithoutErr[id]);
			}
			else if (e->type == 5) {
				// NOR
				e->out->valWithErr[id] = ~(e->inp1->valWithErr[id] | e->inp2->valWithErr[id]);
				e->out->valWithoutErr[id] = ~(e->inp1->valWithoutErr[id] | e->inp2->valWithoutErr[id]);
			}
			else if (e->type == 6) {
				// XOR
				e->out->valWithErr[id] = e->inp1->valWithErr[id] ^ e->inp2->valWithErr[id];
				e->out->valWithoutErr[id] = e->inp1->valWithoutErr[id] ^ e->inp2->valWithoutErr[id];
			}
			else if (e->type == 8) {
				// XNOR
				e->out->valWithErr[id] = ~(e->inp1->valWithErr[id] ^ e->inp2->valWithErr[id]);
				e->out->valWithoutErr[id] = ~(e->inp1->valWithoutErr[id] ^ e->inp2->valWithoutErr[id]);
			}
			if (e->failure[id] == ONE) {
				e->out->valWithErr[id] = ~(e->out->valWithErr[id]);
			}
			e->proc[id] = 1;
			e->out->proc[id] = 1;
			flag = 1;
		}
	}
}

int compare_same(int id) {
	int i;
	int count = 0;
	char j;
	char bit1, bit2;

	for (j = 0; j < simbits; j++) {
		for (i = inNum; i < inNum + outNum; i++) {
			if (nl[i].proc[id] == 0) {
				fprintf(stderr, "Propagation problem 2!\n");
				exit(1);
			}
			bit1 = getbit(nl[i].valWithErr[id], j);
			bit2 = getbit(nl[i].valWithoutErr[id], j);
			if (bit1 != bit2) {
				count++;
				break;
			}
		}
	}
	return count;
}

void freePreviousData() {
	int i, j;

	/* Чистим память и данные по схемам */
	for (i = 0; i < nlNum; i++) {
		free(nl[i].fanout);
		nl[i].fanout = NULL;
		nl[i].fanin = NULL;
		nl[i].oNum = 0;
		for (j = 0; j < numthreads; j++) {
			nl[i].proc[j] = 0;
			nl[i].valWithErr[j] = ZERO;
			nl[i].valWithoutErr[j] = ZERO;
		}
		strcpy(nl[i].name, "");
	}
	for (i = 0; i < elNum; i++) {
		el[i].type = 0;
		for (j = 0; j < numthreads; j++) {
			el[i].proc[j] = ZERO;
			el[i].failure[j] = ZERO;
		}
		el[i].inp1 = NULL;
		el[i].inp2 = NULL;
		el[i].out = NULL;
		el[i].level = 0;
	}
	nlNum = 0;
	elNum = 0;
	inNum = 0;
	outNum = 0;
}

void create_prop_arrays() {
	int i, flag;
	int ind;

	/* Сбрасываем внутренние переменные */
	clear_state(0);
	for (i = 0; i < inNum; i++) {
		nl[i].proc[0] = 1;
		nl[i].valWithErr[0] = (INT_REL) 0;
		nl[i].valWithoutErr[0] = (INT_REL) 0;
	}

	/* Формируем массив для тестовой схемы */
	flag = 1;
	ind = 0;
	while (flag) {
		flag = 0;
		for (i = 0; i < elNum; i++) {
			if (el[i].proc[0] == 1)
				continue;
			if (el[i].type == 1 || el[i].type == 7) {
				// INV
				if (el[i].inp1->proc[0] != 0) {
					el[i].out->proc[0] = 1;
					el[i].out->valWithErr[0] = (INT_REL) 0;
					el[i].out->valWithoutErr[0] = (INT_REL) 0;
					elPA[ind] = &(el[i]);
					ind++;
					el[i].proc[0] = 1;
					flag = 1;
				}
			}
			else {
				if (el[i].inp1->proc[0] != 0 && el[i].inp2->proc[0] != 0) {
					el[i].out->proc[0] = 1;
					el[i].out->valWithErr[0] = (INT_REL) 0;
					el[i].out->valWithoutErr[0] = (INT_REL) 0;
					elPA[ind] = &(el[i]);
					ind++;
					el[i].proc[0] = 1;
					flag = 1;
				}
			}
		}
	}
	if (ind != elNum) {
		struct element *echeck;
		fprintf(stderr, "Not reachable parts of circuits (%d != %d)!\n", ind, elNum);
		for (i = 0; i < elNum; i++) {
			echeck = &(el[i]);
			if (echeck->out->proc[0] == 0) {
				if (echeck->type != 1 && echeck->type != 7) {
					if (echeck->inp1->proc[0] == 0 && echeck->inp2->proc[0] != 0) {
						fprintf(stderr, "Type 1: %d %s %s\n", i, echeck->out->name, echeck->inp1->name);
					}
					else if (echeck->inp1->proc[0] != 0 && echeck->inp2->proc[0] == 0) {
						fprintf(stderr, "Type 2: %d %s %s\n", i, echeck->out->name, echeck->inp2->name);
					}
					else if (echeck->inp1->proc[0] == 0 && echeck->inp2->proc[0] == 0) {
						fprintf(stderr, "Type 3: %d %s %s %s\n", i, echeck->out->name, echeck->inp1->name, echeck->inp2->name);
					}
					else if (echeck->inp1->proc[0] != 0 && echeck->inp2->proc[0] != 0) {
						fprintf(stderr, "Type 4: %d %s %s %s\n", i, echeck->out->name, echeck->inp1->name, echeck->inp2->name);
					}
					else {
						fprintf(stderr, "Type UNKNOWN: %d %s %s\n", i, echeck->out->name, echeck->inp2->name);
					}
				}
				else {
					if (echeck->inp1->proc[0] == 0) {
						fprintf(stderr, "Type INV 1: %d %s %s\n", i, echeck->out->name, echeck->inp1->name);
					}
					else if (echeck->inp1->proc[0] != 0) {
						fprintf(stderr, "Type INV 2: %d %s %s\n", i, echeck->out->name, echeck->inp1->name);
					}
					else {
						fprintf(stderr, "Type INV UNKNOWN\n");
					}
				}
			}
		}
		for (i = 0; i < nlNum; i++) {
			if (nl[i].proc[0] == 0 && nl[i].fanin != NULL) {
				if (nl[i].fanin->type != 1 && nl[i].fanin->type != 7) {
					if (nl[i].fanin->inp1->proc[0] != 0 && nl[i].fanin->inp2->proc[0] != 0)
						fprintf(stderr, "OPA: %s\n", nl[i].name);
				}
				else {
					if (nl[i].fanin->inp1->proc[0] != 0)
						fprintf(stderr, "OPA: %s\n", nl[i].name);
				}
			}
		}
	}
}

void read_data(
	FILE *in
) {
	int i;
	char buf[1024];

	nl = (struct node *)calloc(MAX_NUMBER_OF_ELEMENTS, sizeof(struct node));
	el = (struct element *)calloc(MAX_NUMBER_OF_ELEMENTS, sizeof(struct element));
	elPA = (struct element **)calloc(MAX_NUMBER_OF_ELEMENTS, sizeof(struct element *));

	/* Создаем переменные для параллельной обработки */
	for (i = 0; i < MAX_NUMBER_OF_ELEMENTS; i++) {
		nl[i].proc = (char *)calloc(numthreads, sizeof(char));
		nl[i].valWithErr = (INT_REL *)calloc(numthreads, sizeof(INT_REL));
		nl[i].valWithoutErr = (INT_REL *)calloc(numthreads, sizeof(INT_REL));
		el[i].failure = (INT_REL *)calloc(numthreads, sizeof(INT_REL));
		el[i].proc = (INT_REL *)calloc(numthreads, sizeof(INT_REL));
	}

	/* Читаем схему оригинал */
	fscanf(in, "%d", &inNum);
	for (i = 0; i < inNum; i++) {
		fscanf(in, "%s", nl[nlNum].name);
		nl[nlNum].type = 0;
		nlNum++;
	}
	fscanf(in, "%d", &outNum);
	for (i = 0; i < outNum; i++) {
		fscanf(in, "%s", nl[nlNum].name);
		nl[nlNum].type = 2;
		nlNum++;
	}
	fscanf(in, "%d", &elNum);
	for (i = 0; i < elNum; i++) {
		fscanf(in, "%s", buf);
		if (!strcmp(buf, "INV") || !strcmp(buf, "BUF"))
		{
			if (!strcmp(buf, "INV")) {
				el[i].type = 1;
			}
			else if (!strcmp(buf, "BUF")) {
				el[i].type = 7;
			}
			fscanf(in, "%s", buf);
			el[i].inp1 = findNode(nl, nlNum, buf);
			el[i].inp2 = NULL;
			if (el[i].inp1 == NULL) {
				el[i].inp1 = addNode(nl, &nlNum, buf);
			}
			addNodeFanout(el[i].inp1, &(el[i]));

		}
		else {
			if (!strcmp(buf, "AND")) {
				el[i].type = 2;
			}
			else if (!strcmp(buf, "OR")) {
				el[i].type = 3;
			}
			else if (!strcmp(buf, "NAND")) {
				el[i].type = 4;
			}
			else if (!strcmp(buf, "NOR")) {
				el[i].type = 5;
			}
			else if (!strcmp(buf, "XOR")) {
				el[i].type = 6;
			}
			else if (!strcmp(buf, "XNOR")) {
				el[i].type = 8;
			}
			else {
				fprintf(stderr, "Unknown cell type!\n");
				exit(1);
			}
			fscanf(in, "%s", buf);
			el[i].inp1 = findNode(nl, nlNum, buf);
			if (el[i].inp1 == NULL) {
				el[i].inp1 = addNode(nl, &nlNum, buf);
			}
			addNodeFanout(el[i].inp1, &(el[i]));

			fscanf(in, "%s", buf);
			el[i].inp2 = findNode(nl, nlNum, buf);
			if (el[i].inp2 == NULL) {
				el[i].inp2 = addNode(nl, &nlNum, buf);
			}
			addNodeFanout(el[i].inp2, &(el[i]));
		}
		/* Выход схемы */
		fscanf(in, "%s", buf);
		el[i].out = findNode(nl, nlNum, buf);
		if (el[i].out == NULL) {
			el[i].out = addNode(nl, &nlNum, buf);
		}
		addNodeFanin(el[i].out, &(el[i]));
	}
}

void read_distrib_data(FILE *in) {
	int i, j;

	interDistribution = (double *)calloc((1 << inNum), sizeof(double));
	outputMatrixError = (double **)calloc((1 << outNum), sizeof(double*));
	for (i = 0; i < (1 << outNum); i++) {
		outputMatrixError[i] = (double *)calloc((1 << outNum), sizeof(double));
	}

	for (i = 0; i < (1 << inNum); i++) {
		fscanf(in, "%lf", &(interDistribution[i]));
	}

	for (i = 0; i < (1 << outNum); i++) {
		for (j = 0; j < (1 << outNum); j++) {
			fscanf(in, "%lf", &(outputMatrixError[i][j]));
		}
	}

}

void free_data_final() {
	int i;

	freePreviousData();

	/* Удаляем переменные для параллельной обработки */
	for (i = 0; i < MAX_NUMBER_OF_ELEMENTS; i++) {
		free(nl[i].proc);
		free(nl[i].valWithErr);
		free(nl[i].valWithoutErr);
		free(el[i].failure);
		free(el[i].proc);
	}

	free(interDistribution);
	for (i = 0; i < 1 << outNum; i++) {
		free(outputMatrixError[i]);
	}
	free(outputMatrixError);

	free(nl);
	free(el);
	free(elPA);
}

// Возвращает 1 если тесты совпали и 0 если не совпали
int compare_same_by_bit(int id, int bit) {
	int i;
	int count = 0;
	char bit1, bit2;

	for (i = inNum; i < inNum + outNum; i++) {
		if (nl[i].proc[id] == 0) {
			fprintf(stderr, "Propagation problem 2!\n");
			exit(1);
		}
		bit1 = getbit(nl[i].valWithErr[id], bit);
		bit2 = getbit(nl[i].valWithoutErr[id], bit);
		if (bit1 != bit2) {
			return 0;
		}
	}
	return 1;
}

double find_reliability_for_iteration(int id) {
	int i, j;
	double res;
	int out_number;
	int same, bit;
	int input_vector;
	int out_etalon;
	int out_error;
	
	res = 0.0;
	for (i = 0; i < simbits; i++) {
		same = compare_same_by_bit(id, i); // Проверяем выходы схем на одинаковые значения
		if (!same) {
			// Считаем индекс входного вектора
			input_vector = 0;
			for (j = 0; j < inNum; j++) {
				bit = getbit(nl[j].valWithoutErr[id], i);
				input_vector += (bit << j);
			}
			// Считаем индексы матрицы выходов
			out_etalon = 0;
			out_error = 0;
			for (j = inNum; j < inNum + outNum; j++) {
				out_number = j - inNum;
				bit = getbit(nl[j].valWithoutErr[id], i);
				out_etalon += (bit << out_number);
				bit = getbit(nl[j].valWithErr[id], i);
				out_error += (bit << out_number);
			}
			res += interDistribution[input_vector] * outputMatrixError[out_etalon][out_error];
			// printf("Input vec: %d, Etalon vec: %d, Err vec: %d, Distr: %lf Matrix: %lf\n", input_vector, out_etalon, out_error, interDistribution[input_vector], outputMatrixError[out_etalon][out_error]);
		}
	}
	return res;
}

int main(int argc, char **argv)
{
	int i, iterator;
	int test_num = 0;
	clock_t timeStart, timeEnd;
	double tm;
	int total_iter;
	int full_search;
	int monte_carlo_iter;
	int mciter;
	FILE *in;
	FILE *indistr;
	int total_mc = 0;
	double reliability;
	double *incorr_res;
	int tid = 0;
	
	srand((unsigned)time(NULL));

	// Ставим число потоков
	numthreads = omp_get_num_procs() - 1;
	if (numthreads < 1)
		numthreads = 1;
			
	if (argc != 4) {
		printf("Invalid parameters! Must be: <program.exe> <file with circuit> <file with distribution> <iteration number>\n");
		return 1;
	}

	in = fopen(argv[1], "r");
	if (in == NULL) {
		printf("Check file (%s)!\n", argv[1]);
		return 1;
	}
	indistr = fopen(argv[2], "r");
	if (in == NULL) {
		printf("Check file (%s)!\n", argv[2]);
		return 1;
	}
	mciter = atoi(argv[3]);
	timeStart = clock();
	nlNum = 0;
	
	// Ставим число бит
	simbits = 8 * sizeof(INT_REL);

	/* Читаем данные из файлов */
	read_data(in);
	
	if (inNum > 16) {
		fprintf(stderr, "Too large number of internal nodes (%d). Currently we support only 16\n", inNum);
		exit(1);
	}
	if (outNum > 12) {
		fprintf(stderr, "Too large number of internal output nodes (%d). Currently we support only 12\n", outNum);
		exit(1);
	}

	// Случай если число тестов больше полного перебора
	if (mciter != -1 && inNum < 32) {
		if (mciter > (1 << inNum)) {
			mciter = -1;
		}
	}

	// Если число нужных тестов меньше чем число бит под моделирование (возможно для маленьких схем)
	if (mciter == -1 && inNum < 32) {
		if ((1 << inNum) < simbits) {
			simbits = (1 << inNum);
		}
	}

	read_distrib_data(indistr);

	if (mciter == -1) {
		if (inNum > 16) {
			fprintf(stderr, "Too large number of inputs (%d). We can't use full search here\n", inNum);
			exit(1);
		}
		full_search = 1;
		monte_carlo_iter = (1 << inNum)/simbits;
	}
	else {
		full_search = 0;
		monte_carlo_iter = mciter/simbits + 1;
	}

	/* Заполняем уровни */
	fill_levels();
	/* Делаем массивы для быстрого обхода схемы */
	create_prop_arrays();

	/* Моделирование неисправностей */
	incorr_res = (double *)calloc(elNum, sizeof(double));
	for (i = 0; i < elNum; i++) {
		incorr_res[i] = 0.0;
	}
	total_iter = elNum*monte_carlo_iter;

	// Объединяем два цикла в один для облегчения параллелизма
	#pragma omp parallel for firstprivate(iterator) num_threads(numthreads)
	for (iterator = 0; iterator < total_iter; iterator++) {
		int tid = omp_get_thread_num();
		int elem_index = iterator / monte_carlo_iter;
		int mc_iteration = iterator % monte_carlo_iter;
		double rel_val;

		clear_state(tid); // Сбрасываем все данные по рассчетам
		el[elem_index].failure[tid] = ONE; // Кидаем нисправность на конкретный элемент
		if (full_search == 0) {
			dice(tid); // Кидаем кубики со значениями на входы схем
		}
		else {
			set_input_vector(mc_iteration*simbits, tid); // Устанавливаем конкретное значение на входы схемы
		}
		propagate(elPA, elNum, tid); // Распространяем логику от входов к выходам тестовой схемы
		rel_val = find_reliability_for_iteration(tid); // Считаем надежность
		#pragma omp critical
		{
			incorr_res[elem_index] += rel_val;
		}
	}
	
	/* Считаем финальную надежность */
	reliability = 0.0;
	for (i = 0; i < elNum; i++) {
		reliability += incorr_res[i];
	}
	
	timeEnd = clock();
	tm = (float)(timeEnd - timeStart);
	printf("%.18lf %.3f", reliability, tm / CLOCKS_PER_SEC);

	free(incorr_res);
	free_data_final();
	fclose(in);
	fclose(indistr);
	return 0;
}
