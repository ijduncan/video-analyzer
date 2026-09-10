import asyncio

from app.services.adaptive_concurrency import AdaptiveConcurrency


class Clock:
    now = 0

    def __call__(self):
        return self.now


def complete_window(gate, clock, count, frames=3, latency=8):
    clock.now += 15
    for _ in range(count):
        gate.success(frames, latency)


def test_grows_when_throughput_improves_and_respects_maximum():
    clock = Clock()
    gate = AdaptiveConcurrency(20, clock=clock)
    complete_window(gate, clock, 6)
    assert gate.limit == 12
    complete_window(gate, clock, 12)
    assert gate.limit == 20
    complete_window(gate, clock, 20)
    assert gate.limit == 20 and gate.status()['frames_per_minute'] == 240


def test_unproductive_concurrency_rolls_back_and_waits_before_retesting():
    clock = Clock()
    gate = AdaptiveConcurrency(20, clock=clock)
    complete_window(gate, clock, 6)
    complete_window(gate, clock, 12)
    assert gate.limit == 20
    complete_window(gate, clock, 20, frames=1, latency=20)
    assert gate.limit == 12
    complete_window(gate, clock, 12)
    assert gate.limit == 12


def test_shared_throttling_reduces_once_per_burst_and_holds_recovery():
    clock = Clock()
    gate = AdaptiveConcurrency(20, initial=20, clock=clock)
    gate.throttle()
    assert gate.limit == 10 and gate.status()['cooling_down']
    gate.throttle()
    assert gate.limit == 10
    clock.now += 11
    assert not gate.status()['cooling_down']
    complete_window(gate, clock, 10)
    assert gate.limit == 10  # Do not immediately ramp back into the same throttle.


def test_cancelled_waiter_does_not_leak_capacity():
    async def verify():
        gate = AdaptiveConcurrency(maximum=2)
        async with gate:
            async with gate:
                waiter = asyncio.create_task(gate.__aenter__())
                await asyncio.sleep(0)
                assert gate.active == 2 and not waiter.done()
                waiter.cancel()
                await asyncio.gather(waiter, return_exceptions=True)
            assert gate.active == 1
        assert gate.active == 0
        async with gate:
            assert gate.active == 1

    asyncio.run(verify())


def test_reduction_drains_inflight_requests_before_admitting_more():
    async def verify():
        clock = Clock()
        gate = AdaptiveConcurrency(maximum=3, clock=clock)
        for _ in range(3):
            await gate.__aenter__()
        gate.throttle()
        clock.now += 11
        waiter = asyncio.create_task(gate.__aenter__())
        await asyncio.sleep(0)
        await gate.__aexit__()
        await asyncio.sleep(0)
        assert not waiter.done() and gate.active == 2
        await gate.__aexit__()
        await asyncio.sleep(0)
        assert not waiter.done() and gate.active == 1
        await gate.__aexit__()
        await asyncio.wait_for(waiter, 1)
        assert gate.active == 1
        await gate.__aexit__()
        assert gate.active == 0

    asyncio.run(verify())
