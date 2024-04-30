from datetime import datetime, timezone
import logging
import threading
import uuid as uuid_pkg


class AgentLock:
    """ Represents the result of a AgentManager.try_acquire_lock method
        You must check 'lock.acquired' before you enter the code which requires the lock
        Furthermore, if you successfully acquired the lock you must release it with AgentLock.release()
    """
    def __init__(self, acquired: bool, agent_id: uuid_pkg.uuid4, lock: threading.Lock = None):
        self.acquired = acquired
        self.agent_id = agent_id
        self.lock = lock

    def release(self):
        """ release the lock held be the agent"""
        if self.lock is not None:
            agent_manager.release(lock=self.lock, agent_id=self.agent_id)


class AgentManager:
    _locks: dict[uuid_pkg.uuid4, threading.Lock] = dict()
    _last_task: dict[uuid_pkg.uuid4] = dict()

    _internalLock = threading.Lock()

    def __init__(self):
        # Creating a lock for each agent based on their unique ID
        self._internalLock = threading.Lock()

    def _find_lock(self, agent_id: uuid_pkg.uuid4) -> threading.Lock:
        self._internalLock.acquire()
        try:
            if agent_id not in self._locks:
                self._locks[agent_id] = threading.Lock()
            return self._locks[agent_id]
        finally:
            self._internalLock.release()

    def try_acquire_lock(self, agent_id: uuid_pkg.uuid4) -> AgentLock:
        """ tries to acquire a write lock for the specified agent
            :returns an AgentLock with acquire: True if this was successful, False otherwise
        """
        # Acquiring the lock for the specific agent
        lock = self._find_lock(agent_id=agent_id)
        if lock.acquire(blocking=False):
            logging.info(f"AgentManager.lock SUCCESSFULLY acquired lock for agent: {agent_id}")
            return AgentLock(acquired=True, lock=lock, agent_id=agent_id)
        else:
            logging.info(f"AgentManager.lock UNSUCCESSFULLY lock not acquired for agent: {agent_id}")
            return AgentLock(acquired=False, agent_id=agent_id)

    def release(self, agent_id: uuid_pkg.uuid4, lock: threading.Lock):
        """ Only to be called from AgentLock.release() """
        if (agent_id in self._locks
                and lock == self._locks[agent_id]):
            self._last_task[agent_id] = datetime.now(timezone.utc)
            lock.release()
            logging.info(f"AgentManager.release lock was released: {agent_id}, {self._last_task[agent_id]}")
        else:
            logging.info(f"AgentManager.release lock was not released: {agent_id}")

    def last_task_completed(self, agent_id: uuid_pkg.uuid4):
        """ returns the last time an agent completed a task or None if the agent
            has not completed a task yet
        """
        if agent_id in self._last_task:
            return self._last_task[agent_id]
        return None


agent_manager = AgentManager()
