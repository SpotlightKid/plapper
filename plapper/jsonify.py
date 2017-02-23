"""JSON en-/decoder with support for datetime/date and custom object instances.

Encodes Python class instances which have a ``__json__`` method returning a
JSON-encodable object of the instance state. Provides the ``Jsonable`` class,
which can be used as a mix-in to add an implementation of the ``__json__``
method that works for many objects.

Object serialization and de-serialization can be further customized by using
the `pickle API`_ described in the standard library reference, in particular by
implementing any of the special methods ``__getstate___``, ``__setstate__`` and
``__getnewargs__``.

See the documentation of the ``JsonifyEncoder`` and ``JsonifyDecopder`` classes
and the example code at the end of the module for usage information.


.. _pickle api:
    https://docs.python.org/2/library/pickle.html#pickling-class-instances

"""


__all__ = ('Jsonable', 'JsonifyDecoder', 'JsonifyEncoder', 'dumps', 'loads')

import datetime
import inspect
import json


DATETIME_FMT = "%Y%m%dT%H:%M:%S.%f"
DATE_FMT = "%Y%m%d"


class Jsonable(object):
    """Mixin class providing JSON serialization support for class instances."""

    def __json__(self):
        """Return JSON-serializable representation of object state.

        Returns dict of attribute name/value pairs with the class name of the
        instance added under the key ``'__class__'``.

        If the object has a ``__dir__`` method, it is expected to return an
        iterable of the names of the attributes, which make up the returned
        state dict. Otherwise the list of attributes is obtained by taking
        the value of the ``__dict__`` attribute of the instance and filtering
        out any attributes whose name starts with two underscores.

        """
        attrlister = getattr(self, '__dir__', None)
        if callable(attrlister):
            attr = {a: getattr(self, a) for a in attrlister()
                    if not a.startswith('__') and not inspect.ismethod(getattr(self, a))}
        else:
            attr = {a:v for a,v in self.__dict__.items()
                    if not a.startswith('__')}

        attr['__class__'] = self.__class__.__name__
        return attr


class JsonifyEncoder(json.JSONEncoder):
    """Subclass of json.JSONEncoder, which supports additional types.

    This encoder supports serializing custom class and datetime/date instances
    in combination with the ``Jsonable`` mixin.

    """

    def default(self, obj):
        for method in ('__json__', '__getstate__'):
            jsonify = getattr(obj, method, None)
            if callable(jsonify):
                return jsonify()

        if isinstance(obj, datetime.datetime):
            return {
                '__class__': '_datetime',
                '__newargs__': [
                    obj.year,
                    obj.month,
                    obj.day,
                    obj.hour,
                    obj.minute,
                    obj.second,
                    obj.microsecond
                ]
            }
        elif isinstance(obj, datetime.date):
            return {
                '__class__': '_date',
                '__newargs__': [
                    obj.year,
                    obj.month,
                    obj.day
                ]
            }
        else:
            return super(JsonifyEncoder, self).default(obj)


class JsonifyDecoder(json.JSONDecoder):
    def __init__(self, namespace=None, **kw):
        kw.setdefault('object_hook', self.decode_object)
        super(JsonifyDecoder, self).__init__(**kw)
        self._namespace = namespace or {}
        self._namespace.setdefault('_date', datetime.date)
        self._namespace.setdefault('_datetime', datetime.datetime)

    def decode_object(self, obj, namespace=None):
        """Decode dict or list resulting from decoded JSON object notation."""
        if isinstance(obj, list):
            pairs = enumerate(obj)
        elif isinstance(obj, dict):
            pairs = obj.items()

        result = []
        for key, val in pairs:
            if isinstance(val, (dict, list)):
                val = self.decode_object(val, namespace)

            result.append((key, val))

        if isinstance(obj, list):
            return [x[1] for x in result]
        elif isinstance(obj, dict):
            result = dict(result)
            clsname = result.pop('__class__', None)

            if clsname:
                try:
                    cls = getattr(self._namespace, clsname)
                except AttributeError:
                    cls = self._namespace.get(clsname)

                if cls is None:
                    raise NameError("name '%s' not found in given namespace." %
                                    clsname)

                inst = cls.__new__(cls, *result.pop('__newargs__', ()))

                try:
                    getattr(inst, '__setstate__')(result)
                except AttributeError:
                    for k in result:
                        if not k.startswith('__'):
                            setattr(inst, k, result[k])

                return inst
            else:
                return result


def dumps(obj, **kw):
    """Serialize obj to a JSON formatted str with support for class instances.

    Keyword arguments are passed to ``json.dumps``, which in turn passes any
    keyword arguments it doesn't recognize to the init method of the JSON
    encoder class, which is set to ``JsonifyEncoder`` by default.

    """
    kw.setdefault('cls', JsonifyEncoder)
    return json.dumps(obj, **kw)


def loads(s, namespace=None, **kw):
    """Deserialize string to a Python object with support for class instances.

    *namespace* is a dict-like or module object, which is used to resolve class
    names of JSON-ified class instances. By default the global *module*
    namespace is used, which probably isn't what you want. Normally you would
    pass something like the return value of ``globals()`` or ``locals()``.

    The remaining keyword arguments are passed to ``json.loads``, which in turn
    passes any keyword arguments it doesn't recognize to the init method of
    the JSON decoder class, which is set to ``JsonifyDecoder`` by default.

    """
    if namespace is None:
        namespace = globals()

    kw.setdefault('cls', JsonifyDecoder)
    kw['namespace'] = namespace
    return json.loads(s, **kw)


if __name__ == '__main__':
    class Bunch(Jsonable):
        def __init__(self, **kw):
            self.__dict__.update(kw)

        def test(self):
            pass

        def __repr__(self):
            return "<Bunch %r>" % (self.__dict__,)

    mytimestamp = datetime.datetime.utcnow()
    mydate = datetime.date.today()
    data = dict(
        foo=42,
        array=[mytimestamp, mydate],
        date=mydate,
        timestamp=mytimestamp,
        instance=Bunch(
            spamm='eggs',
            ham=23,
            timestamp3=mytimestamp
        ),
        struct=dict(
            date2=mydate,
            timestamp2=mytimestamp
        )
    )

    print("Python input:\n")
    print(repr(data))
    jsonstring = dumps(data)
    print("\nJSON output:\n")
    print(jsonstring)
    print("\nPython from JSON input:\n")
    print(repr(loads(jsonstring)))
