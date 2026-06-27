#!/usr/bin/env python3

from SQLparse import *
import os
import numpy as mp
import sys
import tensorflow as tf

def infix2postfix(exp):
    '''
    This function will transfer the infix expression to postfix expression

    For example: 
    ['deposit', 'op5', '20000', 'AND', '(', 'credit', 'op3', '3', 'OR', 'credit', 'op4', '7', ')']
    |   |   |   |   |
    After transform:
    ['deposit', '20000', 'credit', '3', 'op3', 'credit', '7', 'op4', 'op5', 'AND']
    '''
    
    '''
    Code here!
    '''
