import random
from dataclasses import dataclass, field


@dataclass
class Equation:
    a: int
    op: str
    b: int
    result: int

    @property
    def tokens(self) -> list[str]:
        """Always 5 tokens: [A, op, B, '=', C] — each number is ONE token."""
        return [str(self.a), self.op, str(self.b), '=', str(self.result)]

    @property
    def display(self) -> str:
        return f"{self.a} {self.op} {self.b} = {self.result}"

    def number_at(self, pos: int) -> int | None:
        """Return the number value at token position 0, 2, or 4."""
        if pos == 0:
            return self.a
        if pos == 2:
            return self.b
        if pos == 4:
            return self.result
        return None

    def __repr__(self):
        return self.display


NUMBER_POSITIONS = [0, 2, 4]

# A4 portrait constraints (usable ~190×257mm at min 9mm/cell)
A4_MAX_COLS = 21
A4_MAX_ROWS = 28


@dataclass
class PlacedEquation:
    equation: Equation
    row: int
    col: int
    direction: str  # 'H' or 'V'
    hidden_positions: list[int] = field(default_factory=list)

    def cell_coords(self) -> list[tuple[int, int]]:
        """Return (row, col) for each of the 5 token positions."""
        coords = []
        for i in range(5):
            if self.direction == 'H':
                coords.append((self.row, self.col + i))
            else:
                coords.append((self.row + i, self.col))
        return coords


class CrosswordGenerator:
    def __init__(self):
        self.grid: dict[tuple[int, int], str] = {}
        self.cell_owners: dict[tuple[int, int], list[tuple[int, str]]] = {}
        self.placed: list[PlacedEquation] = []

    def generate_equation_pool(
        self, num_range: int, operations: list[str], pool_size: int = 5000
    ) -> list[Equation]:
        pool = []
        op_map = {'+': lambda a, b: a + b, '-': lambda a, b: a - b, '*': lambda a, b: a * b}

        for op in operations:
            func = op_map[op]
            for a in range(1, num_range + 1):
                for b in range(1, num_range + 1):
                    result = func(a, b)
                    if result < 1:
                        continue
                    pool.append(Equation(a, op, b, result))

        random.shuffle(pool)
        return pool[:pool_size]

    def _can_place(
        self, tokens: list[str], row: int, col: int, direction: str
    ) -> bool:
        has_crossing = False

        for i, token in enumerate(tokens):
            if direction == 'H':
                r, c = row, col + i
            else:
                r, c = row + i, col

            if (r, c) in self.grid:
                if self.grid[(r, c)] != token:
                    return False
                owners = self.cell_owners.get((r, c), [])
                if any(d == direction for _, d in owners):
                    return False
                has_crossing = True
            else:
                # Check no parallel neighbors (prevents merging)
                if direction == 'H':
                    for dr in [-1, 1]:
                        nr, nc = r + dr, c
                        if (nr, nc) in self.grid:
                            owners = self.cell_owners.get((nr, nc), [])
                            if any(d == 'H' for _, d in owners):
                                return False
                else:
                    for dc in [-1, 1]:
                        nr, nc = r, c + dc
                        if (nr, nc) in self.grid:
                            owners = self.cell_owners.get((nr, nc), [])
                            if any(d == 'V' for _, d in owners):
                                return False

        # Cell before and after must be empty
        if direction == 'H':
            before = (row, col - 1)
            after = (row, col + 5)
        else:
            before = (row - 1, col)
            after = (row + 5, col)

        if before in self.grid or after in self.grid:
            return False

        # Check A4 bounds: new placement must not expand grid beyond limits
        if self.grid:
            if direction == 'H':
                new_rows = [row]
                new_cols = list(range(col, col + 5))
            else:
                new_rows = list(range(row, row + 5))
                new_cols = [col]

            all_rows = [r for r, c in self.grid] + new_rows
            all_cols = [c for r, c in self.grid] + new_cols

            if max(all_rows) - min(all_rows) + 1 > A4_MAX_ROWS:
                return False
            if max(all_cols) - min(all_cols) + 1 > A4_MAX_COLS:
                return False

        if not self.placed:
            return True
        return has_crossing

    def _place(self, equation: Equation, row: int, col: int, direction: str):
        pe = PlacedEquation(equation, row, col, direction)
        eq_idx = len(self.placed)
        tokens = equation.tokens
        for i, (r, c) in enumerate(pe.cell_coords()):
            self.grid[(r, c)] = tokens[i]
            if (r, c) not in self.cell_owners:
                self.cell_owners[(r, c)] = []
            self.cell_owners[(r, c)].append((eq_idx, direction))
        self.placed.append(pe)

    def _find_crossings(
        self, equation: Equation, direction: str
    ) -> list[tuple[int, int, int]]:
        """Find valid positions where this equation crosses existing ones at matching numbers."""
        tokens = equation.tokens
        crossings = []

        for pe_idx, pe in enumerate(self.placed):
            if pe.direction == direction:
                continue

            pe_tokens = pe.equation.tokens
            pe_coords = pe.cell_coords()

            for pe_pos in NUMBER_POSITIONS:
                pe_num = pe_tokens[pe_pos]
                pe_r, pe_c = pe_coords[pe_pos]

                for eq_pos in NUMBER_POSITIONS:
                    if tokens[eq_pos] != pe_num:
                        continue

                    # Calculate placement origin so token eq_pos lands on (pe_r, pe_c)
                    if direction == 'H':
                        r = pe_r
                        c = pe_c - eq_pos
                    else:
                        r = pe_r - eq_pos
                        c = pe_c

                    if self._can_place(tokens, r, c, direction):
                        crossings.append((r, c, pe_idx))

        return crossings

    def build(
        self,
        target_count: int,
        num_range: int,
        operations: list[str],
        fill_percent: int = 50,
        max_attempts: int = 20,
    ) -> dict:
        best_result = None

        for attempt in range(max_attempts):
            self.grid = {}
            self.cell_owners = {}
            self.placed = []

            pool = self.generate_equation_pool(num_range, operations)
            if not pool:
                continue

            first = pool.pop(0)
            self._place(first, 0, 0, 'H')

            placed_count = 1
            failures = 0
            max_failures = len(pool) * 2

            eq_index = 0
            while placed_count < target_count and eq_index < len(pool) and failures < max_failures:
                eq = pool[eq_index % len(pool)]
                eq_index += 1

                prefer_dir = 'V' if self.placed[-1].direction == 'H' else 'H'
                dirs = [prefer_dir, 'H' if prefer_dir == 'V' else 'V']

                placed_this = False
                for direction in dirs:
                    crossings = self._find_crossings(eq, direction)
                    if crossings:
                        random.shuffle(crossings)
                        r, c, _ = crossings[0]
                        self._place(eq, r, c, direction)
                        placed_count += 1
                        placed_this = True
                        break

                if not placed_this:
                    failures += 1

            if best_result is None or placed_count > len(best_result['placed']):
                best_result = {
                    'grid': dict(self.grid),
                    'cell_owners': dict(self.cell_owners),
                    'placed': list(self.placed),
                }
                if placed_count >= target_count:
                    break

        if best_result:
            self.grid = best_result['grid']
            self.cell_owners = best_result['cell_owners']
            self.placed = best_result['placed']

        self._assign_hidden_cells(fill_percent)
        return self._to_json()

    def _assign_hidden_cells(self, fill_percent: int = 50):
        """Hide number cells based on fill_percent (10-80%).

        Rules (enforced globally, accounting for crossings):
        - Every equation MUST have at least 1 hidden number cell
        - Every equation MUST have at least 1 visible number cell
        """
        hide_ratio = max(0.2, min(0.9, 1.0 - fill_percent / 100))
        total_numbers = len(self.placed) * 3
        target_hidden = max(len(self.placed), round(total_numbers * hide_ratio))
        target_hidden = max(len(self.placed), min(len(self.placed) * 2, target_hidden))

        # Map grid cell -> list of (eq_idx, token_pos) that use it
        cell_to_eqs: dict[tuple[int, int], list[tuple[int, int]]] = {}
        for i, pe in enumerate(self.placed):
            coords = pe.cell_coords()
            for pos in NUMBER_POSITIONS:
                rc = coords[pos]
                cell_to_eqs.setdefault(rc, []).append((i, pos))

        # Step 1: hide exactly 1 random position per equation
        eq_hidden: dict[int, set[int]] = {}
        for i in range(len(self.placed)):
            eq_hidden[i] = {random.choice(NUMBER_POSITIONS)}

        # Step 2: add more until target (max 2 per equation's own positions)
        current = sum(len(v) for v in eq_hidden.values())
        if current < target_hidden:
            extras = []
            for i in range(len(self.placed)):
                for p in NUMBER_POSITIONS:
                    if p not in eq_hidden[i]:
                        extras.append((i, p))
            random.shuffle(extras)
            for eq_idx, pos in extras:
                if current >= target_hidden:
                    break
                if len(eq_hidden[eq_idx]) < 2:
                    eq_hidden[eq_idx].add(pos)
                    current += 1

        # Step 3: build global hidden set from per-equation decisions
        hidden_cells: set[tuple[int, int]] = set()
        for i, pe in enumerate(self.placed):
            coords = pe.cell_coords()
            for pos in eq_hidden[i]:
                hidden_cells.add(coords[pos])

        # Step 4: fix violations — ensure each equation has 1-2 hidden, 1-2 visible
        changed = True
        while changed:
            changed = False
            for i, pe in enumerate(self.placed):
                coords = pe.cell_coords()
                num_coords = [coords[p] for p in NUMBER_POSITIONS]
                hidden_count = sum(1 for rc in num_coords if rc in hidden_cells)
                visible_count = 3 - hidden_count

                if visible_count == 0:
                    # All 3 hidden — reveal one (prefer non-crossing cell)
                    for rc in random.sample(num_coords, 3):
                        hidden_cells.discard(rc)
                        changed = True
                        break

                if hidden_count == 0:
                    # All 3 visible — hide one
                    rc = random.choice(num_coords)
                    hidden_cells.add(rc)
                    changed = True

        # Apply back to equations
        for i, pe in enumerate(self.placed):
            coords = pe.cell_coords()
            pe.hidden_positions = [p for p in NUMBER_POSITIONS if coords[p] in hidden_cells]

    def _to_json(self) -> dict:
        if not self.grid:
            return {'cells': [], 'equations': [], 'bounds': {}}

        min_r = min(r for r, c in self.grid)
        min_c = min(c for r, c in self.grid)
        max_r = max(r for r, c in self.grid)
        max_c = max(c for r, c in self.grid)

        # Build a set of hidden cells: (row, col) -> True
        hidden_set: set[tuple[int, int]] = set()
        for pe in self.placed:
            coords = pe.cell_coords()
            for pos in pe.hidden_positions:
                hidden_set.add(coords[pos])

        cells = []
        for (r, c), token in self.grid.items():
            nr, nc = r - min_r, c - min_c
            is_number = token not in ('+', '-', '*', '=')
            is_hidden = (r, c) in hidden_set and is_number

            cells.append({
                'row': nr,
                'col': nc,
                'value': token,
                'is_number': is_number,
                'is_hidden': is_hidden,
            })

        equations_info = []
        for pe in self.placed:
            equations_info.append({
                'equation': pe.equation.display,
                'row': pe.row - min_r,
                'col': pe.col - min_c,
                'direction': pe.direction,
            })

        return {
            'cells': cells,
            'equations': equations_info,
            'bounds': {
                'rows': max_r - min_r + 1,
                'cols': max_c - min_c + 1,
            },
            'total_equations': len(self.placed),
        }
