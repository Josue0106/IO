from __future__ import annotations

from typing import List

from core.data_model import CaseData


def validate_case(case: CaseData) -> List[str]:
    """Validate a CaseData object and return a list of error messages.

    The function performs lightweight structural checks (codes exist, positive sizes,
    flows/relations reference known areas) and a simple area-sum warning.
    """
    errors: List[str] = []

    # Facility
    if case.facility.width < 1 or case.facility.height < 1:
        errors.append("Facility dimensions must be positive integers.")

    # Areas
    if not case.areas:
        errors.append("No areas defined.")

    codes = [a.code for a in case.areas]
    if len(set(codes)) != len(codes):
        errors.append("Area codes must be unique.")

    for a in case.areas:
        if not a.code:
            errors.append("Area with empty code found.")
        if a.min_area < 1:
            errors.append(f"Area '{a.code}' has non-positive min_area.")

    code_set = set(codes)

    # Flows
    for f in case.flows:
        if f.origin not in code_set:
            errors.append(f"Flow origin '{f.origin}' not found among areas.")
        if f.dest not in code_set:
            errors.append(f"Flow dest '{f.dest}' not found among areas.")
        if f.value < 0:
            errors.append(f"Flow {f.origin}->{f.dest} has negative value.")

    # Relations
    valid_rels = {"A", "E", "I", "O", "U", "X"}
    for r in case.relations:
        if r.a not in code_set or r.b not in code_set:
            errors.append(f"Relation references unknown areas: {r.a}, {r.b}.")
        if r.rel not in valid_rels:
            errors.append(f"Relation {r.a}-{r.b} uses invalid relation symbol '{r.rel}'.")

    # Special constraints
    for a, b in case.constraints.must_adjacent:
        if a not in code_set or b not in code_set:
            errors.append(f"Must-adjacent constraint references unknown areas: {a}, {b}.")
    for a, b in case.constraints.must_separate:
        if a not in code_set or b not in code_set:
            errors.append(f"Must-separate constraint references unknown areas: {a}, {b}.")

    # Area sum warning (not an error)
    total_min_area = sum(int(a.min_area) for a in case.areas)
    facility_area = int(case.facility.width) * int(case.facility.height)
    if total_min_area > facility_area:
        errors.append(
            "Total minimum area of all areas exceeds facility area (may be infeasible)."
        )

    return errors
