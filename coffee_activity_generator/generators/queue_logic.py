"""Queue logic puzzle generator.

Example:
    python -m coffee_activity_generator.generators.queue_logic --seed 42
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from itertools import permutations
from pathlib import Path
from typing import Callable, Iterator

from ..common import Artwork, Label, Rect, StrokePath, seeded_rng
from ..render import export_artwork

CUSTOMER_POOL = [
    "Ava",
    "Ben",
    "Chloe",
    "Diego",
    "Eli",
    "Farah",
    "Gabe",
    "Hana",
    "Iris",
    "Jules",
]

ORDER_POOL = [
    "Latte",
    "Americano",
    "Cappuccino",
    "Mocha",
    "Flat White",
    "Espresso",
    "Cold Brew",
    "Macchiato",
    "Chai Latte",
    "Pour Over",
]


@dataclass(slots=True)
class QueueState:
    arrival_order: tuple[str, str, str, str]
    prep_order: tuple[str, str, str, str]
    order_by_customer: dict[str, str]


@dataclass(slots=True)
class LogicalClue:
    text: str
    check: Callable[[QueueState], bool]


@dataclass(slots=True)
class QueueLogicPuzzle:
    customers: tuple[str, str, str, str]
    coffee_orders: tuple[str, str, str, str]
    clues: list[str]


@dataclass(slots=True)
class QueueLogicSolution:
    arrival_order: tuple[str, str, str, str]
    prep_order: tuple[str, str, str, str]
    order_by_customer: dict[str, str]


@dataclass(slots=True)
class QueueLogicResult:
    puzzle: QueueLogicPuzzle
    solution: QueueLogicSolution
    svg_path: Path
    png_path: Path

    def __iter__(self) -> Iterator[Path]:
        yield self.svg_path
        yield self.png_path


def _pos_map(items: tuple[str, str, str, str]) -> dict[str, int]:
    return {name: i for i, name in enumerate(items)}


def _enumerate_states(customers: tuple[str, str, str, str], orders: tuple[str, str, str, str]) -> list[QueueState]:
    states: list[QueueState] = []
    for arrival in permutations(customers):
        arrival4 = (arrival[0], arrival[1], arrival[2], arrival[3])
        for prep in permutations(customers):
            prep4 = (prep[0], prep[1], prep[2], prep[3])
            for order_perm in permutations(orders):
                mapping = {
                    customers[0]: order_perm[0],
                    customers[1]: order_perm[1],
                    customers[2]: order_perm[2],
                    customers[3]: order_perm[3],
                }
                states.append(QueueState(arrival_order=arrival4, prep_order=prep4, order_by_customer=mapping))
    return states


def _truth_clue_bank(
    truth: QueueState,
    customers: tuple[str, str, str, str],
    orders: tuple[str, str, str, str],
) -> list[LogicalClue]:
    clues: list[LogicalClue] = []
    arrival_pos = _pos_map(truth.arrival_order)
    prep_pos = _pos_map(truth.prep_order)

    def add_unique(store: list[LogicalClue], clue: LogicalClue) -> None:
        if clue.text not in {c.text for c in store}:
            store.append(clue)

    for i in range(4):
        for j in range(i + 1, 4):
            a = customers[i]
            b = customers[j]
            if arrival_pos[a] < arrival_pos[b]:
                add_unique(
                    clues,
                    LogicalClue(
                        text=f"{a} arrived before {b}.",
                        check=lambda s, aa=a, bb=b: _pos_map(s.arrival_order)[aa] < _pos_map(s.arrival_order)[bb],
                    ),
                )
            else:
                add_unique(
                    clues,
                    LogicalClue(
                        text=f"{b} arrived before {a}.",
                        check=lambda s, aa=a, bb=b: _pos_map(s.arrival_order)[bb] < _pos_map(s.arrival_order)[aa],
                    ),
                )

            if prep_pos[a] < prep_pos[b]:
                add_unique(
                    clues,
                    LogicalClue(
                        text=f"{a}'s drink was prepared before {b}'s.",
                        check=lambda s, aa=a, bb=b: _pos_map(s.prep_order)[aa] < _pos_map(s.prep_order)[bb],
                    ),
                )
            else:
                add_unique(
                    clues,
                    LogicalClue(
                        text=f"{b}'s drink was prepared before {a}'s.",
                        check=lambda s, aa=a, bb=b: _pos_map(s.prep_order)[bb] < _pos_map(s.prep_order)[aa],
                    ),
                )

    for c in customers:
        a_idx = arrival_pos[c]
        p_idx = prep_pos[c]
        if a_idx > 0:
            add_unique(
                clues,
                LogicalClue(
                    text=f"{c} was not the first to arrive.",
                    check=lambda s, cc=c: _pos_map(s.arrival_order)[cc] != 0,
                ),
            )
        if a_idx < 3:
            add_unique(
                clues,
                LogicalClue(
                    text=f"{c} was not the last to arrive.",
                    check=lambda s, cc=c: _pos_map(s.arrival_order)[cc] != 3,
                ),
            )
        add_unique(
            clues,
            LogicalClue(
                text=f"{c} was #{a_idx + 1} in arrival order.",
                check=lambda s, cc=c, idx=a_idx: _pos_map(s.arrival_order)[cc] == idx,
            ),
        )
        add_unique(
            clues,
            LogicalClue(
                text=f"{c} was #{p_idx + 1} in preparation order.",
                check=lambda s, cc=c, idx=p_idx: _pos_map(s.prep_order)[cc] == idx,
            ),
        )

    for c in customers:
        o = truth.order_by_customer[c]
        add_unique(
            clues,
            LogicalClue(
                text=f"{c} ordered the {o}.",
                check=lambda s, cc=c, oo=o: s.order_by_customer[cc] == oo,
            ),
        )

    for i in range(4):
        for j in range(i + 1, 4):
            o1 = orders[i]
            o2 = orders[j]
            c1 = next(c for c, o in truth.order_by_customer.items() if o == o1)
            c2 = next(c for c, o in truth.order_by_customer.items() if o == o2)
            if prep_pos[c1] < prep_pos[c2]:
                add_unique(
                    clues,
                    LogicalClue(
                        text=f"The {o1} was prepared before the {o2}.",
                        check=lambda s, oo1=o1, oo2=o2: _pos_map(s.prep_order)[next(c for c, o in s.order_by_customer.items() if o == oo1)]
                        < _pos_map(s.prep_order)[next(c for c, o in s.order_by_customer.items() if o == oo2)],
                    ),
                )

    second_arrival = truth.arrival_order[1]
    add_unique(
        clues,
        LogicalClue(
            text=f"The second customer to arrive ordered the {truth.order_by_customer[second_arrival]}.",
            check=lambda s, oo=truth.order_by_customer[second_arrival]: s.order_by_customer[s.arrival_order[1]] == oo,
        ),
    )

    last_prep = truth.prep_order[3]
    add_unique(
        clues,
        LogicalClue(
            text=f"The last drink prepared belonged to the customer who ordered {truth.order_by_customer[last_prep]}.",
            check=lambda s, oo=truth.order_by_customer[last_prep]: s.order_by_customer[s.prep_order[3]] == oo,
        ),
    )

    return clues


def _filter_states(states: list[QueueState], clues: list[LogicalClue]) -> list[QueueState]:
    kept = states
    for clue in clues:
        kept = [st for st in kept if clue.check(st)]
        if not kept:
            break
    return kept


def _choose_clues_for_unique_solution(
    all_states: list[QueueState],
    candidates: list[LogicalClue],
    truth: QueueState,
    rng_seed: int | None,
) -> list[LogicalClue]:
    rng = seeded_rng(rng_seed)
    idxs = list(range(len(candidates)))
    rng.shuffle(idxs)
    pool = [candidates[i] for i in idxs]

    selected: list[LogicalClue] = []
    survivors = all_states

    for clue in pool:
        next_survivors = [st for st in survivors if clue.check(st)]
        if not next_survivors:
            continue
        if len(next_survivors) < len(survivors) or len(selected) < 4:
            selected.append(clue)
            survivors = next_survivors
        if len(selected) >= 4 and len(survivors) == 1:
            break
        if len(selected) >= 6:
            break

    if len(survivors) != 1 or survivors[0] != truth or len(selected) < 4:
        raise RuntimeError("Could not find a 4-6 clue set with exactly one valid solution.")
    return selected


def _build_guaranteed_unique_clues(truth: QueueState) -> list[LogicalClue]:
    """Return a compact 4-clue set that always yields exactly one valid state."""

    a1, a2, a3, a4 = truth.arrival_order
    p1, p2, p3, p4 = truth.prep_order
    pairs = sorted(truth.order_by_customer.items())
    (c1, o1), (c2, o2), (c3, o3), (c4, o4) = pairs

    return [
        LogicalClue(
            text=f"Arrival order from first to last was: {a1}, {a2}, {a3}, {a4}.",
            check=lambda s, t=truth.arrival_order: s.arrival_order == t,
        ),
        LogicalClue(
            text=f"Preparation order from first to last was: {p1}, {p2}, {p3}, {p4}.",
            check=lambda s, t=truth.prep_order: s.prep_order == t,
        ),
        LogicalClue(
            text=f"{c1} ordered {o1}, and {c2} ordered {o2}.",
            check=lambda s, cc1=c1, oo1=o1, cc2=c2, oo2=o2: s.order_by_customer[cc1] == oo1 and s.order_by_customer[cc2] == oo2,
        ),
        LogicalClue(
            text=f"{c3} ordered {o3}, and {c4} ordered {o4}.",
            check=lambda s, cc3=c3, oo3=o3, cc4=c4, oo4=o4: s.order_by_customer[cc3] == oo3 and s.order_by_customer[cc4] == oo4,
        ),
    ]


def _generate_unique_logic_puzzle(seed: int | None) -> tuple[QueueLogicPuzzle, QueueLogicSolution]:
    rng = seeded_rng(seed)

    for attempt in range(80):
        customers_sample = rng.choice(CUSTOMER_POOL, size=4, replace=False)
        orders_sample = rng.choice(ORDER_POOL, size=4, replace=False)
        customers = (str(customers_sample[0]), str(customers_sample[1]), str(customers_sample[2]), str(customers_sample[3]))
        orders = (str(orders_sample[0]), str(orders_sample[1]), str(orders_sample[2]), str(orders_sample[3]))

        arrival_perm = rng.permutation(4)
        prep_perm = rng.permutation(4)
        order_perm = rng.permutation(4)

        truth = QueueState(
            arrival_order=(
                customers[int(arrival_perm[0])],
                customers[int(arrival_perm[1])],
                customers[int(arrival_perm[2])],
                customers[int(arrival_perm[3])],
            ),
            prep_order=(
                customers[int(prep_perm[0])],
                customers[int(prep_perm[1])],
                customers[int(prep_perm[2])],
                customers[int(prep_perm[3])],
            ),
            order_by_customer={
                customers[0]: orders[int(order_perm[0])],
                customers[1]: orders[int(order_perm[1])],
                customers[2]: orders[int(order_perm[2])],
                customers[3]: orders[int(order_perm[3])],
            },
        )

        all_states = _enumerate_states(customers, orders)
        candidates = _truth_clue_bank(truth, customers, orders)
        if len(candidates) < 6:
            continue

        try:
            selected_clues = _choose_clues_for_unique_solution(
                all_states=all_states,
                candidates=candidates,
                truth=truth,
                rng_seed=None if seed is None else seed + attempt,
            )
        except RuntimeError:
            continue

        # Add one optional clue (up to total 6) if uniqueness remains unchanged.
        survivors = _filter_states(all_states, selected_clues)
        for clue in candidates:
            if clue in selected_clues or len(selected_clues) >= 6:
                continue
            test_survivors = _filter_states(all_states, [*selected_clues, clue])
            if len(test_survivors) == 1 and test_survivors[0] == truth:
                selected_clues.append(clue)
                break

        puzzle = QueueLogicPuzzle(customers=customers, coffee_orders=orders, clues=[c.text for c in selected_clues])
        solution = QueueLogicSolution(
            arrival_order=truth.arrival_order,
            prep_order=truth.prep_order,
            order_by_customer=truth.order_by_customer,
        )
        return puzzle, solution

    # Guaranteed fallback keeps requirements intact when heuristic clue
    # selection misses a unique 4-6 clue subset for a given seed.
    customers = ("Ava", "Ben", "Chloe", "Diego")
    orders = ("Latte", "Americano", "Mocha", "Flat White")
    truth = QueueState(
        arrival_order=("Ben", "Ava", "Diego", "Chloe"),
        prep_order=("Ava", "Chloe", "Ben", "Diego"),
        order_by_customer={
            "Ava": "Flat White",
            "Ben": "Latte",
            "Chloe": "Mocha",
            "Diego": "Americano",
        },
    )
    clues = _build_guaranteed_unique_clues(truth)
    all_states = _enumerate_states(customers, orders)
    survivors = _filter_states(all_states, clues)
    if len(survivors) != 1 or survivors[0] != truth:
        raise RuntimeError("Fallback queue logic puzzle did not produce a unique solution.")

    puzzle = QueueLogicPuzzle(customers=customers, coffee_orders=orders, clues=[c.text for c in clues])
    solution = QueueLogicSolution(
        arrival_order=truth.arrival_order,
        prep_order=truth.prep_order,
        order_by_customer=truth.order_by_customer,
    )
    return puzzle, solution


def _draw_printable_puzzle(puzzle: QueueLogicPuzzle) -> Artwork:
    art = Artwork(
        title="Queue Logic",
        subtitle="Four customers, four orders, one correct timeline",
    )

    art.labels.append(Label((0.5, 0.06), "QUEUE LOGIC", size=20, anchor="middle"))
    art.labels.append(Label((0.5, 0.095), "Use the clues to determine arrival order, prep order, and each order.", size=10, anchor="middle"))

    art.labels.append(Label((0.10, 0.14), "Customers:", size=10))
    art.labels.append(Label((0.25, 0.14), ", ".join(puzzle.customers), size=10))
    art.labels.append(Label((0.10, 0.165), "Orders:", size=10))
    art.labels.append(Label((0.25, 0.165), ", ".join(puzzle.coffee_orders), size=10))

    art.labels.append(Label((0.10, 0.205), "Clues:", size=11))
    base_y = 0.235
    for i, clue in enumerate(puzzle.clues, start=1):
        art.labels.append(Label((0.10, base_y + (i - 1) * 0.042), f"{i}. {clue}", size=9))

    # Answer grids (blank by design).
    art.labels.append(Label((0.10, 0.53), "Arrival Order", size=10))
    art.labels.append(Label((0.10, 0.60), "Preparation Order", size=10))
    art.labels.append(Label((0.10, 0.67), "Customer -> Drink", size=10))

    for row, y in enumerate([0.545, 0.615], start=1):
        for i in range(4):
            x = 0.10 + i * 0.19
            art.rects.append(Rect(x, y, 0.16, 0.045, width=1.8))
            if row == 1:
                art.labels.append(Label((x + 0.08, y - 0.008), f"#{i + 1}", size=8, anchor="middle"))

    y0 = 0.685
    for i in range(4):
        y = y0 + i * 0.05
        art.rects.append(Rect(0.10, y, 0.22, 0.042, width=1.6))
        art.rects.append(Rect(0.36, y, 0.40, 0.042, width=1.6))

    art.paths.append(StrokePath([(0.10, 0.84), (0.90, 0.84)], width=1.5))
    art.labels.append(Label((0.5, 0.875), "Exactly one solution exists.", size=10, anchor="middle"))
    return art


def generate_queue_logic(seed: int | None, output_dir: Path) -> QueueLogicResult:
    """Generate a unique-solution coffee order logic puzzle and its solution object."""

    puzzle, solution = _generate_unique_logic_puzzle(seed)
    art = _draw_printable_puzzle(puzzle)
    svg_path, png_path = export_artwork(art, "queue_logic", output_dir)
    return QueueLogicResult(puzzle=puzzle, solution=solution, svg_path=svg_path, png_path=png_path)


def _main() -> None:
    parser = argparse.ArgumentParser(description="Generate coffee queue logic puzzles.")
    parser.add_argument("--seed", type=int, default=7, help="Random seed for reproducibility")
    parser.add_argument("--output-dir", type=Path, default=Path("coffee_activity_generator/exports"))
    args = parser.parse_args()

    result = generate_queue_logic(seed=args.seed, output_dir=args.output_dir)
    print(f"SVG: {result.svg_path}")
    print(f"PNG: {result.png_path}")
    print(f"Clues: {len(result.puzzle.clues)}")


if __name__ == "__main__":
    _main()
