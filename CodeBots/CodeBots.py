#!/usr/bin/env python

import os
import random

num_lines = 24
num_copies = 50
num_turns = 5000
num_games = 10
width = 0
height = 0
bots = {}

directions = North, East, South, West = ((0, -1), (1, 0), (0, 1), (-1, 0))

recursives = set()

class BlockedException(BaseException):
    pass

class BadFormatException(BaseException):
    pass

class Action(object):
    def __init__(self, name, args=(), func=lambda b: None):
        self.name = name
        self.args = args
        self.func = func
        self.hash = hash(args)

    def equals(self, other):
        return self.name == other.name

    def __eq__(self, other):
        return self.equals(other) and self.args == other.args

    def __call__(self, *args, **kwargs):
        if self.hash in recursives:
            return
        recursives.add(self.hash)
        return self.func(*args, **kwargs)

    def __str__(self):
        return self.name+" "+" ".join(self.args)

ArgumentTypes = Int, Var, Line = range(3)

class Argument(object):
    def __init__(self, string):
        self.num_line_opponents = 0
        self.type = Var
        self.string = string
        if "+" in string:
            self.type = Int
        if "#" in string:
            self.type = Line
            parts = string.split("#")
            if len(parts) > 2:
                raise BadFormatException
            self.num_line_opponents = len(parts[0])
            string = parts[1]
        self.parts_to_add = []
        for part in string.split("+"):
            num_opponents = part.count("*")
            if not part.startswith("*"*num_opponents):
                raise BadFormatException
            part = part[num_opponents:]
            try:
                self.parts_to_add.append((int(part), 0))
                if self.type == Var:
                    self.type = Int
                continue
            except ValueError:
                pass
            if part < "A" or part > "E":
                raise BadFormatException
            self.parts_to_add.append((part, num_opponents))
        self.var_name = self.parts_to_add[0][0] \
            if len(self.parts_to_add) is 1 else None
        if not len(self.parts_to_add):
            raise BadFormatException

    def __str__(self):
        return self.string

    def __hash__(self):
        return hash(self.string)

    def step_opponents(self, person, num_opponents):
        for _ in xrange(num_opponents):
            person = person.get_opponent()
            if not person:
                return None
        return person

    def get_value(self, person):
        return_person = person
        if len(self.parts_to_add) == 1:
            return_person = self.step_opponents(person, self.parts_to_add[0][1])
            if not return_person:
                return None, None
            return_val = self.parts_to_add[0][0] % num_lines
        else:
            sum = 0
            for part, opponents in self.parts_to_add:
                return_person = self.step_opponents(person, opponents)
                if not return_person:
                    return None, None
                sum += return_person.parse_number(part)
            return_val = sum % num_lines
        if self.type is Line:
            opponent = self.step_opponents(person, self.num_line_opponents)
            return_val = return_person.parse_number(return_val)
            return_person = opponent
        return return_person, return_val

_
class Bot(object):
    def __init__(self, name, coordinates, code):
        self.name = name
        self.vars = {"A": 0, "B": 0, "C": 0,
                     "D": random.randrange(num_lines), "E": random.randrange(num_lines)}
        self.coordinates = coordinates
        self.blocked = {}
        self.actions = self.read_code(code)

    def __str__(self):
        return "\n".join(self.actions)

    def read_code(self, code):
        actions = []
        for line in code.splitlines():
            if r"//" in line:
                line = line[:line.index(r"//")]
            line = line.strip()
            if not line:
                continue
            words = line.split(" ")
            method_holder = self if words[0] == "Flag" else Bot
            try:
                actions.append(getattr(method_holder, words[0])(*words[1:]))
            except BadFormatException:
                print "Error on Line "+str(len(actions)) + " in " +self.name
                actions.append(Line)
                raise
        while len(actions) < num_lines:
            actions.append(self.Flag())
        return actions

    def get_arg(self, argument):
        person, val = argument.get_value(self)
        if not person:
            return None
        if argument.type == Int:
            return val % num_lines
        if argument.type == Line:
            return person.actions[val % num_lines]
        return person.vars[argument.var_name] % num_lines

    def set_arg(self, argument, value):
        value = self.get_arg(value)
        if value is None:
            return
        person, val = argument.get_value(self)
        if person is None:
            return
        person.check_blocked(argument.var_name)
        if argument.type == Line:
            person.actions[val % num_lines] = value
        if argument.type == Var:
            person.vars[val] = value

    def check_blocked(self, val):
        if val in self.blocked and self.blocked[val]:
            self.blocked[val].pop()
            raise BlockedException()

    def parse_number(self, num):
        if isinstance(num, int):
            return num
        return self.vars[num]

    def get_direction(self):
        try:
            direction = directions[self.vars["D"] % 4]
        except:
            import pdb
            pdb.set_trace()
            raise
        position = [d+c for d, c in zip(direction, self.coordinates)]
        if position[0] < 0:
            position[0] += width
        elif position[0] >= width:
            position[0] -= width
        if position[1] < 0:
            position[1] += height
        elif position[1] >= height:
            position[1] -= height
        return tuple(position)

    def get_opponent(self):
        d = self.get_direction()
        if d in bots:
            return bots[d]
        else:
            return None

    @classmethod
    def Move(cls):
        global bots
        def move(b):
            new_coordinates = b.get_direction()
            if new_coordinates not in bots:
                del bots[b.coordinates]
                bots[new_coordinates] = b
                b.coordinates = new_coordinates
        return Action(name="Move", func=move)

    def Flag(self):
        flag_type = self.name
        return Action(name="Flag", args=(flag_type,))

    @classmethod
    def Copy(cls, copy_from, copy_to):
        copy_from = Argument(copy_from)
        copy_to = Argument(copy_to)
        if copy_to.type == Int:
            raise BadFormatException
        if (copy_to.type == Line or copy_from.type == Line) \
                and copy_from.type != copy_to.type:
            raise BadFormatException
        return Action(name="Copy", args=(copy_from, copy_to),
                      func=lambda b: b.set_arg(copy_to, copy_from))

    @classmethod
    def Block(cls, var_name):
        var_name = Argument(var_name)
        if var_name.type == Int:
            raise BadFormatException
        uniqifier = random.random()
        def block(b):
            person, var = var_name.get_value(b)
            if not person:
                return
            if var not in person.blocked:
                person.blocked[var] = set()
            person.blocked[var].add(uniqifier)
        return Action(name="Block", args=(var_name,), func=block)

    @classmethod
    def If(cls, condition, line1, line2):
        c = cls.parse_condition(condition)
        line1 = Argument(line1)
        line2 = Argument(line2)
        if line1.type != Line or line2.type != Line:
            raise BadFormatException
        return Action(name="If", args=(condition, line1, line2),
                      func=lambda b: b.get_arg(line1)(b) if c(b)
                      else b.get_arg(line2)(b))
    @classmethod
    def parse_condition(cls, condition):
        if "==" in condition:
            try:
                val1, val2 = tuple(condition.split("=="))
            except ValueError:
                raise BadFormatException
            val1 = Argument(val1)
            val2 = Argument(val2)
            if (val1.type == Line or val2.type == Line) \
                    and val2.type != val1.type:
                raise BadFormatException
            def is_equal(b):
                v1 = b.get_arg(val1)
                v2 = b.get_arg(val2)
                if v1 is None or v2 is None:
                    return False
                return v1 == v2
            return is_equal
        if "=" in condition:
            try:
                val1, val2 = tuple(condition.split("="))
            except ValueError:
                raise BadFormatException
            val1 = Argument(val1)
            val2 = Argument(val2)
            if (val1.type == Line or val2.type == Line) \
                    and val2.type != val1.type:
                raise BadFormatException
            def equals(b):
                v1 = b.get_arg(val1)
                v2 = b.get_arg(val2)
                if v1 is None or v2 is None:
                    return False
                if val1.type == Line:
                    return b.get_arg(val1).equals(b.get_arg(val2))
                return val1 == val2
            return equals
        condition = Argument(condition)
        if condition.type == Line:
            def test_line(b):
                person, arg = condition.get_value(b)
                if person is None:
                    return False
                return person.actions[arg].name == "Flag"
            return test_line
        if condition.type == Var:
            if condition.var_name == "E":
                def test_e(b):
                    person, arg = condition.get_value(b)
                    return bool(person.vars[arg] % 2)
                return test_e
            if condition.var_name == "D":
                def test_d(b):
                    person, arg = condition.get_value(b)
                    return person.get_direction() in bots
                return test_d
            def test_all(b):
                person, arg = condition.get_value(b)
                return bool(person.vars[arg])
            return test_all
        return lambda b: bool(condition.get_value(b)[1])

    def act(self):
        recursives.clear()
        self.vars["E"] = random.randrange(num_lines)
        try:
            self.actions[self.vars["C"]](self)
        except BlockedException:
            pass
        self.vars["C"] += 1
        if self.vars["C"] >= num_lines:
            self.vars["C"] -= num_lines

    def declare_flag(self):
        flags = {}
        for action in self.actions:
            if action.name == "Flag":
                flag = action.args[0]
                if flag not in flags:
                    flags[flag] = 1
                else:
                    flags[flag] += 1
        max_flag_count = 0
        max_flag = 0
        for flag, amount in flags.items():
            if amount > max_flag_count:
                max_flag = flag
                max_flag_count = amount
            elif amount == max_flag_count:
                max_flag = 0
        return max_flag

def read_bots():
    b = [(read_file("bots/"+f), f.replace(".txt","")) for f in os.listdir("bots/")]*num_copies
    random.shuffle(b)
    global width
    global height
    width = int((len(b)*4)**.5)
    height = int(len(b)*4/width)+1
    for x in xrange(width):
        for y in xrange(height):
            if (x%4 == 0 and y%2 == 0) or (x%4 == 2 and y%2 == 1):
                coordinates = (x,y)
                code, name = b.pop()
                bots[coordinates] = Bot(name, coordinates, code)
                if not b:
                    return


def read_file(filename):
    f = file(filename)
    s = f.read()
    f.close()
    return s


if __name__ == "__main__":
    import time
    start_time = time.time()
    points = {}
    for game in xrange(num_games):
        bots.clear()
        read_bots()
        for turn in xrange(num_turns):
            if not turn % 100:
                print "Game:"+str(game)+ " Turn:"+str(turn)
            for bot in bots.values():
                bot.act()
        for bot in bots.values():
            flag = bot.declare_flag()
            if flag in points:
                points[flag] += 1
            else:
                points[flag] = 1
    finish_time = time.time()
    running_time = (finish_time-start_time)

    total_scores = sorted([x[::-1] for x in points.items()])[::-1]

    for score, name in total_scores:
        if name == 0:
            print "> There were "+str(score)+" bots with equal flags\n"
        else:
            print "> "+name+" had "+str(score)+" points\n"
    print "Execution took "+str(running_time)+" seconds"