from gatesym.gates import Nor, Not, Placeholder, block
from gatesym.utils import invert


@block
def gated_d_latch(data_, clock_):
    """ a basic latch that passes and latches the data while the clock is high """
    s_ = Nor(data_, clock_)
    r_ = Nor(s_, clock_)
    q_ = Placeholder(data_.network)
    q = Nor(q_, r_)
    q_.replace(Nor(q, s_))

    # force it to init as 0
    q.network.write(q.index, False)
    return q, q_


@block
def ms_d_flop(data_, clock, clock_):
    """ a two stage latch that clocks data in on a positive edge and out on a negative edge """
    latch, latch_ = gated_d_latch(data_, clock_)
    res, res_ = gated_d_latch(latch_, clock)
    return res, res_


@block
def register(data, clock, negate_in=False, negate_out=False):
    """ a bank of ms_d_flops that share a clock line """
    clock_ = Not(clock)
    if not negate_in:
        data_ = invert(data)
    else:
        data_ = data
    res = []
    for i_ in data_:
        d, d_ = ms_d_flop(i_, clock, clock_)
        if negate_out:
            res.append(d_)
        else:
            res.append(d)
    return res
