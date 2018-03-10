import random

from gatesym import core, gates, test_utils
from gatesym.blocks import latches


def test_gated_d_latch():
    network = core.Network()
    clock = gates.Switch(network)
    data = gates.Switch(network)
    latch, latch_ = latches.gated_d_latch(gates.Not(data), gates.Not(clock))
    network.drain()
    assert not latch.read()
    assert latch_.read()

    data.write(True)
    network.drain()
    assert not latch.read()
    assert latch_.read()

    clock.write(True)
    network.drain()
    assert latch.read()
    assert not latch_.read()

    data.write(False)
    network.drain()
    assert not latch.read()
    assert latch_.read()


def test_ms_d_flop_basic():
    network = core.Network()
    clock = gates.Switch(network)
    data = gates.Switch(network)
    flop, flop_ = latches.ms_d_flop(data, clock, gates.Not(clock))
    network.drain()
    assert not flop.read()

    # clock a 1 through
    data.write(True)
    network.drain()
    assert not flop.read()
    assert flop_.read()
    clock.write(True)
    network.drain()
    assert not flop.read()
    assert flop_.read()
    clock.write(False)
    network.drain()
    assert flop.read()
    assert not flop_.read()

    # and back to 0
    data.write(False)
    network.drain()
    assert flop.read()
    assert not flop_.read()
    clock.write(True)
    network.drain()
    assert flop.read()
    assert not flop_.read()
    clock.write(False)
    network.drain()
    assert not flop.read()
    assert flop_.read()


def test_ms_d_flop_timing():
    network = core.Network()
    clock = gates.Switch(network)
    data = gates.Switch(network)
    flop, flop_ = latches.ms_d_flop(data, clock, gates.Not(clock))
    network.drain()
    assert not flop.read()

    # clock a 1 through
    data.write(True)
    network.drain()
    assert not flop.read()  # data has no impact
    assert flop_.read()
    clock.write(True)
    network.drain()
    assert not flop.read()  # clock high data in
    assert flop_.read()
    clock.write(False)
    data.write(False)
    network.drain()
    assert flop.read()  # clock low stored data out
    assert not flop_.read()

    # and back to 0
    data.write(False)
    network.drain()
    assert flop.read()  # data has no impact
    assert not flop_.read()
    clock.write(True)
    network.drain()
    assert flop.read()  # clock high data in
    assert not flop_.read()
    clock.write(False)
    data.write(True)
    network.drain()
    assert not flop.read()  # clock low stored data out
    assert flop_.read()


def test_register():
    network = core.Network()
    clock = gates.Switch(network)
    data = test_utils.BinaryIn(network, 8)
    register = latches.register(data, clock)
    res = test_utils.BinaryOut(register)
    network.drain()
    assert res.read() == 0

    # clock a value through
    v1 = random.randrange(256)
    data.write(v1)
    network.drain()
    assert res.read() == 0
    clock.write(True)
    network.drain()
    assert res.read() == 0
    clock.write(False)
    network.drain()
    assert res.read() == v1

    # and a different value
    v2 = random.randrange(256)
    data.write(v2)
    network.drain()
    assert res.read() == v1
    clock.write(True)
    network.drain()
    assert res.read() == v1
    clock.write(False)
    network.drain()
    assert res.read() == v2
