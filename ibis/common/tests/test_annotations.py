import inspect

import pytest
from toolz import identity

from ibis.common.annotations import Argument, Attribute, Parameter, Signature
from ibis.common.validators import instance_of, option

is_int = instance_of(int)


def test_default_argument():
    annotation = Argument.default(validator=int, default=3)
    assert annotation.validate(1) == 1
    with pytest.raises(TypeError):
        annotation.validate(None)


@pytest.mark.parametrize(
    ('default', 'expected'),
    [(None, None), (0, 0), ('default', 'default'), (lambda: 3, 3)],
)
def test_optional_argument(default, expected):
    annotation = Argument.optional(default=default)
    assert annotation.validate(None) == expected


@pytest.mark.parametrize(
    ('argument', 'value', 'expected'),
    [
        (Argument.optional(identity, default=None), None, None),
        (Argument.optional(identity, default=None), 'three', 'three'),
        (Argument.optional(identity, default=1), None, 1),
        (Argument.optional(identity, default=lambda: 8), 'cat', 'cat'),
        (Argument.optional(identity, default=lambda: 8), None, 8),
        (Argument.optional(int, default=11), None, 11),
        (Argument.optional(int, default=None), None, None),
        (Argument.optional(int, default=None), 18, 18),
        (Argument.optional(str, default=None), 'caracal', 'caracal'),
    ],
)
def test_valid_optional(argument, value, expected):
    assert argument.validate(value) == expected


@pytest.mark.parametrize(
    ('arg', 'value', 'expected'),
    [
        (Argument.optional(is_int, default=''), None, TypeError),
        (Argument.optional(is_int), 'lynx', TypeError),
    ],
)
def test_invalid_optional_argument(arg, value, expected):
    with pytest.raises(expected):
        arg(value)


def test_initialized():
    class Foo:
        a = 10

    field = Attribute.default(lambda self: self.a + 10)
    assert field == field

    assert field.initialize(Foo) == 20

    field2 = Attribute(validator=lambda x, this: str(x), default=lambda self: self.a)
    assert field != field2
    assert field2.initialize(Foo) == '10'


def test_parameter():
    def fn(x, this):
        return int(x) + this['other']

    annot = Argument.mandatory(fn)
    p = Parameter('test', annotation=annot)

    assert p.annotation is fn
    assert p.default is inspect.Parameter.empty
    assert p.validate('2', this={'other': 1}) == 3

    with pytest.raises(TypeError):
        p.validate({}, valid=inspect.Parameter.empty)

    ofn = Argument.optional(fn)
    op = Parameter('test', annotation=ofn)
    assert op.annotation == option(fn, default=None)
    assert op.default is None
    assert op.validate(None, this={'other': 1}) is None

    with pytest.raises(TypeError, match="annotation must be an instance of Argument"):
        Parameter("wrong", annotation=Attribute("a"))


def test_signature():
    def to_int(x, this):
        return int(x)

    def add_other(x, this):
        return int(x) + this['other']

    other = Parameter('other', annotation=Argument.mandatory(to_int))
    this = Parameter('this', annotation=Argument.mandatory(add_other))

    sig = Signature(parameters=[other, this])
    assert sig.validate(1, 2) == {'other': 1, 'this': 3}
    assert sig.validate(other=1, this=2) == {'other': 1, 'this': 3}
    assert sig.validate(this=2, other=1) == {'other': 1, 'this': 3}


def test_signature_unbind():
    def to_int(x, this):
        return int(x)

    def add_other(x, this):
        return int(x) + this['other']

    other = Parameter('other', annotation=Argument.mandatory(to_int))
    this = Parameter('this', annotation=Argument.mandatory(add_other))

    sig = Signature(parameters=[other, this])
    params = sig.validate(1, this=2)

    kwargs = sig.unbind(params)
    assert kwargs == {"other": 1, "this": 3}


def as_float(x, this):
    return float(x)


def as_tuple_of_floats(x, this):
    return tuple(float(i) for i in x)


a = Parameter('a', annotation=Argument.mandatory(validator=as_float))
b = Parameter('b', annotation=Argument.mandatory(validator=as_float))
c = Parameter('c', annotation=Argument.default(default=0, validator=as_float))
d = Parameter(
    'd', annotation=Argument.default(default=tuple(), validator=as_tuple_of_floats)
)
e = Parameter('e', annotation=Argument.optional(validator=as_float))
sig = Signature(parameters=[a, b, c, d, e])


@pytest.mark.parametrize('d', [(), (5, 6, 7)])
def test_signature_unbind_with_empty_variadic(d):
    params = sig.validate(1, 2, 3, d, e=4)
    assert params == {'a': 1.0, 'b': 2.0, 'c': 3.0, 'd': d, 'e': 4.0}

    kwargs = sig.unbind(params)
    assert kwargs == {'a': 1.0, 'b': 2.0, 'c': 3.0, 'd': d, 'e': 4.0}

    params_again = sig.validate(**kwargs)
    assert params_again == params
