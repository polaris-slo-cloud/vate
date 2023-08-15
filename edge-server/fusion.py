from pycocotools.coco import maskUtils as mask
from scipy.optimize import linear_sum_assignment
from typing import List
import numpy as np

from model import RawDetection, DetectionType


def fuse_edge_cloud_detections(current_detections: List[RawDetection],
                               new_detections: List[RawDetection],
                               new_type: DetectionType) -> List[RawDetection]:
    if not current_detections:
        return new_detections

    M = np.zeros((len(current_detections), len(new_detections)))
    for i, current in enumerate(current_detections):
        for j, new in enumerate(new_detections):
            iou = mask.iou([current.bbox], [new.bbox], [0])
            if iou >= 0.5:
                M[i, j] = iou
            else:
                M[i, j] = 0

    current_ind, new_ind = linear_sum_assignment(M, maximize=True)
    result = []

    for i, j in zip(current_ind, new_ind):
        if M[i, j] != 0:
            class_name = ""
            bbox = []
            if new_type == DetectionType.CLOUD:
                class_name = new_detections[j].class_name
                bbox = current_detections[i].bbox
            if new_type == DetectionType.EDGE:
                class_name = current_detections[i].class_name
                bbox = new_detections[j].bbox
            score = new_detections[j].score
            score = score * 0.99
            result.append(RawDetection(class_name=class_name, score=score, bbox=bbox, last_type=new_type))
        else:
            detection = new_detections[j]
            result.append(RawDetection(class_name=detection.class_name, score=detection.score, bbox=detection.bbox,
                                       last_type=new_type))

    return result
