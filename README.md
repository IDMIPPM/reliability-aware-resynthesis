# reliability-aware-resynthesis
Experimental programm for reliability aware resynthesis (RELIC) 

Input data - combinational circuit (without memory elements) synthesised in basis: INV, AND, NAND, OR, NOR, XOR, XNOR.<br />
Output data - curciut with same logical function but more reliable to single event upset (SEU)<br />

## Input data format:

```
<number of inputs> <input list>
<number of outputs> <output list>
<number of elements>
<element type> <input1> <input2> <output1>
.....
<element type> <input1> <input2> <output1>
```
## Example:

```
5 N1 N2 N3 N6 N7
2 N22 N23
6
NAND N1 N3 N10
NAND N3 N6 N11
NAND N2 N11 N16
NAND N11 N7 N19
NAND N10 N16 N22
NAND N16 N19 N23
```
## Directory structure:

- circuits - sample circuits for analysis<br />
- relic - Python sources<br />
-- resynthesis - main module<br />
-- resynthesis_main.py - main RUN-file<br />
- temp - folder for storing intermediate and final data needed for RELIC<br />
- utils - additional programs and sources needed for RELIC<br />
-- bin - binaries<br />
--- win32 - windows sources<br />
---- espresso - espresso binaries<br />
---- yosys - YOSYS binaries<br />
---- distrib_estim_mt.exe - WIN32 binaries based on C-code. Fast version of function to find signal distribution on subckt inputs and error observability matrix at subckt outputs.<br />
---- reliability_uneven.exe - WIN32 binaries based on C-code. Fast version of function to calculate sensitivity coefficient of subckt based on input distribution and error observability matrix<br />
---- vulnerability_map.exe - WIN32 binaries based on C-code. Fast version of function to find sensitivity coefficient for large logic circuit using Monte Carlo method.<br />
---- vcomp140.dll - Part of VC2015 redistributable for running OpenMP programs. Required by distrib_estim_mt.exe, reliability_uneven.exe and vulnerability_map.exe.<br />
--- linux - linux sources (currently absent)<br />
-- source - C-sources<br />
--- distrib_estim_mt.c - Fast version of function to find signal distribution on subckt inputs and error observability matrix at subckt outputs. Multithreaded version.<br />
--- reliability_uneven.c - Fast version of function to calculate sensitivity coefficient of subckt based on input distribution and error observability matrix. Multithreaded version.<br />
--- vulnerability_map.c - Fast version of function to find sensitivity coefficient for large logic circuit using Monte Carlo method. Multithreaded version.<br />
<br />

## Notes:

RELIC now support only Windows. It can be used on Linux, but you need to prepare the following binaries:
Yosys, yosys-abc, espresso and also compile C-files: "distrib_estim_mt_fast.c", "reliability_uneven.c" and "vulnerability_map.c" with OpenMP support.<br />
