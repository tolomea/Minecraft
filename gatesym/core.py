""" the actual (and entire) simulation implementation """

import collections

TIE, SWITCH, NOR = ['tie', 'switch', 'nor']


class _Gate(collections.namedtuple('_Gate', 'type_, inputs, outputs, cookies')):
    # internal gate format

    def __new__(cls, type_, cookies):
        return super().__new__(cls, type_, set(), set(), cookies)


class Network(object):

    def __init__(self):
        self._gates = []
        self._values = []
        self._queue = set()
        self._watches = []
        self._log = []

    def add_gate(self, type_, cookie=None):
        assert type_ in [TIE, SWITCH, NOR]
        index = len(self._gates)
        self._gates.append(_Gate(type_, {cookie}))
        self._values.append(type_ == NOR)
        return index

    def remove_gate(self, index):
        raise NotImplemented

    def add_link(self, source_index, destination_index):
        dest_gate = self._gates[destination_index]
        assert dest_gate.type_ not in {TIE, SWITCH}
        self._gates[source_index].outputs.add(destination_index)
        dest_gate.inputs.add(source_index)
        self._queue.add(destination_index)

    def remove_link(self, source_index, destination_index):
        raise NotImplemented

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
