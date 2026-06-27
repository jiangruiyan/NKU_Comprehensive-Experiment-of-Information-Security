from loadData import *
from PSI import *
from SQLparse import *
from AST import *

def computePostfix(id, postexp, cipherTable, header):
    '''
    This function will compute the result according to postfix expressions
    
    Tips:
    Before compute the intermediate results, you should judge the type of each opearand from the stack's top:
        If operand is digit, generate the share of digit directly
        If operand is string, select the cipher column from the ciphertable
        If operand is Tensor, use it directly
    '''
    operand = []
    
    '''
    Code here!
    '''

    return operand.pop()


def execute(id, SQL, header):
    sys.argv.extend(["--node_id", "P{}".format(id)])
    
    # sys.argv.extend(["--node_id", id])
    import latticex.rosetta as rtt

    import tensorflow as tf
    import numpy as np

    rtt.activate("SecureNN")
    
    '''
    Step1. Load the dataset and PSI
    
    Code here!
    '''
    psi = PSI(id)

    '''
    Step2. Parse the SQL
    '''
    plan = parseSQL(SQL)
    '''
    Code here!
    '''

    '''
    Step3. Transfer the WHERE infix-subquery to postfix-subquery 
    '''
    opAST = infix2postfix(plan['WHERE'])

    '''
    Step4. Compute the WHERE subquery compute result
    '''
    compare_result = computePostfix(id, opAST, psi, header)
    compare_result = tf.reshape(compare_result, [100, 1])

    '''
    Step5. Reveal the result to check whether your code is correct
    '''
    cipher_result = rtt.SecureMul(psi, compare_result)

    sess = tf.compat.v1.Session()
    sess.run(tf.compat.v1.global_variables_initializer())
    a_and_c_can_get_plain = 0b101 
    print('From ID:{} plaintext greater result:\n'.format(id), sess.run(rtt.SecureReveal(cipher_result, a_and_c_can_get_plain)))

SQL = "SELECT ID FROM table WHERE DEPOSIT > 1000000"
header = ['ID', 'AGE', 'CARD', 'CREDIT', 'DEPOSIT']

p0 = multiprocessing.Process(target = execute, args = (0, SQL, header))
p1 = multiprocessing.Process(target = execute, args = (1, SQL, header))
p2 = multiprocessing.Process(target = execute, args = (2, SQL, header))

p0.daemon = True
p0.start()
p1.daemon = True
p1.start()
p2.daemon = True
p2.start()

p0.join()
p1.join()
p2.join()