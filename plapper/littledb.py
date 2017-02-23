# -*- coding: utf-8 -*-
"""An easy to use key-value storage based on sqlite3."""

from __future__ import absolute_import, print_function

import collections
import datetime
import sqlite3
import threading

try:
    import cPickle as pickle
except ImportError:
    import pickle

try:
    import umsgpack
except ImportError:
    umsgpack = None

import jsonify


SQL_CREATE_TABLE = """\
CREATE TABLE IF NOT EXISTS "{}" (
    key TEXT PRIMARY KEY,
    content BLOB
) WITHOUT ROWID
"""
SQL_INSERT_DOCUMENT = 'INSERT OR REPLACE INTO "{}" VALUES (?, ?)'
SQL_SELECT_DOCUMENT = 'SELECT content FROM "{}" WHERE key = ?'
SQL_SELECT_KEYS = 'SELECT key FROM "{}"'


class RegistrableMeta(type):
    """Meta-class for Adapter class and sub-classes.

    Holds a registry of all sub-classes.
    """
    registry = collections.OrderedDict()

    def __init__(cls, clsname, bases, classdict):
        cls.registry[cls.format] = cls

    def from_format(cls, format):
        return cls.registry.get(format)


Adapter = RegistrableMeta('Adapter', (object,), {'format': None})


class PickleAdapter(Adapter):
    format = 'pickle'

    @staticmethod
    def from_dict(data):
        return pickle.dumps(data)

    @staticmethod
    def to_dict(s):
        return pickle.loads(s)


class JsonAdapter(Adapter):
    format = 'json'

    @staticmethod
    def from_dict(obj):
        return jsonify.dumps(obj).encode('utf-8')

    @staticmethod
    def to_dict(data):
        return jsonify.loads(data.decode('utf-8'))


if umsgpack:
    class MsgPackAdapter(Adapter):
        date_fmt = "%Y%m%d"
        datetime_fmt = "%Y%m%dT%H:%M:%S.%f"
        format = 'msgpack'

        def from_date(self, date):
            return umsgpack.Ext(0x10, date.isoformat().encode())

        def to_date(self, ext):
            return datetime.date(*(int(v) for v in ext.data.split(b'-')))

        def from_datetime(self, dt):
            return umsgpack.Ext(0x20, dt.strftime(self.datetime_fmt).encode())

        def to_datetime(self, ext):
            return datetime.datetime.strptime(ext.data.decode('ascii'), self.datetime_fmt)

        def from_dict(self, obj):
            return umsgpack.packb(obj, ext_handlers={
                datetime.date: self.from_date,
                datetime.datetime: self.from_datetime
            })

        def to_dict(self, data):
            return umsgpack.unpackb(data, ext_handlers={
                0x10: self.to_date,
                0x20: self.to_datetime
            })


class Collection(object):
    def __init__(self, db, name, format, adapter):
        self.db = db
        self.name = name
        self.format = format
        self._from_dict = adapter.from_dict
        self._to_dict = adapter.to_dict
        self.SQL_INSERT_DOCUMENT = SQL_INSERT_DOCUMENT.format(name)
        self.SQL_SELECT_DOCUMENT = SQL_SELECT_DOCUMENT.format(name)
        self.SQL_SELECT_KEYS = SQL_SELECT_KEYS.format(name)

    def get(self, key):
        con = self.db.connection()
        cur = con.execute(self.SQL_SELECT_DOCUMENT, (key,))
        try:
            val = cur.fetchone()[0]
        except (IndexError, TypeError):
            raise KeyError(key)
        finally:
            cur.close()

        if isinstance(val, bytes):
            return self._to_dict(val)
        else:
            return val

    __getitem__ = get

    def set(self, key, data):
        con = self.db.connection()
        if isinstance(data, dict):
            data = self._from_dict(data)

        if con.in_transaction:
            con.execute(self.SQL_INSERT_DOCUMENT, (key, data))
        else:
            with con:
                con.execute(self.SQL_INSERT_DOCUMENT, (key, data))

    __setitem__ = set

    def keys(self):
        return (r[0] for r in self.db.connection().execute(self.SQL_SELECT_KEYS))

    def begin(self):
        self.db.begin_transaction()

    def commit(self):
        self.db.connection().commit()


class LittleDB(object):
    def __init__(self, filename):
        self.filename = filename
        self._local = threading.local()
        self._adapters = {}

    def connection(self):
        try:
            con = getattr(self._local, 'connection')
            con.total_changes  # test if connection is stil valid (open)
        except (AttributeError, sqlite3.ProgrammingError):
            con = self._local.connection = sqlite3.connect(self.filename)
        return con

    def begin(self):
        self.connection().execute('BEGIN TRANSACTION')

    def commit(self):
        self.connection().commit()

    def close(self):
        con = getattr(self._local, 'connection', None)
        if con:
            con.close()

    def get_collection(self, name, format='json'):
        if format not in self._adapters:
            cls = Adapter.from_format(format)
            if not cls:
                raise NotImplementedError("No adapter found for format '{}'.".format(format))

            self._adapters[format] = adapter = cls()

        with self.connection() as con:
            con.execute(SQL_CREATE_TABLE.format(name))

        return Collection(self, name, format, adapter)


if __name__ == '__main__':
    document = dict(
        id=42,
        author='Joe Doe',
        text="My hovercraft is full of eels!",
        score=3.141,
        today=datetime.date.today(),
        timestamp=datetime.datetime.utcnow()
    )

    db = LittleDB(':memory:')
    coll = db.get_collection('documents', format='pickle')

    # using the Collection instance methods
    coll.set('doc1', document)
    print("doc1:", coll.get('doc1'))

    # using the Collection instance as a dict
    try:
        print(coll['doc2'])
    except KeyError:
        print("Document 'doc2' does not exist. Creating it.")

    coll['doc2'] = dict(spamm='eggs')
    print("doc2:", coll['doc2'])
    coll['doc1'] = dict(ham='bacon')
    print("doc1:", coll['doc1'])
    print("Keys:", list(coll.keys()))
    db.close()
