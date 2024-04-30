
from taskiq import InMemoryBroker
import taskiq_fastapi

broker = InMemoryBroker()

taskiq_fastapi.init(broker, "app:main")
