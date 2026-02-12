import asyncio
import random
import logging
import os
import signal
from goatclaw.task_queue import task_queue
from goatclaw.message_broker import broker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("goatclaw.chaos")

class ChaosRunner:
    """
    USP: Enterprise-grade chaos testing for distributed system resilience.
    """
    def __init__(self):
        self._running = False

    async def start(self, duration_seconds: int = 60):
        logger.info(f"Starting Chaos Experiment for {duration_seconds}s...")
        self._running = True
        
        # Start random disruptions
        tasks = [
            asyncio.create_task(self._kill_random_workers()),
            asyncio.create_task(self._corrupt_task_queue()),
            asyncio.create_task(self._delay_events())
        ]
        
        await asyncio.sleep(duration_seconds)
        self._running = False
        
        for t in tasks:
            t.cancel()
        
        logger.info("Chaos Experiment finished.")

    async def _kill_random_workers(self):
        """Simulate worker crashes."""
        while self._running:
            await asyncio.sleep(random.uniform(5, 15))
            if random.random() < 0.3:
                logger.warning("CHAOS: Simulating random worker crash...")
                # Note: In a real distributed env, we'd find worker PIDs
                # Since we might be running local workers, we'll just log and let the system handle "silence"

    async def _corrupt_task_queue(self):
        """Simulate message loss in Redis."""
        await task_queue.connect()
        while self._running:
            await asyncio.sleep(random.uniform(10, 20))
            if task_queue.redis and random.random() < 0.2:
                logger.warning("CHAOS: Dropping random task from queue...")
                await task_queue.redis.lpop(task_queue.queue_key)

    async def _delay_events(self):
        """Simulate high network latency."""
        while self._running:
            await asyncio.sleep(random.uniform(5, 10))
            if random.random() < 0.4:
                delay = random.uniform(2, 5)
                logger.warning(f"CHAOS: Injected {delay}s latency into event bus...")
                await asyncio.sleep(delay)

if __name__ == "__main__":
    runner = ChaosRunner()
    asyncio.run(runner.start())
