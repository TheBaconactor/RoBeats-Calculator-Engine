# Analytical Gem Optimization Study

## Overview

This document summarizes the mathematical analysis and feasibility study of replacing the current iterative greedy gem allocation algorithm with a purely analytical (closed-form) solution. The goal was to determine if the same optimal allocation could be derived mathematically to reduce computational overhead in the Genetic Algorithm (GA) and Force Greats (FG) solvers.

## 1. Problem Statement

The gem allocation problem involves distributing a fixed budget of gems (typically 90) across four categories—Perfect Points (PP), Combo Multiplier (CM), Fever Multiplier (FM), and Elemental Overflow (OV)—to maximize the total score for a given gear loadout and fever timeline.

Because this optimization happens in the innermost loop of the GA (evaluating thousands of genomes per song) and the FG solver (evaluating thousands of timeline configurations), its efficiency is critical to overall system throughput.

## 2. Current Implementation: Greedy + Hints

The current system uses a highly optimized **Greedy Algorithm with Warm-Start Hints**.

### The Greedy Core
The `optimize_core_jit` (CPU) and `optimize_core_device` (GPU) functions iterate through the gem budget one gem at a time. At each step, they evaluate the score gain for all four options and pick the best one.

### The Hint System (Warm-Start)
To avoid the full 90-iteration search for every genome, the system uses a **Warm-Start Hint** mechanism:
- **Seed Allocation**: Genomes inherit the best gem allocation from their parents as a "hint".
- **Local Search Window**: Instead of starting from zero, the solver starts at the hint allocation and performs a local search within a small window (typically 5 searches).
- **Climbing Effect**: The allocation "climbs" toward the optimum across generations. For example, it might start at 3 gems, climb to 59, and maintain its 5-search window while still finding the optimal split due to diminishing returns at higher stat values.
- **Efficiency**: This reduces the computational cost from $O(\text{budget} \times 4)$ to $O(\text{window} \times 12)$, making it nearly as fast as an analytical solution.

## 3. Mathematical Analysis

The score function $S$ is defined as:

$$S = \text{head\_score} + \text{body\_score}$$

Where:
- $\text{body\_score} = N_{fever} \times \lfloor \text{base} \times CM \times FM \rfloor + N_{normal} \times \lfloor \text{base} \times CM \rfloor$
- $\text{base} = (2 \times P_{val} + S_{val}) + PP_{factor}(pp)$
- $CM, FM, PP_{factor}$ are derived from non-linear lookup tables (`Stats.txt`).

### Reference Table Structure
- **Perfect Points (PP)**: Uses a discrete lookup table where values only change at specific **breakpoints** (e.g., stat 158 and 159 might both result in a factor of 484).
- **CM / FM**: Use continuous multipliers that change at almost every stat point, though the marginal gain decreases as the stat increases.

## 4. Barriers to a Purely Analytical Solution

While a simplified version of this problem could be solved with calculus (Lagrange multipliers), several "real-world" factors in the game logic make an exact analytical match for the greedy algorithm extremely difficult:

### 4.1. The Fill Bonus Coupling
The `fill_bonus` calculation assumes that all *remaining* gems will be allocated to the Overflow (OV) color. This creates a non-separable dependency where the value of a choice at step $t$ depends on the total budget $R$.

### 4.2. Floor Operations (Discrete Jumps)
The use of `floor` (or `int` truncation) in the score formula means the objective function is piecewise-constant. Small changes in stats often result in zero score change until a boundary is crossed, creating "plateaus" that break standard gradient-based optimization.

### 4.3. PP Lookahead
The greedy algorithm includes a specific lookahead (up to 8 gems) to handle ties between PP and OV. It will "invest" in PP if it sees a strictly better score within the next 8 steps, even if the immediate step is a tie. This path-dependency is difficult to model in a closed-form equation.

### 4.4. Float32 Precision
To maintain parity with the GPU (Taichi/Vulkan), all math must use `float32` rounding. Analytical solutions using higher precision (`float64`) would frequently diverge from the greedy algorithm's results at integer boundaries.

## 5. Conclusion

The audit concludes that while a **near-optimal** analytical solution is possible, an **exact-parity** analytical solution that matches the greedy algorithm's output 100% of the time is likely more complex to implement and maintain than the current greedy system.

Furthermore, the **Warm-Start Hint system** already provides the performance benefits of an analytical approach. By restricting the search to a 5-window local climb, the system avoids redundant work and achieves high throughput while guaranteed to converge on the same "greedy-optimal" result that the game logic expects.

**Recommendation**: Retain the current Greedy + Hints architecture as it represents the most efficient balance between mathematical accuracy (parity) and computational speed.
