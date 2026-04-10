import asyncio
import hashlib
import logging
import random
import time
from dataclasses import asdict, dataclass
from functools import cached_property
from typing import Awaitable, Callable, Iterable

import redis.asyncio as redis

logger = logging.getLogger("coordinator")


@dataclass
class OwnershipClaimStats:
    """Statistics for ownership claiming operations."""

    claimed: int = 0
    released: int = 0
    failed_claims: int = 0
    expired_claims: int = 0
    stolen_by_others: int = 0


class OwnershipCoordinator:
    """
    Coordinates workload distribution using Redis distributed locks.

    Each replica claims ownership of specific remote instances by acquiring
    ownership in form of Redis records. Ensures even distribution through
    fair share limiting and deterministic preference ordering.

    Features:
    - **Strong consistency**: Ownership holder is the definitive owner
    - **Graceful handoff**: Instances released before replica shutdown
    - **Fair distribution**: Each replica claims at most ceil(K/R) instances
    - **Thundering herd prevention**: Random jitter on startup
    - **Deterministic preference**: Replicas prefer specific instances based on hash
    """

    # Redis keys and prefixes
    REPLICAS_KEY: str = "coord:replicas"
    "Sorted set of active replicas (score = timestamp)"
    HEARTBEAT_PREFIX: str = "coord:heartbeat"
    "Prefix for replicas heartbeat keys `{HEARTBEAT_PREFIX}:{replica_id}`"
    OWNERSHIP_PREFIX: str = "coord:ownership"
    "Prefix for instance ownership keys `{OWNERSHIP_PREFIX}:{instance_id}`, value = `replica_id`"
    REPLICAS_LOCK_KEY: str = "coord:lock:replicas"
    "Lock key for operations with replicas registry"
    INSTANCES_LOCK_PREFIX: str = "coord:lock:instances"
    "Prefix for lock key to manage instance ownership `{INSTANCES_LOCK_PREFIX}:{instance_id}`"

    # ─────────────────────────────────────────────────────────────────────────
    # Lifecycle
    # ─────────────────────────────────────────────────────────────────────────

    def __init__(self, replica_id: str, redis_client: redis.Redis) -> None:
        self.replica_id = replica_id
        self.redis: redis.Redis = redis_client

        # Internal state
        self._known_instances: set[str] = set()
        self._owned_instances: set[str] = set()
        self._others_instances: set[str] = set()
        self._known_replicas: set[str] = set()

        self._pref_scores_cache: dict[tuple[str, str], int] = {}
        self._natural_owner_cache: dict[str, str] = {}

        self._stats: OwnershipClaimStats = OwnershipClaimStats()

        # Background tasks
        self._heartbeat_task: asyncio.Task | None = None
        self._refresh_task: asyncio.Task | None = None
        self._rebalance_task: asyncio.Task | None = None

        # Callbacks
        self._on_acquired: list[Callable[[str], Awaitable[None]]] = list()
        self._on_released: list[Callable[[str], Awaitable[None]]] = list()

        # Timing configuration
        self.ownership_ttl: int = 30  # Ownership TTL in seconds
        self.refresh_interval: float = 10.0  # How often to refresh owned instances
        self.heartbeat_ttl: int = 15  # Heartbeat TTL in seconds
        self.heartbeat_interval: float = 5.0  # How often to send heartbeat
        self.rebalance_interval: float = 10.0  # How often to check for rebalance
        self.claim_jitter_max: float = 0.2  # Max random jitter before claiming

    async def start(self) -> None:
        """Start the coordinator and begin background tasks."""

        self._stats = OwnershipClaimStats()

        # Register this replica
        await self._register()

        # Start background tasks
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._refresh_task = asyncio.create_task(self._refresh_loop())
        self._rebalance_task = asyncio.create_task(self._rebalance_loop())

        logger.info(f"OwnershipCoordinator started: {self.replica_id}")

    async def stop(self) -> None:
        """Stop the coordinator, release all instances, and cleanup."""

        # Cancel background tasks
        for task in (self._heartbeat_task, self._refresh_task, self._rebalance_task):
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Release all instances gracefully
        await self._release_all_instances()

        # Deregister
        await self._deregister()

        logger.info(
            f"OwnershipCoordinator stopped: {self.replica_id} "
            f"(stats: claimed={self._stats.claimed}, released={self._stats.released})"
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    async def update_instances(self, instances: list[str]) -> None:
        """
        Update the set of instance_ids to coordinate.

        Call this when the set of remote instances changes. The coordinator will
        automatically rebalance ownership on the next rebalance cycle.

        Args:
            instances: Complete set of instance_ids that should be distributed
        """

        new = set(instances)
        added = new - self._known_instances
        removed = self._known_instances - new

        for instance_id in removed:
            if instance_id in self._owned_instances:
                await self._release_instance(instance_id)
            self._clear_preference_scores_cache(instance_id=instance_id)
            self._clear_natural_owner_cache(instance_id=instance_id)
            self._others_instances.discard(instance_id)

        if added or removed:
            self._clear_fair_share_cache()
            self._known_instances = new
            logger.info(
                f"Instances updated: +{len(added)} -{len(removed)} "
                f"(owned: {len(self._owned_instances)}, known: {len(self._known_instances)})"
            )

    def is_mine(self, instance_id: str) -> bool:
        """Check if this replica currently owns the given instance."""
        return instance_id in self._owned_instances

    def get_owned_instances(self) -> set[str]:
        """Get set of instance_ids currently owned by this replica."""
        return self._owned_instances.copy()

    def get_stats(self) -> OwnershipClaimStats:
        """Get claiming statistics."""
        return self._stats

    def on_acquired(self, callback: Callable[[str], Awaitable[None]]) -> None:
        """
        Register callback for when a instance is acquired.

        Callback receives the instance_id that was acquired.
        Use this to start processing for the instance (e.g., subscribe to relevant MQTT topic).
        """
        self._on_acquired.append(callback)

    def on_released(self, callback: Callable[[str], Awaitable[None]]) -> None:
        """
        Register callback for when a instance is released.

        Callback receives the instance_id that was released.
        Use this to stop processing for the instance (e.g., unsubscribe from relevant MQTT topic).
        """
        self._on_released.append(callback)

    async def force_rebalance(self) -> None:
        """Force an immediate rebalance check."""
        await self._rebalance()

    # ─────────────────────────────────────────────────────────────────────────
    # Preference Hash (Highest Random Weight)
    # ─────────────────────────────────────────────────────────────────────────

    def _preference_score(self, instance_id: str, replica_id: str) -> int:
        """
        Compute deterministic preference score for a (instance_id, replica_id) pair.

        Lower score = higher preference. All replicas compute identical scores,
        so they agree on the "natural" owner of each instance.

        This enables:
        - Stable assignments (same replica prefers same instances)
        - Faster convergence (replicas claim preferred instances first)
        - Predictable distribution after rebalance
        """
        combined = (instance_id, replica_id)
        if combined not in self._pref_scores_cache:
            digest = hashlib.md5(f"{instance_id}:{replica_id}".encode(), usedforsecurity=False).digest()
            self._pref_scores_cache[combined] = int.from_bytes(digest[:8])
        return self._pref_scores_cache[combined]

    def _clear_preference_scores_cache(self, instance_id: str | None = None, replica_id: str | None = None) -> None:
        if instance_id is None and replica_id is None:
            self._pref_scores_cache.clear()
            return

        if replica_id is None:
            key = instance_id
            index = 0
        else:
            key = replica_id
            index = 1

        for combined in set(self._pref_scores_cache):
            if combined[index] == key:
                del self._pref_scores_cache[combined]

    # HRW classic
    def _get_natural_owner(self, instance_id: str) -> str | None:
        """Compute which replica should naturally own this instance."""
        if not self._known_replicas:
            return None
        if instance_id not in self._natural_owner_cache:
            # Replica with highest score wins (deterministic across all replicas)
            self._natural_owner_cache[instance_id] = max(
                self._known_replicas,
                key=lambda r: self._preference_score(instance_id, r)
            )
        return self._natural_owner_cache[instance_id]

    def _clear_natural_owner_cache(self, instance_id: str | None = None, replica_id: str | None = None) -> None:
        if instance_id is None and replica_id is None:
            self._natural_owner_cache.clear()
            return

        if replica_id is None:
            if instance_id in self._natural_owner_cache:
                del self._natural_owner_cache[instance_id]

        else:
            for instance_id in set(self._natural_owner_cache):
                if self._natural_owner_cache[instance_id] == replica_id:
                    del self._natural_owner_cache[instance_id]

    def _get_preferred_instances(self, all_instances: set[str]) -> list[str]:
        """
        Get instances sorted by preference for a specific replica.

        Instances where this replica is the "natural owner" come first,
        followed by others sorted by preference score.
        """
        natural: list[str] = []
        others: list[str] = []

        for i_id in all_instances:
            if self._get_natural_owner(i_id) == self.replica_id:
                natural.append(i_id)
            else:
                others.append(i_id)

        # Sort each bucket by preference score (lower = more preferred)
        natural.sort(key=lambda i: self._preference_score(i, self.replica_id))
        others.sort(key=lambda i: self._preference_score(i, self.replica_id))

        return natural + others

    # HRW ranks
    # def _get_rank_for_instance(self, instance_id: str) -> int:
    #     """Get this replica's rank (0=best) for an instance among all replicas."""
    #     scores = [
    #         (self._preference_score(instance_id, r), r)
    #         for r in self._known_replicas
    #     ]
    #     scores.sort(reverse=True)  # highest score = rank 0
    #     for rank, (_, r) in enumerate(scores):
    #         if r == self.replica_id:
    #             return rank
    #     return len(scores)  # shouldn't happen

    # def _get_preferred_instances(self, all_instances: set[str]) -> list[str]:
    #     """Sort instances by our rank (lower rank = higher preference)."""
    #     return sorted(
    #         all_instances,
    #         key=lambda i: (
    #             self._get_rank_for_instance(i),
    #             self._preference_score(i, self.replica_id)  # tiebreaker within same rank
    #         )
    #     )

    # ─────────────────────────────────────────────────────────────────────────
    # Fair Share Limiting
    # ─────────────────────────────────────────────────────────────────────────

    @cached_property
    def _fair_share(self) -> int:
        """
        Compute the maximum number of instances this replica should own.

        All replicas get at least _known_instances // _known_replicas, and if there are
        any _known_instances % _known_replicas they will be given to the first several
        replicas (ordered by replica_id)
        """
        try:
            base, extras = divmod(len(self._known_instances), len(self._known_replicas))
        except ZeroDivisionError:
            logger.warning("Computing fair share without any known replicas")
            return 0
        if extras == 0:
            return base
        # Only first `extras` replicas (sorted by ID) get +1, so in the case of uneven distribution
        # (like 3 replicas and 10 instances) replicas will not try to claim excessive instances
        sorted_replicas = sorted(self._known_replicas)
        my_rank = sorted_replicas.index(self.replica_id)
        return base + (1 if my_rank < extras else 0)

    def _clear_fair_share_cache(self) -> None:
        try:
            del self._fair_share
        except AttributeError:
            pass

    def _should_release_excess(self) -> list[str]:
        """
        Determine which instances to release if we own more than fair share.

        Returns list of instance_ids to release (least preferred first).
        """
        excess = len(self._owned_instances) - self._fair_share
        if excess <= 0:
            return []

        # Most preferred instances are first
        owned_instances_by_preference = self._get_preferred_instances(self._owned_instances)
        # Thus taking items from the end
        return owned_instances_by_preference[-excess:]

    def _needs_to_claim(self) -> list[str]:
        """
        Determine which unclaimed instances this replica should try to claim.

        Returns instance_ids in preference order, limited to fair share.
        """
        can_claim = max(0, self._fair_share - len(self._owned_instances))
        if can_claim == 0:
            return []

        # Get unclaimed instances (not owned by us)
        unclaimed = self._known_instances - self._owned_instances - self._others_instances

        # Sort by our preference
        preferred = self._get_preferred_instances(unclaimed)

        return preferred[:can_claim]

    # ─────────────────────────────────────────────────────────────────────────
    # Replica Registry
    # ─────────────────────────────────────────────────────────────────────────

    async def _register(self) -> None:
        """Register this replica in the registry."""
        logger.debug(f"Starting replica registration: {self.replica_id}")
        await self._send_heartbeat(int(self.rebalance_interval * 2))
        await self.redis.zadd(self.REPLICAS_KEY, {self.replica_id: time.time()})
        self._known_replicas.add(self.replica_id)
        await asyncio.sleep(self.rebalance_interval)
        await self._sync_replicas()
        await self._send_heartbeat()
        await self._claim_all_instances()
        logger.debug(f"Registered replica: {self.replica_id}")

    async def _deregister(self) -> None:
        """Remove this replica from the registry."""
        await self.redis.zrem(self.REPLICAS_KEY, self.replica_id)
        heartbeat_key = f"{self.HEARTBEAT_PREFIX}:{self.replica_id}"
        await self.redis.delete(heartbeat_key)
        logger.debug(f"Deregistered replica: {self.replica_id}")

    async def _send_heartbeat(self, ttl: int | None = None) -> None:
        """Send heartbeat to indicate this replica is alive."""
        heartbeat_key = f"{self.HEARTBEAT_PREFIX}:{self.replica_id}"
        ex = self.heartbeat_ttl if ttl is None else ttl
        await self.redis.set(heartbeat_key, b"1", ex=ex)

    async def _sync_replicas(self) -> None:
        """Sync the list of active replicas from Redis."""

        async with self.redis.lock(
            self.REPLICAS_LOCK_KEY, timeout=self.rebalance_interval, raise_on_release_error=False
        ):
            # Get all registered replicas
            registered = await self.redis.zrange(self.REPLICAS_KEY, 0, -1)
            registered_ids: set[str] = {r.decode() for r in registered}

            # Filter to those with valid heartbeats
            alive: set[str] = set()
            stale: set[str] = set()

            for replica_id in registered_ids:
                heartbeat_key = f"{self.HEARTBEAT_PREFIX}:{replica_id}"
                if await self.redis.exists(heartbeat_key):
                    alive.add(replica_id)
                else:
                    stale.add(replica_id)

            # Clean up stale entries
            if stale:
                await self.redis.zrem(self.REPLICAS_KEY, *stale)
                logger.info(f"Removed stale replicas from Redis: {stale}")
            else:
                logger.debug("No stale replicas to remove from Redis")

        if alive != self._known_replicas:
            joined = alive - self._known_replicas
            left = self._known_replicas - alive
            for replica_id in left:
                self._clear_preference_scores_cache(replica_id=replica_id)
            self._clear_natural_owner_cache()
            self._clear_fair_share_cache()
            self._others_instances.clear()
            self._known_replicas = alive
            logger.info(f"Actualized known replicas set: +{joined} -{left} ={alive}")
        else:
            logger.debug("No changes in known replicas set")

    # ─────────────────────────────────────────────────────────────────────────
    # Ownership Operations
    # ─────────────────────────────────────────────────────────────────────────

    async def _try_claim_instance(self, instance_id: str, steal: bool = False) -> bool:
        """
        Try to acquire ownership (redis key) for a instance_id.

        Uses SET NX (set if not exists) for atomic acquisition.

        Returns:
            True if acquired, False if already held by another replica
        """

        lock_key = f"{self.INSTANCES_LOCK_PREFIX}:{instance_id}"
        async with self.redis.lock(lock_key, timeout=self.ownership_ttl, raise_on_release_error=False):

            ownership_key = f"{self.OWNERSHIP_PREFIX}:{instance_id}"

            # SET key value NX EX ttl - atomic acquire
            acquired = await self.redis.set(
                ownership_key, self.replica_id, nx=(not steal), ex=self.ownership_ttl
            )

            if acquired:
                self._owned_instances.add(instance_id)
                self._stats.claimed += 1
                claim_type = " (forced)" if steal else ""
                logger.debug(f"Claimed ownership of {instance_id}{claim_type}")
                await self._notify_acquired(instance_id)
            else:
                self._others_instances.add(instance_id)
                self._stats.failed_claims += 1
                logger.warning(f"Failed to claim ownership of {instance_id}")

        return acquired

    async def _release_instance(self, instance_id: str) -> bool:
        """
        Release ownership for a instance_id.

        Only releases if we're the current owner.

        Returns:
            True if released, False if we weren't the owner
        """

        lock_key = f"{self.INSTANCES_LOCK_PREFIX}:{instance_id}"
        async with self.redis.lock(lock_key, timeout=self.ownership_ttl, raise_on_release_error=False):

            ownership_key = f"{self.OWNERSHIP_PREFIX}:{instance_id}"

            owner = await self.redis.get(ownership_key)
            if owner is None or owner.decode() != self.replica_id:
                released = False
            else:
                await self.redis.delete(ownership_key)
                released = True

            self._owned_instances.discard(instance_id)
            if released:
                self._stats.released += 1
                logger.debug(f"Released ownership of {instance_id}")
            elif owner is None:
                self._stats.expired_claims += 1
                logger.warning(f"Released ownership of expired {instance_id}")
            else:
                self._others_instances.add(instance_id)
                self._stats.stolen_by_others += 1
                logger.warning(f"Released ownership of stolen {instance_id}")
            await self._notify_released(instance_id)

        return released

    async def _refresh_instance(self, instance_id: str) -> bool:
        """
        Refresh ownership TTL.

        Returns:
            True if refreshed, False if ownership was stolen/expired
        """

        lock_key = f"{self.INSTANCES_LOCK_PREFIX}:{instance_id}"
        async with self.redis.lock(lock_key, timeout=self.ownership_ttl, raise_on_release_error=False):

            ownership_key = f"{self.OWNERSHIP_PREFIX}:{instance_id}"

            owner = await self.redis.get(ownership_key)
            if owner is None or owner.decode() != self.replica_id:
                refreshed = False
            else:
                await self.redis.expire(ownership_key, self.ownership_ttl)
                refreshed = True

            if refreshed:
                logger.debug(f"Refreshed ownership of {instance_id}")
            else:
                # Ownership was stolen or expired
                self._owned_instances.discard(instance_id)
                if owner is None:
                    # FIXME: falsely detects released instance as expired
                    self._stats.expired_claims += 1
                    logger.warning(f"Ownership of {instance_id} was expired")
                else:
                    self._others_instances.add(instance_id)
                    self._stats.stolen_by_others += 1
                    logger.warning(f"Ownership of {instance_id} was stolen")
                await self._notify_released(instance_id)

        return refreshed

    async def _claim_all_instances(self) -> None:
        """Claim all ownerships of this replica.

        TODO: implemantation with bulk operations (like mget) and/or pipelines
        """
        instances_to_claim = self._needs_to_claim()
        logger.info(f"Trying to initially claim instances: {len(instances_to_claim)}")
        for instance_id in instances_to_claim:
            # Random jitter to avoid thundering herd
            jitter = random.uniform(0, self.claim_jitter_max)
            await asyncio.sleep(jitter)
            await self._try_claim_instance(instance_id)

    async def _release_all_instances(self) -> None:
        """Release all ownerships of this replica.

        TODO: implemantation with bulk operations (like mget) and/or pipelines
        """
        logger.info(f"Releasing all claimed instances: {len(self._owned_instances)}")
        for instance_id in list(self._owned_instances):
            await self._release_instance(instance_id)

    async def _get_current_owners(self, instance_ids: Iterable[str]) -> list[str | None]:
        """Get the current owners of instances."""
        ownership_keys = [f"{self.OWNERSHIP_PREFIX}:{i_id}" for i_id in instance_ids]
        owners_bytes = await self.redis.mget(ownership_keys)
        owners = [o if o is None else o.decode() for o in owners_bytes]
        return owners

    async def _rebalance(self) -> None:
        """
        Perform rebalancing:
        1. Sync replica list
        2. Release excess instances (if over fair share)
        3. Claim unclaimed instances (up to fair share)

        TODO: implemantation with bulk operations (like mget) and/or pipelines
        """

        # Step 1: Release excess keys if we have more than fair share
        await self._sync_replicas()

        # Step 2: Release excess keys if we have more than fair share
        excess_instances = self._should_release_excess()
        if excess_instances:
            logger.info(f"Releasing excess instances: {len(excess_instances)}")
            for instance_id in excess_instances:
                await self._release_instance(instance_id)
        else:
            logger.debug("No excess instances to release")

        # Step 3: Claim unclaimed instances up to fair share
        # FIXME: break in cycle instead of slicing in _needs_to_claim
        instances_to_claim = self._needs_to_claim()
        if not instances_to_claim and self._fair_share > len(self._owned_instances):
            logger.warning(
                f"No instances to claim, but fair share is not filled "
                f"({len(self._owned_instances)}/{self._fair_share})"
            )
            if len(self._others_instances):
                logger.warning(f"Retrying instances of other replicas: {len(self._others_instances)}")
                self._others_instances.clear()
                instances_to_claim = self._needs_to_claim()
            else:
                logger.error(
                    f"Not enough instances to fill the fair share "
                    f"({len(self._owned_instances)}/{self._fair_share})"
                )
        if instances_to_claim:
            logger.info(f"Trying to claim instances: {instances_to_claim}")
            for instance_id in instances_to_claim:
                await self._try_claim_instance(instance_id)
        else:
            logger.debug("No instances to claim")

        logger.debug(
            f"Rebalance complete: instances={len(self._owned_instances)}/{len(self._known_instances)} "
            f"(owned/known), fair_share={self._fair_share}, replicas={len(self._known_replicas)}"
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Background Loops
    # ─────────────────────────────────────────────────────────────────────────

    async def _heartbeat_loop(self) -> None:
        """Periodically send heartbeats."""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                logger.debug(f"Sending replica heartbeat: {self.replica_id}")
                await self._send_heartbeat()
            except asyncio.CancelledError:
                logger.debug("Heartbeat loop cancelled")
                raise
            except Exception:
                logger.exception("Error within heartbeat loop")

    async def _refresh_loop(self) -> None:
        """Periodically refresh owned instances."""
        while True:
            try:
                await asyncio.sleep(self.refresh_interval)
                if self._owned_instances:
                    logger.debug(f"Refreshing owned instances: {len(self._owned_instances)}")
                    for instance_id in list(self._owned_instances):
                        await self._refresh_instance(instance_id)
                else:
                    log_method = logger.warning
                    if len(self._known_instances):
                        log_method = logger.error
                    log_method(
                        f"Doesn't have any owned instances to refresh, "
                        f"total known instances: {len(self._known_instances)}"
                    )
            except asyncio.CancelledError:
                logger.debug("Refresh loop cancelled")
                raise
            except Exception:
                logger.exception("Error within refresh loop")

    async def _rebalance_loop(self) -> None:
        """Periodically check and rebalance instances ownership."""
        while True:
            try:
                await asyncio.sleep(self.rebalance_interval)
                logger.debug("Checking for periodic rebalance")
                await self._rebalance()
            except asyncio.CancelledError:
                logger.debug("Rebalance loop cancelled")
                raise
            except Exception:
                logger.exception("Error within rebalance loop")

    # ─────────────────────────────────────────────────────────────────────────
    # Callbacks
    # ─────────────────────────────────────────────────────────────────────────

    async def _notify_acquired(self, instance_id: str) -> None:
        """Notify all registered callbacks that an instance was acquired."""
        for callback in self._on_acquired:
            try:
                await callback(instance_id)
            except Exception:
                logger.exception(f"Error in on_acquired callback for {instance_id}")

    async def _notify_released(self, instance_id: str) -> None:
        """Notify all registered callbacks that an instance was released."""
        for callback in self._on_released:
            try:
                await callback(instance_id)
            except Exception:
                logger.exception(f"Error in on_released callback for {instance_id}")

    # ─────────────────────────────────────────────────────────────────────────
    # Utility
    # ─────────────────────────────────────────────────────────────────────────

    def get_distribution_stats(self) -> dict[str, int]:
        """Get current distribution of instances across replicas."""
        # For synchronous access, just return what we know locally
        result = {
            "known_replicas": len(self._known_replicas),
            "known_instances": len(self._known_instances),
            "fair_share": self._fair_share,
            "owned_instances": len(self._owned_instances),
            "others_instances": len(self._others_instances),
        }
        result.update(asdict(self._stats))
        return result

    async def get_full_distribution(self) -> dict[str | None, list[str]]:
        """
        Get full distribution by querying all ownerships from Redis.

        Returns dict mapping replica_id to list of owned instance_ids.
        """
        distribution: dict[str | None, list[str]] = {}
        known_instances_sorted = sorted(self._known_instances)
        owners = await self._get_current_owners(known_instances_sorted)
        for inst, owner in zip(known_instances_sorted, owners):
            if owner not in distribution:
                distribution[owner] = []
            distribution[owner].append(inst)
        return distribution
