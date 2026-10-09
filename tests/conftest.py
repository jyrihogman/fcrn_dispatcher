from collections.abc import Awaitable, Callable

import pytest

from fcrn_dispatcher.sample import Sample


@pytest.fixture
def stored() -> list[Sample]:
    return []


@pytest.fixture
def write_batch(stored: list[Sample]) -> Callable[[list[Sample]], Awaitable[None]]:
    async def write_batch(batch: list[Sample]) -> None:
        stored.extend(batch)

    return write_batch
