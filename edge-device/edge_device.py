from typing import Union

import cv2 as cv
import glob
import time

from annotation import annotations_available, load_annotations
from bbox import scale
from category import to_category_id
from detection import detect_objects, frame_change_detected
from display import display_detection, display_annotation, display_fps
from evaluation import evaluate_detections
from frame import get_frames
from model import DetectionView, ImageList, AnnotationsByImage, Frame, Detection, DetectionType
from track import MultiObjectTracker


class EdgeDevice:
    frame_processing_width: int
    frame_processing_height: int
    detection_rate: int
    object_tracker: MultiObjectTracker

    frame_count: int
    prev_frame_at: float

    all_detections: list[DetectionView]
    detections_to_display: list[DetectionView]

    skipped_frames: int
    tracker_failures: int

    def __init__(self, frame_processing_width: int, frame_processing_height: int, detection_rate: int,
                 object_tracker: MultiObjectTracker):
        self.frame_processing_width = frame_processing_width
        self.frame_processing_height = frame_processing_height
        self.detection_rate = detection_rate
        self.object_tracker = object_tracker

        self.frame_count = 0
        self.prev_frame_at = 0

        self.all_detections = []
        self.detections_to_display = []

        self.skipped_frames = 0
        self.tracker_failures = 0

    def process(self, videos: Union[str, None], annotations_path: Union[str, None]):
        items = []
        multiple_videos = False

        if videos is not None:
            items = glob.glob(videos)
        else:
            self._process_camera()

        if len(items) > 0:
            if items[0].endswith(".jpg"):
                video = videos
                self._process_video(video, annotations_path)
            else:
                multiple_videos = True

        if multiple_videos:
            self._process_multiple_videos(videos, annotations_path)

        if annotations_available(videos, annotations_path):
            evaluate_detections(self.all_detections, annotations_path)

        cv.destroyAllWindows()
        print(f"{self.skipped_frames} frames skipped")
        print(f"{self.tracker_failures} tracker failures")

    def _process_camera(self):
        self._process_video(None, None)

    def _process_multiple_videos(self, videos: str, annotations_path: Union[str, None]):
        for video in glob.glob(videos):
            self.detections_to_display = []
            self.object_tracker.reset_objects()
            self.frame_count = 0
            self.prev_frame_at = 0
            self._process_video(f"{video}/*", annotations_path)

    def _process_video(self, video: Union[str, None], annotations_path: Union[str, None]):
        images: ImageList = []
        annotations: AnnotationsByImage = dict()
        if annotations_available(video, annotations_path):
            (images, annotations) = load_annotations(video, annotations_path)

        prev_frame: Union[Frame, None] = None
        frames = get_frames(video, images, self.frame_processing_width, self.frame_processing_height)

        while True:
            frame = next(frames)
            if frame.id == -1:
                break

            frame_height, frame_width, _ = frame.data.shape
            frame_width_scale = frame_width / self.frame_processing_width
            frame_height_scale = frame_height / self.frame_processing_height

            frame_changed = True
            if prev_frame is not None:
                frame_changed = frame_change_detected(frame, prev_frame)

            if not frame_changed:
                print('Skipping frame due to no changes')
                self.skipped_frames += 1
            elif self.frame_count % self.detection_rate == 0:
                self.detections_to_display = []
                self.object_tracker.reset_objects()
                (det_type, detections) = detect_objects(frame)
                for detection in detections:
                    self.object_tracker.add_object(frame, detection, det_type)

                    det_view = _to_view(detection, det_type, frame.id, frame_width_scale, frame_height_scale,
                                        tracked=False)
                    self.all_detections.append(det_view)
                    self.detections_to_display.append(det_view)
            elif self.frame_count % 2 == 0:
                tracking_result = self.object_tracker.track_objects(frame)
                if not tracking_result:
                    self.tracker_failures += 1

                for (detection, det_type) in tracking_result:
                    det_view = _to_view(detection, det_type, frame.id, frame_width_scale, frame_height_scale,
                                        tracked=True)
                    self.all_detections.append(det_view)
                    self.detections_to_display.append(det_view)

            frame_at = time.time()
            fps = int(1 / (frame_at - self.prev_frame_at))
            self.prev_frame_at = frame_at

            self.frame_count += 1
            prev_frame = frame

            for received_detection in self.detections_to_display:
                display_detection(frame.data, received_detection)

            if annotations_available(video, annotations_path):
                for annotation in annotations[frame.id]:
                    display_annotation(frame.data, annotation)

            display_fps(frame.data, fps)

            cv.imshow('frame', frame.data)
            if cv.waitKey(1) == ord('q'):
                break


def _to_view(detection: Detection, det_type: DetectionType, frame_id: int, scale_width: float, scale_height: float,
             tracked: bool) -> DetectionView:
    (x, y, w, h) = scale(detection.bbox, scale_width, scale_height)
    category_id = to_category_id(detection.category)
    return DetectionView(frame_id, x, y, w, h, detection.score, category_id, det_type, tracked)
