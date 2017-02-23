#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import os
import pstats
import random
import sys
import time
import tempfile
import uuid

import dbtest

import cProfile as profile
#import profile
#profile.Profile.bias = 1.572363555836169e-06

try:
    range = xrange
except NameError:
    pass


N = 100000
testdir = tempfile.mkdtemp()

print('Testing with N =', N)
print('------------------------------------\n')
print('Test database base directory:', testdir)
print()

print("Generating %i test documents..." % N)
documents = [dict(id=i, value=random.random(), content=uuid.uuid4().hex)
             for i in range(N)]
print()

for clsname in ('LittleDBPickleTest', 'LittleDBJsonTest', 'LittleDBMsgpackTest'):
    print(clsname)
    print('~' * len(clsname), end='\n\n')
    test = getattr(dbtest, clsname)(testdir)

    print("Profiling WRITING dictionaries with simple types...\n")
    profile.run('test.test_writes(documents)', 'writestats')
    stats = pstats.Stats('writestats')
    stats.sort_stats('tottime')
    stats.print_stats()

    print("Profiling READING dictionaries with simple types...\n")
    profile.run('test.test_reads(range(N), valtype=dict)', 'readstats')
    stats = pstats.Stats('readstats')
    stats.sort_stats('tottime')
    stats.print_stats()

    test.close()
