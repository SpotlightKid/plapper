#!/usr/bin/env python

import os
import time

# The databases!

# standard library
try:
    import dbm
except ImportError:
    try:
        from dbm import gnu as dbm
    except ImportError:
        import anydbm as dbm

import sqlite3

# third-party
import redis

# our own
import littledb


__all__ = (
    'DBMTest',
    'SqliteTest',
    'RedisTest',
    'LittleDBPickleTest',
    'LittleDBJsonTest',
    'LittleDBMsgpackTest',
)

def timed(fn):
    def inner(*args, **kw):
        s = time.time()
        fn(*args, **kw)
        return time.time() - s
    return inner


class DBTest(object):
    value_types = (int,)

    def __init__(self, workdir):
        if self.filename:
            self.path = os.path.join(workdir, self.filename)
            if os.path.exists(self.path):
                if os.path.isdir(self.path):
                    os.removedirs(self.path)
                else:
                    os.unlink(self.path)
        self._db = self.get_db()

    def close(self):
        try:
            self._db.close()
        except AttributeError:
            pass

    @timed
    def test_writes(self, iter):
        self.begin()
        for i, v in enumerate(iter):
            self.write(str(i), v)
        self.commit()

    @timed
    def test_reads(self, iter, valtype=int):
        for i in iter:
            v = self.read(str(i))
        assert isinstance(v, valtype)

    def write(self, k, v):
        self._db[k] = v

    def read(self, k):
        return self._db[k]

    def begin(self):
        pass

    def commit(self):
        pass


class DBMTest(DBTest):
    filename = 'dbm.db'

    def get_db(self):
        return dbm.open(self.path, 'c')

    def write(self, k, v):
        self._db[k] = str(v)

    def read(self, k):
        return int(self._db[k])


class LittleDBTest(DBTest):
    value_types = (int, dict)

    def __init__(self, *args, **kw):
        self.filename = 'littledb-%s.db' % self.format
        super(LittleDBTest, self).__init__(*args, **kw)

    def get_db(self):
        self._conn = littledb.LittleDB(self.path)
        coll = self._conn.get_collection('test', self.format)
        return coll

    def close(self):
        self._conn.close()

    def begin(self):
        self._conn.begin()

    def commit(self):
        self._conn.commit()


class LittleDBPickleTest(LittleDBTest):
    format = 'pickle'


class LittleDBJsonTest(LittleDBTest):
    format = 'json'


class LittleDBMsgpackTest(LittleDBTest):
    format = 'msgpack'


class RedisTest(DBTest):
    filename = None

    def get_db(self):
        db = redis.Redis(db=15)
        db.flushdb()
        return db

    def read(self, k):
        return int(self._db[k])


class SqliteTest(DBTest):
    filename = 'sqlite.db'

    def get_db(self):
        db = sqlite3.connect(self.path)
        db.execute("""\
            CREATE TABLE data (
                key VARCHAR(255) PRIMARY KEY NOT NULL,
                value INT NOT NULL
            );
        """)
        db.execute('BEGIN TRANSACTION')
        return db

    def write(self, k, v):
        self._db.execute("INSERT INTO data (key, value) VALUES (?, ?)", (k, v))

    def read(self, k):
        cur = self._db.execute("SELECT value FROM data WHERE key=?", (k,))
        val = cur.fetchone()[0]
        cur.close()
        return val

    def commit(self):
        self._db.commit()

