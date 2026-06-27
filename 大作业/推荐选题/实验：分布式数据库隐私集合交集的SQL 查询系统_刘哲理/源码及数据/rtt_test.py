#!/usr/bin/env python3

import multiprocessing
import sys
import tensorflow as tf
import numpy as np
import random

def rtt_test(id):
    '''
    This module will tell you how to use rosetta to develop your project~
    '''

    '''
    Step1. You need to import rosetta into your project, and specify the names of the parties.
    '''
    sys.argv.extend(["--node_id", "P{}".format(id)])
    import latticex.rosetta as rtt
    rtt.activate("SecureNN")

    '''
    Step2. Parties will upload their datasets. In this demo, we specify P0 and P1 to upload data.

    (Note. In this demo I just generate the random numpy matrix to illustrate the module. But in your project, 
    you need to read the data set from csv, I have written all these code for you, just call the relevant API directly.)
    '''
    rd = np.random.RandomState(1789)
    mat1 = rd.randint(0, 10, (3, 2))
    mat2 = rd.randint(0, 10, (2, 5))

    print('mat1:\n', mat1)
    print('mat2:\n', mat2)

    if id == 0:
        rtx = rtt.controller.PrivateDataset(["P0"]).load_X(mat1)
        rty = rtt.controller.PrivateDataset(["P1"]).load_X(None)
        rtz = rtt.controller.PrivateDataset(["P2"]).load_X(None)
    elif id == 1:
        rtx = rtt.controller.PrivateDataset(["P0"]).load_X(None)
        rty = rtt.controller.PrivateDataset(["P1"]).load_X(mat2)
        rtz = rtt.controller.PrivateDataset(["P2"]).load_X(None)
    else:
        '''
        P2 don't have dataset2, so replace as a random int.
        '''
        b = [[rd.randint(0, 1)]]
        rtx = rtt.controller.PrivateDataset(["P0"]).load_X(None)
        rty = rtt.controller.PrivateDataset(["P1"]).load_X(None)
        rtz = rtt.controller.PrivateDataset(["P2"]).load_X(b)

    '''
    Step3. We should call the rtt.SecureOp to compelete our project.

    In this demo, we want to compute the matrix multiply use MPC API.
    '''
    rtt_res = rtt.SecureMatMul(rtx, rty)

    '''
    Step4. Run the task use tensorflow
    '''
    sess = tf.Session()
    sess.run(tf.global_variables_initializer())

    '''
    Step5. Take a glance at your ciphertext
    '''
    print('From ID:{} ciphertext result:\n'.format(id), sess.run(rtt_res))

    '''
    Step6. If you want to check your code, you can call rtt.SecureReveal
    '''
    print('From ID:{} plaintext result:\n'.format(id), sess.run(rtt.SecureReveal(rtt_res)))

    '''
    Step7. Finally, you just tab 'python3 rtt_test.py' into your terminal and run.
    '''

p0 = multiprocessing.Process(target = rtt_test, args = (0,))
p1 = multiprocessing.Process(target = rtt_test, args = (1,))
p2 = multiprocessing.Process(target = rtt_test, args = (2,))

p0.daemon = True
p0.start()
p1.daemon = True
p1.start()
p2.daemon = True
p2.start()

p0.join()
p1.join()
p2.join()