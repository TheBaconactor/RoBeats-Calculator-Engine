"""
Item Registry - GPU-optimized item encoding for GPU-native GA.

This module provides the ItemRegistry class which:
1. Assigns contiguous integer IDs to items per slot
2. Encodes/decodes genomes between dict-based and ID-based representations
3. Provides GPU-friendly arrays for item stats and slot pools
"""

import numpy as np
from typing import Optional


# Stat dimension indices (matching fields.ITEM_STAT_DIM = 10)
STAT_INDICES = {
    "Perfect Points": 0,
    "Combo Multiplier": 1,
    "Fever Multiplier": 2,
    "Fever Time": 3,
    "Fever Fill Rate": 4,
    "Beat": 5,
    "Vibe": 6,
    "Rush": 7,
    "Flow": 8,
    "Chill": 9,
}

# Slot configuration (6 gear + 3 mini = 9 total)
NUM_GEAR_SLOTS = 6
NUM_MINI_SLOTS = 3
MINI_SLOT_INDICES = [6, 7, 8]  # Minis occupy slots 6, 7, 8


class ItemRegistry:
    """
    GPU-optimized item encoding for a specific song/pool combination.
    
    Assigns contiguous integer IDs to items per slot:
      - ID 0 is reserved (empty/invalid)
      - Gear slots 0-5: each has its own ID range
      - Mini slots 6-8: share the same pool (minis are interchangeable)
    
    This allows GPU mutation to sample from slot pools using simple
    modular arithmetic: new_id = slot_start[slot] + (rand % slot_count[slot])
    """
    
    def __init__(
        self,
        gear_pool: dict[str, list[dict]],
        mini_pool: list[dict],
        slots: list[str],
        fixed_gear: Optional[list[dict]] = None,
        fixed_minis: Optional[list[dict]] = None,
    ):
        """
        Build item registry from gear and mini pools.
        
        Args:
            gear_pool: Dict mapping slot name -> list of gear items
            mini_pool: List of mini items (shared across slots 6-8)
            slots: List of gear slot names (e.g., ["Arms", "BackBling", ...])
            fixed_gear: If provided, only these gear items are valid (for fixed slots)
            fixed_minis: If provided, only these minis are valid (for fixed slots)
        """
        self.slots = list(slots)
        self.n_slots = len(slots) + 3  # 6 gear + 3 mini = 9 total
        
        # Mappings
        self.id_to_item: dict[int, dict] = {0: {}}  # ID 0 = empty
        self.item_to_id: dict[tuple[int, str], int] = {}  # (slot_idx, name) -> id
        
        # Per-slot pool boundaries
        self.slot_start = [0] * 9  # First valid ID for each slot
        self.slot_count = [0] * 9  # Number of items in each slot
        
        # Build registry
        next_id = 1  # Start from 1 (0 is reserved)
        
        # Process gear slots (0-5)
        for slot_idx, slot_name in enumerate(slots):
            items = gear_pool.get(slot_name, [])
            
            # If fixed_gear provided, only include that item
            if fixed_gear is not None and slot_idx < len(fixed_gear):
                fixed_item = fixed_gear[slot_idx]
                if fixed_item and fixed_item.get("Name"):
                    items = [fixed_item]
            
            self.slot_start[slot_idx] = next_id
            self.slot_count[slot_idx] = len(items)
            
            for item in items:
                name = item.get("Name", "")
                if not name:
                    continue
                    
                item_id = next_id
                next_id += 1
                
                self.id_to_item[item_id] = item
                self.item_to_id[(slot_idx, name)] = item_id
        
        # Process mini slots (6-8) - they share the same pool
        mini_items = mini_pool
        if fixed_minis is not None:
            # Only use fixed minis
            mini_items = [m for m in fixed_minis if m and m.get("Name")]
        
        mini_start = next_id
        mini_count = len(mini_items)
        
        for item in mini_items:
            name = item.get("Name", "")
            if not name:
                continue
                
            item_id = next_id
            next_id += 1
            
            self.id_to_item[item_id] = item
            # Register for all mini slots (6, 7, 8)
            for mini_slot in MINI_SLOT_INDICES:
                self.item_to_id[(mini_slot, name)] = item_id
        
        # Set mini slot boundaries (all share same pool)
        for mini_slot in MINI_SLOT_INDICES:
            self.slot_start[mini_slot] = mini_start
            self.slot_count[mini_slot] = mini_count
        
        self.n_items = next_id  # Total items including reserved ID 0
    
    def encode_genome(self, genome: list[dict]) -> np.ndarray:
        """
        Convert a genome (list of item dicts) to an array of item IDs.
        
        Args:
            genome: List of 9 item dicts (6 gear + 3 mini)
            
        Returns:
            np.ndarray: (9,) int32 array of item IDs
        """
        ids = np.zeros(9, dtype=np.int32)
        
        for slot_idx, item in enumerate(genome[:9]):
            if not item:
                ids[slot_idx] = 0
                continue
                
            name = item.get("Name", "") if isinstance(item, dict) else str(item)
            key = (slot_idx, name)
            
            if key in self.item_to_id:
                ids[slot_idx] = self.item_to_id[key]
            else:
                # Item not in registry - use ID 0 (empty)
                ids[slot_idx] = 0
        
        return ids
    
    def decode_genome(self, ids: np.ndarray) -> list[dict]:
        """
        Convert an array of item IDs back to a genome (list of item dicts).
        
        Args:
            ids: (9,) array of item IDs
            
        Returns:
            list[dict]: List of 9 item dicts
        """
        genome = []
        for item_id in ids[:9]:
            item_id = int(item_id)
            if item_id in self.id_to_item:
                genome.append(self.id_to_item[item_id])
            else:
                genome.append({})
        return genome
    
    def to_gpu_arrays(self) -> dict[str, np.ndarray]:
        """
        Return numpy arrays for GPU upload.
        
        Returns:
            dict with keys:
                - "item_stats": (n_items, 10) int32 - stats per item
                - "slot_start": (9,) int32 - first ID per slot
                - "slot_count": (9,) int32 - count per slot
        """
        # Build item_stats array
        item_stats = np.zeros((self.n_items, 10), dtype=np.int32)
        
        for item_id, item in self.id_to_item.items():
            if item_id == 0 or not item:
                continue
            
            for stat_name, stat_idx in STAT_INDICES.items():
                value = item.get(stat_name, 0)
                if value:
                    item_stats[item_id, stat_idx] = int(value)
        
        return {
            "item_stats": item_stats,
            "slot_start": np.array(self.slot_start, dtype=np.int32),
            "slot_count": np.array(self.slot_count, dtype=np.int32),
        }
    
    def encode_population(self, population: list[list[dict]]) -> np.ndarray:
        """
        Encode an entire population of genomes.
        
        Args:
            population: List of genomes (each genome is list of 9 item dicts)
            
        Returns:
            np.ndarray: (n_genomes, 9) int32 array of item IDs
        """
        n_genomes = len(population)
        ids = np.zeros((n_genomes, 9), dtype=np.int32)
        
        for i, genome in enumerate(population):
            ids[i] = self.encode_genome(genome)
        
        return ids
    
    def decode_population(self, ids: np.ndarray) -> list[list[dict]]:
        """
        Decode an entire population of ID arrays to genomes.
        
        Args:
            ids: (n_genomes, 9) array of item IDs
            
        Returns:
            List of genomes (each genome is list of 9 item dicts)
        """
        return [self.decode_genome(row) for row in ids]
    
    def get_stats_summary(self) -> str:
        """Return a summary string for debugging."""
        lines = [f"ItemRegistry: {self.n_items} items total"]
        for slot_idx in range(9):
            if slot_idx < len(self.slots):
                slot_name = self.slots[slot_idx]
            else:
                slot_name = f"Mini{slot_idx - NUM_GEAR_SLOTS + 1}"
            lines.append(
                f"  Slot {slot_idx} ({slot_name}): "
                f"start={self.slot_start[slot_idx]}, count={self.slot_count[slot_idx]}"
            )
        return "\n".join(lines)
