import sys
import re

class HPXError(Exception):
    pass

class StopLoop(Exception):
    pass


class Interpreter:
    def __init__(self):
        self.variables = {}

    def _normalize_equality(self, expr: str) -> str:
        return re.sub(r'(?<![!<>=])=(?![=])', '==', expr)

    def _eval_env(self):
        return {
            "whole": int,
            "decimal": float,
            "letters": str,
            "ask": lambda prompt='': input(prompt),
        }

    def evaluate(self, expr: str):
        if expr is None:
            raise HPXError("Empty expression")
        expr = expr.strip()

        expr = self._normalize_equality(expr)

        try:
            env = self._eval_env()
            return eval(expr, {}, {**env, **self.variables})
        except HPXError:
            raise
        except Exception as e:
            raise HPXError(f"Invalid expression `{expr}`: {e}")

    def execute(self, lines):
        self.run_block(lines, 0, len(lines))

    def run_block(self, lines, start, end):
        i = start
        while i < end:
            raw = lines[i].rstrip("\n")
            line = raw.strip()

            if not line or line.startswith("#"):
                i += 1
                continue

            if line.startswith("keep "):
                self.handle_keep(line)

            elif line.startswith("say"):
                self.handle_say(line)

            elif line == "stop":
                raise StopLoop()

            elif line.startswith("when "):
                i = self.handle_when(lines, i)

            elif line.startswith("repeat until "):
                i = self.handle_repeat_until(lines, i)

            elif line.startswith("forever"):
                i = self.handle_forever(lines, i)

            else:
                raise HPXError(f"Unknown instruction: `{line}` (line {i+1})")

            i += 1

    def handle_keep(self, line: str):

        try:
            parts = line.split(" ", 3)
            if len(parts) < 4 or parts[2] != "to":
                raise ValueError
            _, name, _, expr = parts
        except Exception:
            raise HPXError(f"Invalid keep statement: `{line}`")

        expr = expr.strip()

        if expr == "ask":
            value = input()
        else:
            value = self.evaluate(expr)

        self.variables[name] = value

    def handle_say(self, line: str):
        if not line.startswith("say(") or not line.endswith(")"):
            raise HPXError(f"Invalid say statement, use say(<expression>) : `{line}`")
        inner = line[4:-1].strip()
        if inner == "":
            raise HPXError("say() requires an expression")
        value = self.evaluate(inner)
        print(value)

    def collect_block(self, lines, start):
        base_indent = len(lines[start]) - len(lines[start].lstrip())
        block = []
        i = start + 1

        while i < len(lines):
            indent = len(lines[i]) - len(lines[i].lstrip())
            if indent <= base_indent:
                break
            block.append(lines[i])
            i += 1

        return block, i - 1

    def handle_when(self, lines, index):
        branches = []
        i = index

        while True:
            if i >= len(lines):
                break
            line = lines[i].strip()

            if line.startswith("when "):
                condition = line[5:].strip()
            elif line.startswith("or "):
                condition = line[3:].strip()
            elif line.startswith("complete"):
                condition = None
            else:
                break

            block, i = self.collect_block(lines, i)
            branches.append((condition, block))

            i += 1
            if i >= len(lines):
                break

            next_line = lines[i].strip()
            if not (next_line.startswith("or ") or next_line.startswith("complete")):
                break

        for condition, block in branches:
            if condition is None or self.evaluate(condition):
                self.run_block(block, 0, len(block))
                break

        return i - 1

    def handle_repeat_until(self, lines, index):
        condition = lines[index].strip()[13:].strip()
        if condition == "":
            raise HPXError("repeat until requires a condition")
        block, end = self.collect_block(lines, index)

        while not self.evaluate(condition):
            try:
                self.run_block(block, 0, len(block))
            except StopLoop:
                break

        return end

    def handle_forever(self, lines, index):
        block, end = self.collect_block(lines, index)
        while True:
            try:
                self.run_block(block, 0, len(block))
            except StopLoop:
                break
        return end


def load_file(path):
    if not path.endswith(".hpx"):
        raise HPXError("File must have .hpx extension")
    with open(path, "r", encoding="utf-8") as f:
        return f.readlines()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 hpx_interpreter.py program.hpx")
        sys.exit(1)

    try:
        program = load_file(sys.argv[1])
        Interpreter().execute(program)
    except HPXError as e:
        print("HPX Error:", e)
