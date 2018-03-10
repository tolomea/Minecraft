from gatesym.gates import And, Nor, Or, block
from gatesym.utils import invert


@block
def address_matches(address_value, address_lines, address_lines_):
    """ does the address_value (an integer) match the current value of the address lines """
    assert 2**len(address_lines) > address_value
    matches = []
    for i, (line, line_) in enumerate(zip(address_lines, address_lines_)):
        if address_value & 2**i:
            matches.append(line_)
        else:
            matches.append(line)
    return Nor(*matches)


@block
def address_decode(address, limit=None):
    """ break an address out into individual enable lines """
    if limit is None:
        limit = 2**len(address)
    address_ = invert(address)
    return [address_matches(i, address, address_) for i in range(limit)]


@block
def bit_switch(control_lines, *data):
    """ select the bit(s) from the data that match the enabled control line(s) (generally only 1) """
    assert len(control_lines) >= len(data)
    return Or(*[And(c, d) for c, d in zip(control_lines, data)])


@block
def bit_mux(address, *data):
    """ select a single bit from the block of bits based on the address """
    assert 2**len(address) >= len(data)
    control_lines = address_decode(address)
    return bit_switch(control_lines, *data)


@block
def word_switch(control_lines, *data):
    """ select the words(s) from the data that match the enabled control line(s) (generally only 1) """
    assert len(control_lines) >= len(data)
    word_size = len(data[0])
    assert all(len(d) == word_size for d in data)

    output = []
    for data_lines in zip(*data):
        output.append(bit_switch(control_lines, *data_lines))
    return output


@block
def word_mux(address, *data):
    """ select a single word from the block of words based on the address """
    control_lines = address_decode(address)
    return word_switch(control_lines, *data)
