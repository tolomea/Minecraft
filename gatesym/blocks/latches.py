from gatesym.gates import Nor, Not, Placeholder, block


@block
def gated_d_latch(data, clock):
    """ a basic latch that passes and latches the data while the clock is high """
    clock_ = Not(clock)  # todo invert our relationship with the clock so we don't need all these
    s_ = Nor(Not(data), clock_)
    r_ = Nor(s_, clock_)
    q_ = Placeholder(data.network)
    q = Nor(q_, r_)
    q_.replace(Nor(q, s_))

    # force it to init as 0
    q.network.write(q.index, False)
    return q


@block
def ms_d_flop(data, clock):
    """ a two stage latch that clocks data in on a positive edge and out on a negative edge """
    latch = gated_d_latch(data, clock)
    return gated_d_latch(latch, Not(clock))


@block
def register(data, clock):
    """ a bank of ms_d_flops that share a clock line """
    res = []
    for i in data:
        res.append(ms_d_flop(i, clock))
    return res
