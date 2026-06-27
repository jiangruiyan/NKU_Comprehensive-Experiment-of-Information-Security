#!/usr/bin/env python3

from loadData import *
import csv
import sys
import multiprocessing
import time
import os

def PSI(id):
    sys.argv.extend(["--node_id", "P{}".format(id)])
    # sys.argv.extend(["--node_id", id])
    import latticex.rosetta as rtt

    import tensorflow as tf
    import numpy as np
    '''
    For this PSI module, you only need to implement the following functions:
    
    If dataset1 is:     dataset2 is:
    ID    AGE           ID    DEPOSIT
    1000  25            1000  50000
    1001  23            2001  300000
    1002  40            2002  350000
    1003  56            1003  20000
    1004  37            1004  280000
    1005  32            2005  150000
    
    Tips: The loading module of this data set has already given the interface in loadData.py, just call it directly.
    After PSI and merge the dataset, you should return a merged ciphertext table. You can reveal your ciphertext table to verify correctness.
    After revealing, your plaintext table should be:
    
    ID       AGE       DEPOSIT
    b'1000'  b'25'     b'50000'
    b'0'     b'0'      b'0'
    b'0'     b'0'      b'0'
    b'1003'  b'56'     b'20000'
    b'1004'  b'37'     b'280000'
    b'0'     b'0'      b'0'
        
    Code here!
    '''
    