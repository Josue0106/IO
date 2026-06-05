from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple
import math
import json


@dataclass(frozen=True)
class Area:
    code: str
    name: str
    min_area: int


@dataclass(frozen=True)
class Relation:
    a: str
    b: str
    rel: str


@dataclass(frozen=True)
class Flow:
    origin: str
    dest: str
    value: int


@dataclass(frozen=True)
class Facility:
    width: int
    height: int


@dataclass(frozen=True)
class SpecialConstraints:
    must_adjacent: List[Tuple[str, str]]
    must_separate: List[Tuple[str, str]]


@dataclass(frozen=True)
class CaseData:
    facility: Facility
    areas: List[Area]
    relations: List[Relation]
    flows: List[Flow]
    relation_weights: Dict[str, int]
    growth_percent: float
    constraints: SpecialConstraints


def load_case(path: str) -> CaseData:
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return case_from_dict(payload)


def case_from_dict(payload: Dict) -> CaseData:
    facility = Facility(
        width=int(payload["facility"]["width"]),
        height=int(payload["facility"]["height"]),
    )
    areas = [Area(code=a["code"], name=a["name"], min_area=int(a["min_area"])) for a in payload["areas"]]
    relations = [Relation(a=r["a"], b=r["b"], rel=r["rel"]) for r in payload.get("relations", [])]
    flows = [Flow(origin=f["origin"], dest=f["dest"], value=int(f["value"])) for f in payload.get("flows", [])]
    relation_weights = {k: int(v) for k, v in payload.get("relation_weights", {}).items()}
    growth_percent = float(payload.get("growth_percent", 0.0))

    constraints_payload = payload.get("special_constraints", {})
    must_adjacent = _parse_pairs(constraints_payload.get("must_adjacent", []))
    must_separate = _parse_pairs(constraints_payload.get("must_separate", []))
    constraints = SpecialConstraints(must_adjacent=must_adjacent, must_separate=must_separate)

    return CaseData(
        facility=facility,
        areas=areas,
        relations=relations,
        flows=flows,
        relation_weights=relation_weights,
        growth_percent=growth_percent,
        constraints=constraints,
    )


def case_to_dict(case: CaseData) -> Dict:
    return {
        "facility": {"width": case.facility.width, "height": case.facility.height},
        "areas": [{"code": a.code, "name": a.name, "min_area": a.min_area} for a in case.areas],
        "relations": [{"a": r.a, "b": r.b, "rel": r.rel} for r in case.relations],
        "flows": [{"origin": f.origin, "dest": f.dest, "value": f.value} for f in case.flows],
        "relation_weights": dict(case.relation_weights),
        "growth_percent": case.growth_percent,
        "special_constraints": {
            "must_adjacent": [{"a": a, "b": b} for a, b in case.constraints.must_adjacent],
            "must_separate": [{"a": a, "b": b} for a, b in case.constraints.must_separate],
        },
    }


def _parse_pairs(items: List[Dict]) -> List[Tuple[str, str]]:
    pairs: List[Tuple[str, str]] = []
    for item in items:
        a = item.get("a")
        b = item.get("b")
        if not a or not b:
            continue
        pairs.append((str(a), str(b)))
    return pairs


def area_index(areas: List[Area]) -> Dict[str, int]:
    return {a.code: idx for idx, a in enumerate(areas)}


def area_lookup(areas: List[Area]) -> Dict[str, Area]:
    return {a.code: a for a in areas}
