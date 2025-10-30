import sys
import math
import pyray as rl

ZERO = rl.Vector2(0, 0)
ONE = rl.Vector2(1, 1)
HALF = rl.Vector2(0.5, 0.5)
LEFT = rl.Vector2(-1, 0)
RIGHT = rl.Vector2(1, 0)
UP = rl.Vector2(0, -1)
DOWN = rl.Vector2(0, 1)


def collides(a: rl.Rectangle, b: rl.Rectangle) -> bool:
    return (
        a.x + a.width >= b.x
        and a.x <= b.x + b.width
        and a.y + a.height >= b.y
        and a.y <= b.y + b.height
    )


def normalize(v: rl.Vector2) -> rl.Vector2:
    l2 = length2(v)
    if l2 <= sys.float_info.epsilon:
        return ZERO

    inv = 1.0 / math.sqrt(l2)
    return rl.Vector2(v.x * inv, v.y * inv)


def length(v: rl.Vector2) -> float:
    return math.sqrt(length2(v))


def length2(v: rl.Vector2) -> float:
    return v.x * v.x + v.y * v.y


def distanceTo(v1: rl.Vector2, v2: rl.Vector2) -> float:
    return length(rl.Vector2(v1.x - v2.x, v1.y - v2.y))


def distanceToSquared(v1: rl.Vector2, v2: rl.Vector2) -> float:
    return length2(rl.Vector2(v1.x - v2.x, v1.y - v2.y))
