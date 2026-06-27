#!/usr/bin/env python3

def parseSQL(SQL):
    '''
    Step1. Split the SQL into a list
    This module split the SQL statement into key-value
    For example: "SELECT id FROM tableA WHERE loan>100000" will parse and split as:
        [["SELECT": id],
         ["FROM": tableA],
         ["WHERE": loan>100000]]
         
    Code here!
    '''
    

    '''
    Step2. substract the token.value into operator buffer

    For example: if the select condition is "loan>50000 AND loan<1000000", this condition will parse as:
        ['loan>50000', 'AND', 'loan<1000000']
    
    Above are three subconditions, and we'll substract the subconditions as:
        [['loan', '>', '50000'], ['AND'], ['loan', '<', '1000000']]
    
    Note: this module just for test, only support single table SELECT SQL
    
    Code here!
    '''