"""
Simulates QuickCart-style traffic against a running AgentGate instance, so the
dashboard has real numbers to show: repeat questions (cache hits), an abusive
burst (blocked requests), and normal varied traffic (provider calls).

Usage:
    uvicorn app.main:app &
    python load_test.py
"""

import asyncio
import random
import httpx

BASE_URL = "http://localhost:8000"

COMMON_QUESTIONS = [
    "where is my order",
    "how do I return an item",
    "what is your refund policy",
    "when will my order arrive",
    "how do I track my package",
]


async def normal_traffic(client: httpx.AsyncClient, n: int):
    for _ in range(n):
        q = random.choice(COMMON_QUESTIONS)
        key = f"user-{random.randint(1, 50)}"
        await client.post(f"{BASE_URL}/v1/chat", json={"api_key": key, "prompt": q})
        await asyncio.sleep(random.uniform(0.02, 0.1))


async def abusive_burst(client: httpx.AsyncClient, n: int):
    key = "bad-actor-1"
    for _ in range(n):
        await client.post(
            f"{BASE_URL}/v1/chat",
            json={"api_key": key, "prompt": "spam request " + str(random.random())},
        )


async def main():
    async with httpx.AsyncClient(timeout=10) as client:
        print("Sending normal QuickCart-style traffic...")
        await normal_traffic(client, 150)

        print("Simulating an abusive burst...")
        await abusive_burst(client, 40)

        stats = (await client.get(f"{BASE_URL}/api/stats")).json()
        print("\nFinal stats:")
        for k, v in stats.items():
            print(f"  {k}: {v}")


if __name__ == "__main__":
    asyncio.run(main())
