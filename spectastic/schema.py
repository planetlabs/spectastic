# -*- coding: utf-8 -*-
from copy import deepcopy


def resolve_ref(schema_dict, ref):
    """
    Resolves a local ref in the form of ``#/definitions/dog`` or
    ``#/parameters/cat``.

    :param dict schema_dict: A raw, json-decoded schema.
    """
    kind, name = ref.split('/')[1:]
    return schema_dict[kind][name]


def _resolve_current(schema_dict, current):
    """
    Resolves the current local schema (a reference to a location within the
    schema) to it's corresponding definition, replacing '$refs' with real
    references.

    :param dict schema_dict: A raw, json-decoded schema.
    """
    if isinstance(current, dict):
        if '$ref' in current:
            resolved = resolve_ref(schema_dict, current['$ref'])
            current.clear()
            current.update(resolved)
        else:
            for key, value in current.iteritems():
                _resolve_current(schema_dict, value)
    elif isinstance(current, list):
        for key, value in enumerate(current):
            _resolve_current(schema_dict, value)
    elif isinstance(current, tuple):
        raise ValueError('Tuples make unhappy')


def resolve_all(schema_dict):
    """
    Recursively resolve all refs to appropriate references within the spec
    dictionary.

    :param dict schema_dict: A raw, json-decoded schema.
    """
    _resolve_current(schema_dict, schema_dict)
    return schema_dict


class Schema(dict):
    """
    Simple wrapper around Swagger / Open API schema's. At some 'semblance' of
    type safety. Mostly used to resolve all references with the provided schema
    to make spectastic's job easier.
    """
    def __init__(self, schema_dict):
        schema_dict = resolve_all(deepcopy(schema_dict))
        self.update(schema_dict)
        super(Schema, self).__init__()
