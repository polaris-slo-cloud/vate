from pycocotools.coco import maskUtils as mask
from scipy.optimize import linear_sum_assignment
from typing import List

from model import Detection, DetectionType


def fuse_edge_cloud_detections(current_detections: List[Detection],
                               new_detections: List[Detection],
                               new_type: DetectionType) -> List[Detection]:
    if not current_detections:
        return new_detections

    if not new_detections:
        return []

    current_detection_bboxes = [detection.bbox for detection in current_detections]
    new_detection_bboxes = [detection.bbox for detection in new_detections]

    M = mask.iou(current_detection_bboxes, new_detection_bboxes, [0] * len(new_detection_bboxes))
    M[M < 0.5] = 0

    current_ind, new_ind = linear_sum_assignment(M, maximize=True)
    result = []

    for i, j in zip(current_ind, new_ind):
        if M[i, j] != 0:
            category = ""
            bbox = []
            if new_type == DetectionType.CLOUD:
                category = new_detections[j].category
                bbox = current_detections[i].bbox
            if new_type == DetectionType.EDGE:
                category = current_detections[i].category
                bbox = new_detections[j].bbox
            score = new_detections[j].score
            score = int(score * 0.99)
            result.append(Detection(category=category, score=score, bbox=bbox))
        else:
            detection = new_detections[j]
            result.append(Detection(category=detection.category, score=detection.score, bbox=detection.bbox))

    return result