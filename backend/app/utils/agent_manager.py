from datetime import datetime, timezone
import threading
import uuid as uuid_pkg
from app.models import Idea


class AgentContext:

    def __init__(self, idea: Idea):
        self.last_idea = idea


class AgentGenerationLock:
    """ Represents the result of a AgentManager.try_acquire_generation_lock method
        You must check 'lock.acquired' before you enter the code which requires the lock
        Furthermore, if you successfully acquired the lock you must release it with AgentGenerationLock.release()
    """
    def __init__(self,
                 agent_id: uuid_pkg.uuid4,
                 context: AgentContext | None = None,
                 lock: threading.Lock = None):
        self.acquired = lock is not None
        self.agent_id = agent_id
        self._lock = lock
        self._context = context
        self._released = not self.acquired

    def get_last_idea(self) -> Idea | None:
        if self._context is not None and self._context.last_idea is not None:
            return self._context.last_idea
        return None

    def set_last_idea(self, idea: Idea | None):
        self._context = AgentContext(idea)

    def get_last_id(self) -> uuid_pkg.uuid4:
        if self._context is not None and self._context.last_idea is not None:
            return self._context.last_idea.id
        return None

    def release(self):
        """ release the lock held be the agent"""
        if self._released:
            return
        if self._lock is not None:
            self._released = True
            agent_manager.release_generation_lock(lock=self._lock, agent_id=self.agent_id, next_context=self._context)


class AgentContributionLock:
    """ Represents the result of a AgentManager.acquire_contribution_lock method
        This lock was always acquired and must be released by calling AgentContributionLock.release()
    """
    def __init__(self, agent_id: uuid_pkg.uuid4, lock: threading.Lock = None):
        self.agent_id = agent_id
        self.lock = lock

    def release(self):
        """ release the lock held be the agent"""
        if self.lock is not None:
            agent_manager.release_contribution_lock(lock=self.lock, agent_id=self.agent_id)


class AgentManager:
    """
        The AgentManager provides a locking facilities for two types
        a) making sure that the same agent is not generating ideas more than once
        b) synchronizing the internal counter, so that if XLeap sends two ideas at the same
           time they do get different idea counts
    """
    _generation_locks: dict[uuid_pkg.uuid4, threading.Lock] = dict()
    """ map from Agent uuid to lock for that agent """
    _contribution_lock: dict[uuid_pkg.uuid4, threading.Lock] = dict()
    """ map from Agent uuid to lock for that agent """
    _last_generation: dict[uuid_pkg.uuid4] = dict()
    """ the last time the _generation_lock for an agent was returned """
    _generation_context: dict[uuid_pkg.uuid4, AgentContext] = dict()
    """ map from Agent uuid to lock to the last uuid the agent contribution was triggered for """

    _internalLock = threading.Lock()

    def __init__(self):
        # Creating a lock for each agent based on their unique ID
        self._internalLock = threading.Lock()

    def _find_generation_lock(self, agent_id: uuid_pkg.uuid4) -> threading.Lock:
        self._internalLock.acquire()
        try:
            if agent_id not in self._generation_locks:
                self._generation_locks[agent_id] = threading.Lock()
            return self._generation_locks[agent_id]
        finally:
            self._internalLock.release()

    def _find_contribution_lock(self, agent_id: uuid_pkg.uuid4) -> threading.Lock:
        self._internalLock.acquire()
        try:
            if agent_id not in self._contribution_lock:
                self._contribution_lock[agent_id] = threading.Lock()
            return self._contribution_lock[agent_id]
        finally:
            self._internalLock.release()

    def acquire_contribution_lock(self, agent_id: uuid_pkg.uuid4) -> AgentContributionLock:
        """ Acquire a write lock to create a new contribution (e.g. Idea). Blocks until the write
            lock was acquired
            :returns the AgentContributionLock which must be release with AgentContributionLock.release()
        """
        # Acquiring the lock for the specific agent
        lock = self._find_contribution_lock(agent_id=agent_id)
        lock.acquire(blocking=True)
        return AgentContributionLock(lock=lock, agent_id=agent_id)

    def try_acquire_generation_lock(self, agent_id: uuid_pkg.uuid4) -> AgentGenerationLock:
        """ tries to acquire a write lock for the specified agent
            :returns an AgentLock with acquire: True if this was successful, False otherwise
        """
        # Acquiring the lock for the specific agent
        lock = self._find_generation_lock(agent_id=agent_id)
        last_context: AgentContext | None = None
        if agent_id in self._generation_context:
            last_context = self._generation_context[agent_id]

        if lock.acquire(blocking=False):
            if last_context is not None:
                last_context = AgentContext(last_context.last_idea)
            return AgentGenerationLock(agent_id=agent_id, lock=lock, context=last_context)
        else:
            return AgentGenerationLock(agent_id=agent_id)

    def release_contribution_lock(self, agent_id: uuid_pkg.uuid4, lock: threading.Lock):
        """ Only to be called from AgentLock.release() """
        if (agent_id in self._contribution_lock
                and lock == self._contribution_lock[agent_id]):
            lock.release()

    def release_generation_lock(self,
                                agent_id: uuid_pkg.uuid4,
                                lock: threading.Lock,
                                next_context: AgentContext | None = None):
        """ Only to be called from AgentLock.release() """
        if (agent_id in self._generation_locks
                and lock == self._generation_locks[agent_id]):
            self._last_generation[agent_id] = datetime.now(timezone.utc)

            if next_context is not None:
                self._generation_context[agent_id] = next_context

            lock.release()

    def last_generation_completed(self, agent_id: uuid_pkg.uuid4):
        """ returns the last time an agent completed a task or None if the agent
            has not completed a task yet
        """
        if agent_id in self._last_generation:
            return self._last_generation[agent_id]
        return None


agent_manager = AgentManager()
