import time
from abc import abstractmethod, ABC
from typing import Optional


class Value(ABC):
    @abstractmethod
    def set(self, value) -> int:
        raise NotImplementedError

    @property
    @abstractmethod
    def value(self) -> int:
        raise NotImplementedError


class Memory(list):
    instruction_names = {
        1: "КОП",
        2: "СЛОЖ",
        3: "ВЫЧ",
        4: "ВЫВ",
        5: "СТОП",
        6: "ПРЫГ",
        7: "ИНК",
        8: "ДЕК",
        9: "ЦЕЛ",
        10: "ПРЫГZ",
        11: "ПРЫГНЕZ",
        12: "ОТЛАДКА",
        13: "СРАВ",
        14: "ПРЫГS",
        15: "ПРЫГНЕS",
        16: "ЛОЖИ",
        17: "БЕРИ",
        18: "ЗВОНИ",
        19: "НАЗАД",
    }

    names = {
        "А": 0,
        "Б": 1,
        "В": 2,
        "Г": 3,
        "Д": 4,
        "Ф": 5,
        "АДР": 6,
        "ПАМ": 7,
        "СП": 8,
        "ПК": 9,
    }

    for int_inst, name in instruction_names.items():
        names[name] = int_inst

    @classmethod
    def get_instruction_name(cls, inst_code):
        return cls.instruction_names.get(inst_code, f"НЕИЗВ({inst_code})")

    def __init__(self, size: int = 100):
        super().__init__()
        for i in range(size):
            self.append(0)

    def __setitem__(self, key, arg):
        value = arg

        if isinstance(arg, str):
            value = self.names.get(arg.upper(), None)

        if value is None:
            value = int(arg)

        value = value & 0xFF
        list.__setitem__(self, key, value)

    def write_text(self, text: str, at: int = 0) -> None:
        for n, i in enumerate(text):
            self[at + n] = ord(i) & 0xFF

    def write_code(self, code: str, at: int = 0) -> None:
        n = at
        data = []
        labels = {}
        for inst in code.split('\n'):
            if ';' in inst:
                inst = inst[:inst.index(';')]
            values = inst.split(" ", maxsplit=1)
            if values[0].endswith(":"):
                labels[values[0][:-1]] = n
                continue
            if values[0].strip() == "" or values[0].startswith(";"):
                continue
            print(n, values[0], end=" ")
            data.append(values[0])
            n += 1
            if len(values) == 2:
                for i, arg in enumerate(values[1].split(",")):
                    if arg.startswith(":"):
                        data.append([arg[1:]])
                    else:
                        data.append(arg.strip())
                    print(arg, end="")
                    n += 1
            print()
        n = at
        for d in data:
            if isinstance(d, list):
                self[n] = labels[d[0]]
            else:
                self[n] = d
            n += 1
        print()


class Register(Value):
    def __init__(self):
        self._value = 0

    @property
    def value(self):
        return self._value

    def set(self, value):
        self._value = value & 0xFF

    def __repr__(self):
        return f"R({self.value})"


class StackPointer(Register):
    def __init__(self, initial_value=0xFF):
        super().__init__()
        self._value = initial_value

    def __repr__(self):
        return f"SP({self.value})"


class FlagRegister:
    ZERO = 1 << 0
    CARRY = 1 << 1
    SIGN = 1 << 2
    PARITY = 1 << 3
    OVERFLOW = 1 << 4

    def __init__(self):
        self._flags = 0

    def set_flag(self, flag: int) -> None:
        self._flags |= flag

    def clear_flag(self, flag: int) -> None:
        self._flags &= ~flag

    def is_flag_set(self, flag: int) -> bool:
        return (self._flags & flag) != 0

    def get_value(self) -> int:
        return self._flags

    def set_zero_flag(self, result: int) -> None:
        if (result & 0xFF) == 0:
            self.set_flag(FlagRegister.ZERO)
        else:
            self.clear_flag(FlagRegister.ZERO)

    def set_carry_flag(self, carry: bool) -> None:
        if carry:
            self.set_flag(FlagRegister.CARRY)
        else:
            self.clear_flag(FlagRegister.CARRY)

    def set_sign_flag(self, result: int) -> None:
        if (result & 0x80) != 0:
            self.set_flag(FlagRegister.SIGN)
        else:
            self.clear_flag(FlagRegister.SIGN)

    def set_overflow_flag(self, a: int, b: int, result: int, is_subtraction: bool = False) -> None:
        a_sign = (a & 0x80) != 0
        b_sign = (b & 0x80) != 0
        result_sign = (result & 0x80) != 0

        if is_subtraction:
            b_sign = not b_sign

        if a_sign == b_sign and a_sign != result_sign:
            self.set_flag(FlagRegister.OVERFLOW)
        else:
            self.clear_flag(FlagRegister.OVERFLOW)

    def set_parity_flag(self, result: int) -> None:
        if bin(result & 0xFF).count('1') % 2 == 0:
            self.set_flag(FlagRegister.PARITY)
        else:
            self.clear_flag(FlagRegister.PARITY)

    def __repr__(self):
        flags = []
        if self.is_flag_set(FlagRegister.ZERO):
            flags.append("Z")
        if self.is_flag_set(FlagRegister.CARRY):
            flags.append("C")
        if self.is_flag_set(FlagRegister.SIGN):
            flags.append("S")
        if self.is_flag_set(FlagRegister.PARITY):
            flags.append("P")
        if self.is_flag_set(FlagRegister.OVERFLOW):
            flags.append("O")
        return f"Flags({', '.join(flags)})"


class ProcessorStats:
    def __init__(self):
        self.instruction_counts = {}
        self.memory_accesses = 0
        self.register_accesses = 0
        self.stack_operations = 0
        self.jumps_taken = 0
        self.jumps_not_taken = 0
        self.function_calls = 0
        self.function_returns = 0
        self.arithmetic_operations = 0
        self.flag_changes = 0
        self.max_stack_depth = 0
        self.min_stack_depth = 0xFF
        self.start_time = 0
        self.execution_path = []

    def record_instruction(self, inst_code):
        self.instruction_counts[inst_code] = self.instruction_counts.get(inst_code, 0) + 1

    def record_memory_access(self):
        self.memory_accesses += 1

    def record_register_access(self):
        self.register_accesses += 1

    def record_stack_op(self, sp_value):
        self.stack_operations += 1
        if sp_value < self.min_stack_depth:
            self.min_stack_depth = sp_value
        if sp_value > self.max_stack_depth:
            self.max_stack_depth = sp_value

    def record_jump(self, taken):
        if taken:
            self.jumps_taken += 1
        else:
            self.jumps_not_taken += 1

    def start_execution(self):
        self.start_time = time.time()

    def get_execution_time(self):
        return time.time() - self.start_time

    def print_stats(self):
        print("═" * 60)
        print("СТАТИСТИКА ВЫПОЛНЕНИЯ ПРОЦЕССОРА")
        print("═" * 60)

        total_instructions = sum(self.instruction_counts.values())
        exec_time = self.get_execution_time()

        print(f"Время выполнения: {exec_time:.6f} сек")
        print(f"Общее количество инструкций: {total_instructions}")
        print(f"Производительность: {total_instructions / exec_time:.0f} инст/сек")
        print()

        print("СТАТИСТИКА ИНСТРУКЦИЙ:")
        print("-" * 40)
        for inst_code, count in sorted(self.instruction_counts.items()):
            inst_name = Memory.get_instruction_name(inst_code)
            percentage = (count / total_instructions) * 100
            print(f"{inst_name:12} {count:6d} раз ({percentage:5.1f}%)")
        print()

        print("ОПЕРАЦИИ:")
        print("-" * 40)
        print(f"Обращения к памяти:     {self.memory_accesses}")
        print(f"Обращения к регистрам:  {self.register_accesses}")
        print(f"Операции со стеком:     {self.stack_operations}")
        print(f"Арифметические операции: {self.arithmetic_operations}")
        print(f"Изменения флагов:       {self.flag_changes}")
        print()

        print("УПРАВЛЕНИЕ ПОТОКОМ:")
        print("-" * 40)
        print(f"Прыжки выполнены:       {self.jumps_taken}")
        print(f"Прыжки пропущены:       {self.jumps_not_taken}")
        total_jumps = self.jumps_taken + self.jumps_not_taken
        if total_jumps > 0:
            branch_prediction = (self.jumps_taken / total_jumps) * 100
            print(f"Эффективность прыжков:  {branch_prediction:.1f}%")
        print(f"Вызовов функций:        {self.function_calls}")
        print(f"Возвратов из функций:   {self.function_returns}")
        print()

        print("ИСПОЛЬЗОВАНИЕ СТЕКА:")
        print("-" * 40)
        stack_used = 0xFF - self.min_stack_depth
        print(f"Максимальная глубина:   {stack_used} байт")
        print(f"Диапазон SP: {self.min_stack_depth}-{self.max_stack_depth}")
        print()


class Processor:
    memory: Memory
    memory_pointer: int
    registers: list[Value]

    accumulator: Register
    flags: FlagRegister

    class MemoryProxy(Value):
        processor: "Processor"

        def __init__(self, _processor: "Processor"):
            self.processor = _processor

        @property
        def value(self):
            self.processor.stats.record_memory_access()
            return self.processor.memory[self.processor.addr]

        def set(self, value):
            self.processor.stats.record_memory_access()
            self.processor.memory[self.processor.addr] = value & 0xFF

        def __repr__(self):
            return f"Proxy({self.value})"

    class ProgramCounter(Value):
        def __init__(self, processor):
            self.processor = processor

        @property
        def value(self):
            return self.processor.memory_pointer

        def set(self, value):
            self.processor.memory_pointer = value & 0xFF

        def __repr__(self):
            return f"PC({self.value})"

    def __init__(self, _memory: Optional[Memory]):
        self.memory = _memory or Memory()
        self.memory_pointer = 0
        self.accumulator = Register()
        self.flags = FlagRegister()
        self.stack_pointer = StackPointer(0xFF)
        self.stats = ProcessorStats()
        self.registers = [
            self.accumulator,
            Register(),
            Register(),
            Register(),
            Register(),
            self.flags,
            Register(),
            Processor.MemoryProxy(self),
            self.stack_pointer,
            Processor.ProgramCounter(self)
        ]

    @property
    def current(self) -> int:
        return self.memory[self.memory_pointer]

    def get_next(self) -> int:
        self.memory_pointer += 1
        return self.current

    @property
    def addr(self) -> int:
        return self.registers[6].value

    def set_flags(self, result: int) -> int:
        result_8bit = result & 0xFF
        self.flags.set_zero_flag(result_8bit)
        self.flags.set_sign_flag(result_8bit)
        self.flags.set_parity_flag(result_8bit)
        return result_8bit

    def set_flags_with_carry(self, result: int) -> int:
        self.flags.set_carry_flag(result > 0xFF or result < 0)
        return self.set_flags(result)

    def set_flags_with_overflow(self, a: int, b: int, result: int, is_subtraction: bool = False) -> int:
        self.flags.set_overflow_flag(a, b, result, is_subtraction)
        return self.set_flags_with_carry(result)

    def exec(self, start: int = 0) -> None:
        self.stats.start_execution()
        self.memory_pointer = start
        while True:
            inst = self.current
            self.stats.record_instruction(inst)
            if inst == 9:
                target = self.get_next()
                self.stats.record_register_access()
                self.registers[target].set(self.get_next())
            elif inst == 1:
                self.stats.record_register_access()
                self.registers[self.get_next()].set(self.registers[self.get_next()].value)
            elif inst == 2:
                self.stats.arithmetic_operations += 1
                a = self.registers[self.get_next()]
                b = self.registers[self.get_next()]
                result = a.value + b.value
                a.set(self.set_flags_with_overflow(a.value, b.value, result))
            elif inst == 3:
                self.stats.arithmetic_operations += 1
                a = self.registers[self.get_next()]
                b = self.registers[self.get_next()]
                result = a.value - b.value
                a.set(self.set_flags_with_overflow(a.value, b.value, result, True))
            elif inst == 4:
                print(chr(self.registers[self.get_next()].value), end="")
            elif inst == 5:
                print("\n")
                self.stats.print_stats()
                print("ФИНАЛЬНОЕ СОСТОЯНИЕ РЕГИСТРОВ:")
                print("-" * 40)
                print(self.registers)
                return
            elif inst == 6:
                self.memory_pointer = self.get_next()
                continue
            elif inst == 7:
                self.stats.arithmetic_operations += 1
                target = self.registers[self.get_next()]
                result = target.value + 1
                target.set(self.set_flags_with_overflow(target.value, 1, result))
            elif inst == 8:
                self.stats.arithmetic_operations += 1
                target = self.registers[self.get_next()]
                result = target.value - 1
                target.set(self.set_flags_with_overflow(target.value, 1, result, True))
            elif inst == 10:
                if self.flags.is_flag_set(FlagRegister.ZERO):
                    self.stats.record_jump(True)
                    self.memory_pointer = self.get_next()
                    continue
                else:
                    self.stats.record_jump(False)
                self.get_next()
            elif inst == 11:
                if not self.flags.is_flag_set(FlagRegister.ZERO):
                    self.stats.record_jump(True)
                    self.memory_pointer = self.get_next()
                    continue
                else:
                    self.stats.record_jump(False)
                self.get_next()
            elif inst == 12:
                print(self.registers[self.get_next()].value)
            elif inst == 13:
                a = self.registers[self.get_next()]
                b = self.registers[self.get_next()]
                self.set_flags(int(a.value == b.value))
            elif inst == 14:
                if self.flags.is_flag_set(FlagRegister.SIGN):
                    self.stats.record_jump(True)
                    self.memory_pointer = self.get_next()
                    continue
                else:
                    self.stats.record_jump(False)
                self.get_next()
            elif inst == 15:
                if not self.flags.is_flag_set(FlagRegister.SIGN):
                    self.stats.record_jump(True)
                    self.memory_pointer = self.get_next()
                    continue
                else:
                    self.stats.record_jump(False)
                self.get_next()
            elif inst == 16:  # PUSH
                reg = self.registers[self.get_next()]
                self.stack_pointer.set(self.stack_pointer.value - 1)
                self.stats.record_stack_op(self.stack_pointer.value)
                self.memory[self.stack_pointer.value] = reg.value
            elif inst == 17:  # POP
                reg = self.registers[self.get_next()]
                reg.set(self.memory[self.stack_pointer.value])
                self.stack_pointer.set(self.stack_pointer.value + 1)
                self.stats.record_stack_op(self.stack_pointer.value)
            elif inst == 18:  # CALL
                self.stats.function_calls += 1
                target_addr = self.get_next()
                if self.stack_pointer.value == 0:
                    raise ValueError("Stack overflow")
                self.stack_pointer.set(self.stack_pointer.value - 1)
                self.stats.record_stack_op(self.stack_pointer.value)
                self.memory[self.stack_pointer.value] = self.memory_pointer + 1
                self.memory_pointer = target_addr
                continue
            elif inst == 19:  # RET
                self.stats.function_returns += 1
                if self.stack_pointer.value >= 0xFF:
                    raise ValueError("Stack underflow")
                self.memory_pointer = self.memory[self.stack_pointer.value]
                self.stack_pointer.set(self.stack_pointer.value + 1)
                self.stats.record_stack_op(self.stack_pointer.value)
                continue
            else:
                raise ValueError(f"Invalid instruction {inst} at {self.memory_pointer}")
            self.memory_pointer += 1
