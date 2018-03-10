from gatesym.gates import Nor, Not, Placeholder, block


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
def ms_d_flop(data, clock, clock_):
    """ a two stage latch that clocks data in on a positive edge and out on a negative edge """
    latch, latch_ = gated_d_latch(Not(data), clock_)
    res, res_ = gated_d_latch(latch_, clock)
    return res, res_


@block
def register(data, clock, negate=False):
    """ a bank of ms_d_flops that share a clock line """
    res = []
    for i in data:
        d, d_ = ms_d_flop(i, clock, Not(clock))
        if negate:
            res.append(d_)
        else:
            res.append(d)
    return res
