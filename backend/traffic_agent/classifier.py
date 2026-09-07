from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Protocol


@dataclass(frozen=True)
class ClassificationSignal:
    label: str
    score: float
    backend: str
    calibrated: bool = False


class SequenceClassifier(Protocol):
    """Adapter boundary for an external encrypted-traffic classifier."""

    def classify(self, flow_features: Dict[str, Any]) -> ClassificationSignal:
        ...


class DemoSequenceClassifier:
    """Deterministic placeholder; it is not a trained detector."""

    def classify(self, flow_features: Dict[str, Any]) -> ClassificationSignal:
        packet_count = int(flow_features.get("packetCount") or 0)
        score = min(0.45 + packet_count / 1000, 0.78)
        return ClassificationSignal(
            label="encrypted-traffic-candidate",
            score=round(score, 4),
            backend="DEMO_SEQUENCE_CLASSIFIER",
            calibrated=False,
        )
