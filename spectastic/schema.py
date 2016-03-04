# -*- coding: utf-8 -*-
from copy import deepcopy


def resolve_ref(spec, ref):
    """
    Resolves a local ref in the form of ``#/definitions/dog`` or
    ``#/parameters/cat``.
    """
    kind, name = ref.split('/')[1:]
    return spec[kind][name]


def _resolve_current(spec, current):
    """
    Resolves the current local schema (a reference to a value within spec) to
    it's corresponding definition, replacing '$refs' with real references.
    """
    if isinstance(current, dict):
        if '$ref' in current:
            resolved = resolve_ref(spec, current['$ref'])
            current.clear()
            current.update(resolved)
        else:
            for key, value in current.iteritems():
                _resolve_current(spec, value)
    elif isinstance(current, list):
        for key, value in enumerate(current):
            _resolve_current(spec, value)
    elif isinstance(current, tuple):
        raise ValueError('Tuples make unhappy')


def resolve_all(spec):
    """
    Recursively resolve all refs to appropriate references within the spec
    dictionary.
    """
    _resolve_current(spec, spec)
    return spec


class Schema(dict):
    def __init__(self, spec_dict):
        spec_dict = resolve_all(deepcopy(spec_dict))
        self.update(spec_dict)
        super(Schema, self).__init__()
