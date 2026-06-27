#!/usr/bin/env python3

import csv
import sys
import multiprocessing
import time
import os

def loadData(id):
    sys.argv.extend(["--node_id", "P{}".format(id)])
    # sys.argv.extend(["--node_id", id])
    import latticex.rosetta as rtt

    import tensorflow as tf
    import numpy as np

    rtt.activate("SecureNN")

    path0 = 'dataset/dataset0.csv'
    path1 = 'dataset/dataset1.csv'

    header0 = ['ID', 'AGE', 'CARD']
    header1 = ['ID', 'CREDIT', 'DEPOSIT']

    '''
    Step1. P0, P1 and P2 upload the dataset and generate the secret share
    '''
    if id == 0:
        dataset0 = np.loadtxt(open(path0), delimiter = ",", skiprows = 1)
        rtx = rtt.controller.PrivateDataset(["P0"]).load_X(dataset0)
        rty = rtt.controller.PrivateDataset(["P1"]).load_X(None)
        rtz = rtt.controller.PrivateDataset(["P2"]).load_X(None)
    elif id == 1:
        dataset1 = np.loadtxt(open(path1), delimiter = ",", skiprows = 1)
        rtx = rtt.controller.PrivateDataset(["P0"]).load_X(None)
        rty = rtt.controller.PrivateDataset(["P1"]).load_X(dataset1)
        rtz = rtt.controller.PrivateDataset(["P2"]).load_X(None)
    else:
        '''
        P2 don't have dataset2, so replace as an int.
        
        In this module, we could generate the 1's secret share, facilitate subsequent use of 1's secret sharing
        '''
        dataset2 = [[1]]
        rtx = rtt.controller.PrivateDataset(["P0"]).load_X(None)
        rty = rtt.controller.PrivateDataset(["P1"]).load_X(None)
        rtz = rtt.controller.PrivateDataset(["P2"]).load_X(dataset2)
    # print(type(rtx))
    
    return [rtx, rty, rtz]