"""Shared admission control for remote work; learns from completed throughput."""
import asyncio
import time


class AdaptiveConcurrency:
    def __init__(self, maximum=20, initial=6, window=15, clock=time.monotonic):
        self.maximum = maximum
        self.limit = min(initial, maximum)
        self.active = 0
        self.clock, self.window = clock, window
        self.condition = asyncio.Condition()
        self.cooldown_until = self.probe_after = 0
        self.started = clock()
        self.frames = self.completed = 0
        self.latency = 0
        self.rate = self.best_rate = 0
        self.best_limit = self.limit
        self.best_latency = 0

    async def __aenter__(self):
        async with self.condition:
            while self.active >= self.limit or self.clock() < self.cooldown_until:
                delay = self.cooldown_until - self.clock()
                try:
                    await asyncio.wait_for(self.condition.wait(), delay if delay > 0 else None)
                except TimeoutError:
                    pass
            if not self.active:
                self._reset_window()
            self.active += 1
        return self

    async def __aexit__(self, *args):
        async with self.condition:
            self.active -= 1
            self.condition.notify_all()

    def _reset_window(self):
        self.started = self.clock()
        self.frames = self.completed = 0
        self.latency = 0

    def success(self, frames, seconds):
        if not frames or self.clock() < self.cooldown_until:
            return
        self.frames += frames
        self.completed += 1
        self.latency += seconds
        elapsed = self.clock() - self.started
        if elapsed < self.window or self.completed < self.limit:
            return
        self.rate = self.frames * 60 / max(elapsed, .001)
        average = self.latency / self.completed
        # A trial with more requests must earn its slots with more throughput.
        if self.limit > self.best_limit and self.rate < self.best_rate * 1.05:
            self.limit = self.best_limit
            self.probe_after = self.clock() + 60
        elif self.best_latency and average > self.best_latency * 1.7 and self.rate < self.best_rate * .9:
            self.limit = max(1, self.limit // 2)
            self.best_limit, self.best_rate = self.limit, 0
            self.best_latency = 0
            self.probe_after = self.clock() + 30
        else:
            if self.rate >= self.best_rate:
                self.best_rate, self.best_limit, self.best_latency = self.rate, self.limit, average
            if self.clock() >= self.probe_after:
                self.limit = min(self.maximum, self.limit * 2)
        self._reset_window()

    def throttle(self):
        now = self.clock()
        # Concurrent 429s from the same burst count as one reduction.
        if now >= self.cooldown_until:
            self.limit = max(1, self.limit // 2)
        self.cooldown_until = max(self.cooldown_until, now + 10)
        self.probe_after = self.cooldown_until + 30
        self.best_limit, self.best_rate, self.best_latency = self.limit, 0, 0
        self._reset_window()

    def status(self):
        return {'active': self.active, 'limit': self.limit, 'maximum': self.maximum,
                'frames_per_minute': round(self.rate, 1),
                'cooling_down': self.clock() < self.cooldown_until}
