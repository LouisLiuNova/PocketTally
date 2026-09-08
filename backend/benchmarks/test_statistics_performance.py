"""Issue #16 独立十万笔统计性能门禁。"""

import math
import platform
import sqlite3
from pathlib import Path
from statistics import median
from time import perf_counter_ns

import pytest
from httpx import ASGITransport, AsyncClient
from loguru import logger

from app.config import Settings
from app.main import create_app
from tests.statistics_scale_support import seed_scale_ledger, statistics_requests

SAMPLE_COUNT = 20
MAX_P95_SECONDS = 1.0


def nearest_rank_p95(samples: list[float]) -> float:
    """按 nearest-rank 方法计算 p95。"""

    return sorted(samples)[math.ceil(0.95 * len(samples)) - 1]


@pytest.mark.asyncio
async def test_statistics_warm_p95(tmp_path: Path) -> None:
    """验证八个常用查询在十万笔账本上预热后 p95 不超过一秒。"""

    logger.disable("app")
    app = create_app(
        Settings(environment="test", database_path=tmp_path / "performance.sqlite3")
    )
    try:
        async with (
            app.router.lifespan_context(app),
            AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client,
        ):
            await seed_scale_ledger(client, app.state.resources.engine)
            requests = statistics_requests()
            results: dict[str, list[float]] = {}
            for name, (path, params) in requests.items():
                warmup = await client.get(path, params=params)
                assert warmup.status_code == 200, warmup.text
                samples = []
                for _ in range(SAMPLE_COUNT):
                    started = perf_counter_ns()
                    response = await client.get(path, params=params)
                    elapsed = (perf_counter_ns() - started) / 1_000_000_000
                    assert response.status_code == 200, response.text
                    samples.append(elapsed)
                results[name] = samples
    finally:
        logger.enable("app")

    print(
        f"environment: platform={platform.platform()} "
        f"python={platform.python_version()} sqlite={sqlite3.sqlite_version}"
    )
    print("endpoint samples min_s median_s p95_s max_s")
    failures = []
    for name, samples in results.items():
        p95 = nearest_rank_p95(samples)
        print(
            f"{name} {len(samples)} {min(samples):.6f} "
            f"{median(samples):.6f} {p95:.6f} {max(samples):.6f}"
        )
        if p95 > MAX_P95_SECONDS:
            failures.append(f"{name}={p95:.6f}s")
    assert not failures, "p95 超过 1 秒：" + ", ".join(failures)
