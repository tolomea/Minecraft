""" the actual (and entire) simulation implementation """

import collections

TIE, SWITCH, NOR = ['tie', 'switch', 'nor']


class _Gate(collections.namedtuple('_Gate', 'type_, inputs, outputs, cookies')):
    # internal gate format

    def __new__(cls, type_, cookies):
        return super().__new__(cls, type_, list(), list(), cookies)


class Network(object):

    def __init__(self):
        self._gates = []
        self._values = []
        self._queue = set()
        self._watches = []
        self._log = []
        self._free_list = []

    def add_gate(self, type_, cookie=None):
        assert type_ in [TIE, SWITCH, NOR]
        gate = _Gate(type_, {cookie})
        if self._free_list:
            index = self._free_list.pop()
            self._gates[index] = gate
        else:
            index = len(self._gates)
            self._gates.append(gate)
        self._values.append(type_ == NOR)
        return index

    def remove_gate(self, index):
        assert not self._gates[index].outputs
        assert not self._gates[index].inputs
        self._gates[index] = None
        self._free_list.append(index)

    def add_link(self, source_index, destination_index):
        print("add link", source_index, destination_index)
        dest_gate = self._gates[destination_index]
        source_gate = self._gates[source_index]
        assert dest_gate.type_ not in {TIE, SWITCH}
        source_gate.outputs.append(destination_index)
        dest_gate.inputs.append(source_index)
        self._queue.add(destination_index)

    def remove_link(self, source_index, destination_index):
        print("remove link", source_index, destination_index)
        self._gates[source_index].outputs.remove(destination_index)
        self._gates[destination_index].inputs.remove(source_index)
        self._queue.add(destination_index)

    def read(self, gate_index):
        return self._values[gate_index]

    def write(self, gate_index, value):
        if self._values[gate_index] != value:
            self._values[gate_index] = value
            self._queue.update(self._gates[gate_index].outputs)

    def step(self):
        queue = set()
        values = self._values  # localize references for speed
        gates = self._gates  # localize references for speed

        for index in self._queue:
            gate = gates[index]

            if gate:
                if gate.type_ == NOR:
                    res = not(any(values[i] for i in gate.inputs))
                else:
                    assert False, gate.type_

                if values[index] != res:
                    values[index] = res
                    queue.update(gate.outputs)

        self._queue = queue
        return bool(queue)

    def drain(self):
        count = 0
        if self._queue:
            count += 1
            while self.step():
                count += 1
        return count

    def dump(self):
        for i, (v, g) in enumerate(zip(self._values, self._gates)):
            print(i, v, g)

    def record_log(self):
        new_log = []
        for name, index, negate in self._watches:
            if negate:
                new_log.append(int(self.read(index)))
            else:
                new_log.append(int(not self.read(index)))
        if not self._log or new_log != self._log[-1]:
            self._log.append(new_log)

    def watch(self, gate_index, name, negate):
        assert not self._log
        self._watches.append((name, gate_index, negate))

    def print_log(self):
        self.record_log()
        if self._watches:
            name_len = max(len(name) for name, _, _ in self._watches)
            for (name, _, _), row in zip(self._watches, zip(*self._log)):
                entry = ''.join(str(i) for i in row)
                print(f'{name:{name_len}} {entry}')
            print()

    def get_stats(self):
        gates_by_type = collections.defaultdict(int)
        gates_by_type_and_inputs = collections.defaultdict(int)
        for gate in self._gates:
            if gate:
                gates_by_type[gate.type_] += 1
                gates_by_type_and_inputs[gate.type_, len(gate.inputs)] += 1

        return {
            'size': self.get_size(),
            'gates_by_type': gates_by_type,
            'gates_by_type_and_inputs': gates_by_type_and_inputs,
        }

    def get_size(self):
        """ total count of all gates """
        return len(self._gates)

    def dump_values(self, prefix, nor_low, nor_high, other_low, other_high):
        res = prefix
        for gate, value in zip(self._gates, self._values):
            if gate and gate.type_ == NOR:
                res.extend(nor_high if value else nor_low)
            else:
                res.extend(other_high if value else other_low)
        return res
