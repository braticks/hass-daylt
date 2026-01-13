import asyncio
from unittest.mock import AsyncMock, MagicMock
from aioresponses import aioresponses
from sensor import DayLtSensor

class MockHass:
    """Mock Home Assistant object."""
    def __init__(self):
        # Simulate the `data` dictionary used by Home Assistant
        self.data = {}
        self.helpers = MagicMock()  # Simulate other attributes if necessary
        self.bus = MagicMock()  # Mock the event bus
        self.bus.async_listen_once = AsyncMock(return_value=None)  # Simulate async event listening

    async def async_create_task(self, coroutine):
        """Mock method to simulate creating an async task."""
        await coroutine  # Await the coroutine directly in tests

async def test_sensor():
    """Test the DayLtSensor."""
    hass = MockHass()
    sensor = DayLtSensor(hass, "Test Sensor")
    # Simulate updating the sensor
    await sensor.async_update()
    
    # Print results
    print("State:", sensor.state)
    print("Attributes:", sensor.extra_state_attributes)

# Run the test
if __name__ == "__main__":
    asyncio.run(test_sensor())