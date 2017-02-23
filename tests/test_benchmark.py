#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import random
import sys
import tempfile
import uuid

import dbtest


try:
    range = xrange
except NameError:
    pass


def main(args):
    N = 1000000
    testdir = tempfile.mkdtemp()
    print('Testing with N =', N)
    print('------------------------------------\n')
    print('Test database base directory:', testdir)
    print()

    print("Generating %i test documents..." % N)
    documents = [dict(id=i, value=random.random(), content=uuid.uuid4().hex)
                 for i in range(N)]
    print()

    try:
        for clsname in dbtest.__all__:
            print(clsname)
            print('~' * len(clsname), end='\n\n')

            test = getattr(dbtest, clsname)(testdir)
            if int in test.value_types:
                print("Timing WRITING with int values...\n")
                print('Writes: %.5f sec.\n' % test.test_writes(range(N)))
                print("Timing READING with int values...\n")
                print('Reads:  %.5f sec.\n' % test.test_reads(range(N)))
                print()

            if dict in test.value_types:
                print("Timing WRITING with dict values...\n")
                print('Writes: %.5f sec.\n' % test.test_writes(documents))
                print("Timing READING with dict values...\n")
                print('Reads:  %.5f sec.\n' % test.test_reads(range(N), valtype=dict))
                print()

            test.close()

    finally:
        if '-c' in args:
            import shutil
            shutil.rmtree(testdir)

main(sys.argv[:1])
