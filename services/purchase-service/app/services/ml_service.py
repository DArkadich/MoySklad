import httpx

class MLService:
    def __init__(self, base_url: str = "http://ml-service:8002"):
        self.base_url = base_url

    async def get_forecast(self, product_id: str, days: int = 30):
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/api/v1/forecast/{product_id}?days={days}")
            response.raise_for_status()
            return response.json() 