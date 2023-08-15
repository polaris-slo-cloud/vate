from dataclasses import dataclass
from enum import Enum
from typing import Any


@dataclass
class Image:
    id: int
    file_name: str


@dataclass
class Frame:
    id: int
    data: Any
    resized_data: Any


class DetectionType(Enum):
    EDGE = 1
    CLOUD = 2


@dataclass
class Detection:
    category: str
    score: int
    bbox: list[float]


@dataclass
class DetectionView:
    frame_id: int
    x: int
    y: int
    w: int
    h: int
    score: int
    category: int
    type: DetectionType
    tracked: bool


@dataclass
class AnnotationView:
    x: int
    y: int
    w: int
    h: int
    category: int


@dataclass
class TrackerRecord:
    raw_tracker: Any
    det_score: int
    det_category: int
    det_type: DetectionType


ImageList = list[Image]
AnnotationsByImage = dict[int, list[AnnotationView]]
