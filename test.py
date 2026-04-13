# flake8: noqa
"""
本地随便写的演示模块，用来测翻译工具是否正常。

说明：
- 与具体业务无关
- 可以安全删掉
"""

import math
import random
from dataclasses import dataclass
from typing import Iterable, List


@dataclass
class Point2D:
    x: float
    y: float

    def distance_to(self, other: "Point2D") -> float:
        # 二维欧氏距离，单位与坐标一致
        return math.hypot(self.x - other.x, self.y - other.y)


def jitter(values: List[float], sigma: float = 0.05) -> List[float]:
    """给序列加一点高斯噪声，画图时没那么死板。"""
    return [v + random.gauss(0, sigma) for v in values]


def running_mean(items: Iterable[float], window: int) -> List[float]:
    if window < 1:
        raise ValueError("window must be >= 1")
    seq = list(items)
    out: List[float] = []
    acc = 0.0
    for i, v in enumerate(seq):
        acc += v
        if i >= window:
            acc -= seq[i - window]
        if i >= window - 1:
            out.append(acc / window)
    return out


def fake_score(name: str) -> int:
    # 用字符码求和再取模，纯属玩具，别当真
    return sum(ord(c) for c in name) % 97


def summarize_pairs(pairs: List[tuple[str, int]]) -> dict[str, float]:
    """按首字母分组，对每组里的数值求平均。"""
    buckets: dict[str, List[int]] = {}
    for key, val in pairs:
        prefix = key[:1].upper() if key else "?"
        buckets.setdefault(prefix, []).append(val)
    return {k: sum(v) / len(v) for k, v in buckets.items()}


class Counter:
    def __init__(self) -> None:
        self._n = 0

    def inc(self, delta: int = 1) -> None:
        # 递增；delta 默认 1
        self._n += delta

    @property
    def value(self) -> int:
        return self._n


def _demo() -> None:
    # 随机撒几个点，算到原点的距离并排序
    pts = [Point2D(random.random(), random.random()) for _ in range(5)]
    origin = Point2D(0.0, 0.0)
    dists = sorted(p.distance_to(origin) for p in pts)
    print("distances:", [round(d, 3) for d in dists])

    xs = list(range(10))
    ys = jitter([math.sin(x / 2) for x in xs])
    # 滑动平均窗口长度为 3
    print("smoothed-ish:", [round(y, 3) for y in running_mean(ys, 3)])

    c = Counter()
    for _ in range(7):
        c.inc()
    print("counter:", c.value)

    pairs = [("alpha", 3), ("alice", 10), ("beta", 4), ("bob", 9)]
    print("summarize:", summarize_pairs(pairs))


if __name__ == "__main__":
    random.seed(42)
    _demo()
