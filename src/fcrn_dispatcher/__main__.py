import argparse
import asyncio
from uuid import UUID, uuid4

from psycopg import AsyncConnection

from fcrn_dispatcher.battery import simulated_battery
from fcrn_dispatcher.runtime import fast_loop, run
from fcrn_dispatcher.sample import Sample
from fcrn_dispatcher.settings import Settings
from fcrn_dispatcher.step_test import (
    DOWN_BOUNDS,
    STEP_TEST,
    UP_BOUNDS,
    requirement_1,
    steady_state_response,
)
from fcrn_dispatcher.store import postgres_store, read_samples


async def run_step_test(settings: Settings, run_id: UUID) -> list[Sample]:
    """Run the step test into Postgres and read the run's samples back."""
    async with await AsyncConnection.connect(
        settings.database_url, autocommit=True
    ) as conn:
        battery = simulated_battery(
            settings.battery_energy_wh,
            settings.battery_max_power_w,
            settings.battery_initial_soc,
        )
        await run(
            STEP_TEST, battery, settings.fcrn_capacity_w, postgres_store(conn, run_id)
        )
        return await read_samples(conn, run_id)


def main() -> None:
    parser = argparse.ArgumentParser(prog="fcrn-dispatcher")
    parser.add_argument(
        "--fast", action="store_true", help="run on accelerated loop time"
    )
    args = parser.parse_args()
    settings = Settings()
    run_id = uuid4()
    print(f"Run {run_id}")

    with asyncio.Runner(loop_factory=fast_loop if args.fast else None) as runner:
        samples = runner.run(run_step_test(settings, run_id))

    ratios = requirement_1(*steady_state_response(samples), settings.fcrn_capacity_w)
    passed = True
    for name, ratio, (low, high) in zip(
        ("up", "down"), ratios, (UP_BOUNDS, DOWN_BOUNDS), strict=True
    ):
        ok = low <= ratio <= high
        passed &= ok
        print(
            f"Requirement 1 {name}: {ratio:+.3f} (allowed {low:+.2f}..{high:+.2f})"
            + ("" if ok else " FAIL")
        )
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
