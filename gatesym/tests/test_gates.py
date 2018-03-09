from gatesym import core, gates
from gatesym.blocks import adders


def test_find():
    n = core.Network()
    a = gates.Switch(n)
    b = gates.Switch(n)
    c = gates.Switch(n)
    r, co = adders.full_adder(a, b, c)
    assert a.find('full_adder(0.half_adder(0.not.nor.1).nor.not.1)') is co
    assert a.find('full_adder(0.half_adder(0.not:1.nor.nor.not.0).half_adder(0.not:2.not.nor.nor.not.0).0)') is r


def test_short_cut_find():
    n = core.Network()
    a = gates.Switch(n)
    b = gates.Switch(n)
    c = gates.Switch(n)
    r, co = adders.full_adder(a, b, c)
    assert a.find('full_adder(0.1)') is co
    assert a.find('full_adder(0.0)') is r


def test_list():
    n = core.Network()
    a = gates.Switch(n)
    b = gates.Switch(n)
    c = gates.Switch(n)
    r, co = adders.full_adder(a, b, c)
    assert a.list('') == ['full_adder(0']
    assert a.list('full_adder(0') == ['0)', '1)', 'half_adder(0']
    assert a.list('full_adder(0.half_adder(0') == ['0)', '1)', 'not', 'not', 'not']
    assert a.list('full_adder(0.half_adder(0.not') == ['nor']
    assert a.list('full_adder(0.half_adder(0.not.nor') == ['1)']
    assert a.list('full_adder(0.half_adder(0.not.nor.1)') == ['nor']
    assert a.list('full_adder(0.half_adder(0.not.nor.1).nor') == ['not']
    assert a.list('full_adder(0.half_adder(0.not.nor.1).nor.not') == ['1)']
    assert a.list('full_adder(0.half_adder(0.not.nor.1).nor.not.1)') == []
