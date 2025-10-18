#!/usr/bin/env python3

"""calculator.py

A small safe command-line calculator using Python's ast module to
parse and evaluate arithmetic expressions and a whitelist of math
functions/constants. Provides a REPL with history, help, and quit
commands.

Usage:
    python3 calculator.py
    python3 calculator.py "2 + 3 * 4"

Examples:
    calc> 2 + 3*4
    14
    calc> sin(pi/2)
    1.0
    calc> history
    1: 2 + 3*4 = 14
    2: sin(pi/2) = 1.0
"""

import ast
import operator
import math
import sys

# Allowed binary operators mapping
_ALLOWED_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    # intentionally disallow bitwise and other unsafe ops by omission
}

# Allowed unary operators mapping
_ALLOWED_UNARYOPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

# Whitelisted names (functions/constants) from math module
_ALLOWED_NAMES = {k: getattr(math, k) for k in [
    'sin','cos','tan','asin','acos','atan','atan2',
    'sinh','cosh','tanh',
    'degrees','radians',
    'sqrt','log','log10','exp','pow','hypot',
    'pi','e','tau','inf','nan',
    'factorial',
]}

# Also allow built-in abs and round
_ALLOWED_NAMES.update({'abs': abs, 'round': round})

def _safe_eval(node):
    """Recursively evaluate an AST node in a restricted manner.

    Supports: numbers, binary ops (+, -, *, /, //, %, **), unary +/-, 
    calls to whitelisted math functions, and names for whitelisted
    constants/functions.
    """
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)

    # Python 3.8+: ast.Constant for numbers
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Constants of type {type(node.value)} are not allowed")

    # Older Python: ast.Num
    if isinstance(node, ast.Num):
        return node.n

    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        func = _ALLOWED_BINOPS.get(op_type)
        if func is None:
            raise ValueError(f"Binary operator {op_type.__name__} is not allowed")
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        return func(left, right)

    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        func = _ALLOWED_UNARYOPS.get(op_type)
        if func is None:
            raise ValueError(f"Unary operator {op_type.__name__} is not allowed")
        operand = _safe_eval(node.operand)
        return func(operand)

    if isinstance(node, ast.Call):
        # Only allow simple function calls: Name(args...)
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only direct function calls are allowed")
        func_name = node.func.id
        func = _ALLOWED_NAMES.get(func_name)
        if func is None or not callable(func):
            raise ValueError(f"Function '{func_name}' is not allowed")
        args = [_safe_eval(arg) for arg in node.args]
        if node.keywords:
            raise ValueError("Keyword arguments are not supported")
        # Additional safety: restrict factorial to integers
        if func_name == 'factorial':
            if len(args) != 1 or not float(args[0]).is_integer() or args[0] < 0:
                raise ValueError("factorial() requires a single non-negative integer")
            return math.factorial(int(args[0]))
        return func(*args)

    if isinstance(node, ast.Name):
        val = _ALLOWED_NAMES.get(node.id)
        if val is None:
            raise ValueError(f"Name '{node.id}' is not allowed")
        return val

    if isinstance(node, ast.Tuple):
        return tuple(_safe_eval(elt) for elt in node.elts)

    raise ValueError(f"Unsupported expression: {ast.dump(node)}")

def evaluate(expr: str):
    """Parse expression to AST and evaluate safely.

    Raises ValueError for unsupported constructs or bad input.
    """
    try:
        tree = ast.parse(expr, mode='eval')
    except SyntaxError as e:
        raise ValueError(f"Syntax error: {e}")

    # Disallow attribute access, subscription, and string literals
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            raise ValueError("Attribute access is not allowed")
        if isinstance(node, ast.Subscript):
            raise ValueError("Subscription is not allowed")
        if isinstance(node, ast.Str):
            raise ValueError("String literals are not allowed")

    return _safe_eval(tree)

def repl():
    print("Simple Python calculator. Type 'help' for commands, 'quit' or 'q' to exit.")
    history = []
    while True:
        try:
            s = input('calc> ').strip()
        except (EOFError, KeyboardInterrupt):
            print('\nGoodbye')
            return

        if not s:
            continue

        low = s.lower()
        if low in ('quit', 'q', 'exit'):
            print('Goodbye')
            return

        if low in ('help', '?'):
            print("Commands:\n  help or ?\n  quit or q or exit\n  history\nExamples: 2+2, sin(pi/2), factorial(5)")
            continue

        if low == 'history':
            if not history:
                print('No history yet')
            else:
                for i, (expr, result) in enumerate(history, start=1):
                    print(f"{i}: {expr} = {result}")
            continue

        try:
            result = evaluate(s)
            history.append((s, result))
            print(result)
        except Exception as e:
            print('Error:', e)

if __name__ == '__main__':
    # If run with an expression as command-line arguments, evaluate and exit
    if len(sys.argv) > 1:
        expr = ' '.join(sys.argv[1:])
        try:
            print(evaluate(expr))
        except Exception as e:
            print('Error:', e)
            sys.exit(1)
    else:
        repl()