
import cv2
import time
from PySide6.QtCore import QThread, Signal
import numpy as np
import imutils
import platform
from apps.yunet import YuNet
from apps.centerface import CenterFace
from apps.yolo import YOLOModel
from apps.pose import PoseModel
from apps.utils import mask_boxes, merge_boxes
# Les messages emis par error_occurred finissent dans une boite de dialogue :
# ils suivent la langue de l'interface, comme le reste des textes visibles.
from apps.i18n import tr
import logging



class AnonymizationWorker(QThread):
    progress_updated = Signal(int)
    time_remaining_updated = Signal(int)
    anonymization_complete = Signal()
    error_occurred = Signal(str)
    frame_emited = Signal(np.ndarray, int)

    def __init__(self, video_path, output_format, mask_size, write_output=False):
        super().__init__()
        self.logger = logging.getLogger(__name__).getChild(self.__class__.__name__)
        self.video_path = video_path
        # self.net = net
        self.output_format = output_format
        self._is_paused = False
        self._is_stopped = False
        self.replacewith = 'blur'  # Default value
        self.mask_size = mask_size
        self.model = 'yolo'
        # Detecteur de tete additionnel, combine au modele de visage choisi :
        # il rattrape les personnes de dos, que les detecteurs de visage ratent.
        self.use_pose = False
        self.write_output = write_output
        self.logger.info("worker initialized")

    def run(self):
        cap = None
        out = None
        out_size = None
        try:
            cap = cv2.VideoCapture(self.video_path, cv2.CAP_FFMPEG, (cv2.CAP_PROP_HW_ACCELERATION, cv2.VIDEO_ACCELERATION_ANY))
            if not cap.isOpened():
                self.error_occurred.emit(tr("err_open_input", path=self.video_path))
                return

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)

            # Dimensions demandees par l'utilisateur. Elles ne pilotent que la largeur
            # passee a imutils.resize : la hauteur reelle depend du ratio de la source,
            # c'est pourquoi le writer n'est ouvert qu'une fois la premiere frame produite.
            target_width, target_height = self.get_dimensions(self.output_format)
            self.logger.info(self.output_format)
            rotate_code = cap.get(cv2.CAP_PROP_ORIENTATION_META)
            if rotate_code == 90 or rotate_code == 270:
                target_width, target_height = target_height, target_width
            self.logger.info(f"target_width: {target_width}, target_height: {target_height}")

            output_name = None
            fourcc = None
            if self.write_output:
                if platform.system() == "Windows":
                    fourcc = cv2.VideoWriter_fourcc(*'h264')
                else:
                    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                output_name = (self.video_path).split(".")[0] + "_anonymized_" + self.output_format.lower() + ".avi"
                self.logger.info(output_name)

            if self.model == 'yolo':
                yolo_ = YOLOModel()
                centerface = None
                self.yunet = None
            elif self.model == 'centerface':
                centerface = CenterFace(in_shape=(target_width, target_height), backend='auto')  # auto
                yolo_ = None
                self.yunet = None
            elif self.model == 'yunet':
                self.yunet = YuNet([target_width, target_height])  # auto
                yolo_ = None
                centerface = None
            else:
                yolo_ = None
                centerface = None
                self.yunet = None

            pose = PoseModel() if self.use_pose else None
            self.logger.info(f'Anonymizing video with {self.model} model, mask size: {self.mask_size}, replace with: {self.replacewith}')
            if pose is not None:
                self.logger.info('Pose model combined for back-facing people')
            start_time = time.time()
            frame_count = 0
            while cap.isOpened():
                if self._is_stopped:
                    break
                if self._is_paused:
                    time.sleep(0.1)
                    continue
                ret, frame = cap.read()
                if not ret:
                    break
                frame, _ = self.correct_orientation(frame, cap)
                frame = imutils.resize(frame, width=target_width)
                if pose is not None:
                    # Les deux detecteurs voient la meme personne de face. On
                    # rassemble leurs boites et on masque une seule fois, sinon
                    # la zone commune est floutee deux fois et les ellipses se
                    # superposent.
                    boxes = self.face_boxes(frame, yolo_, centerface)
                    heads = pose.detect_heads(frame, 0.25, 0.45)
                    if heads is not None:
                        boxes.extend(heads)
                    if boxes:
                        frame = mask_boxes(merge_boxes(boxes), frame, self.replacewith,
                                           self.mask_size, ellipse=True, mosaicsize=15)
                elif yolo_ is not None:
                    faces = yolo_.detect_faces(frame, 0.25, 0.45)
                    if faces is not None:
                        frame = yolo_.mask_faces(faces, frame, 20, self.replacewith, self.mask_size)
                elif centerface is not None:
                    detections, _ = centerface(frame, threshold=0.25)
                    centerface.anonymize_frame(
                        detections, frame, self.mask_size, replacewith=self.replacewith,
                        ellipse=True, draw_scores=False, replaceimg=None, mosaicsize=15)
                elif self.yunet is not None:
                    frame = self.yunet_mechanism(
                        frame, self.mask_size, replacewith=self.replacewith,
                        ellipse=True, draw_scores=False, replaceimg=None, mosaicsize=15)

                if self.write_output:
                    # Ouverture paresseuse : les dimensions du writer sont celles que le
                    # pipeline produit reellement, pas celles demandees.
                    if out is None:
                        out_size = (frame.shape[1], frame.shape[0])
                        out = cv2.VideoWriter(output_name, fourcc, fps, out_size)
                        if not out.isOpened():
                            self.error_occurred.emit(tr("err_open_output", path=output_name))
                            return
                        self.logger.info(
                            f"Writer ouvert en {out_size[0]}x{out_size[1]} "
                            f"(format demande : {target_width}x{target_height})")
                    # write() renvoie False quand la frame est refusee (OpenCV >= 5).
                    # Sans ce controle, l'echec produit un fichier vide en silence.
                    if out.write(frame) is False:
                        raise RuntimeError(tr(
                            "err_frame_rejected", frame=frame_count,
                            width=frame.shape[1], height=frame.shape[0],
                            expected_width=out_size[0], expected_height=out_size[1]))
                frame_count += 1
                self.frame_emited.emit(frame, rotate_code)
                # Update progress bar
                progress = (frame_count / total_frames) * 100
                self.progress_updated.emit(int(progress))

                # Estimate remaining time
                elapsed_time = time.time() - start_time
                if frame_count > 0:
                    frames_per_second = frame_count / elapsed_time
                    remaining_frames = total_frames - frame_count
                    remaining_time = remaining_frames / frames_per_second
                    self.time_remaining_updated.emit(int(remaining_time))
        except Exception as exc:
            self.logger.exception("Echec de l'anonymisation")
            self.error_occurred.emit(str(exc))
        finally:
            # Release resources
            if cap is not None:
                cap.release()
            if out is not None:
                out.release()
            self.anonymization_complete.emit()

    def face_boxes(self, frame, yolo_, centerface):
        """Boites du detecteur de visage actif, sans masquer la frame.

        Necessaire pour la fusion avec le modele de pose : les trois detecteurs
        masquent normalement eux-memes, ce qui empeche de regrouper les boites
        avant de les appliquer. Les formats different, YuNet donnant x, y, w, h
        la ou les deux autres donnent des coins.
        """
        if yolo_ is not None:
            faces = yolo_.detect_faces(frame, 0.25, 0.45)
            return list(faces) if faces is not None else []
        if centerface is not None:
            detections, _ = centerface(frame, threshold=0.25)
            return [tuple(det[:4].astype(int)) for det in detections]
        if self.yunet is not None:
            h, w = frame.shape[:2]
            self.yunet.setInputSize((w, h))
            detections = self.yunet.infer(frame)
            return [(int(d[0]), int(d[1]), int(d[0] + d[2]), int(d[1] + d[3]))
                    for d in detections]
        return []

    def correct_orientation(self, frame, cap):
        rotate_code = None
        if hasattr(cv2, 'CAP_PROP_ORIENTATION_META'):
            rotate_code = int(cap.get(cv2.CAP_PROP_ORIENTATION_META))
            # self.logger.info(f"Orientation: {rotate_code}")
        if rotate_code == 90:
            frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        elif rotate_code == 180:
            frame = cv2.rotate(frame, cv2.ROTATE_180)
        elif rotate_code == 270:
            frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
        return frame, rotate_code

    def pause(self):
        self._is_paused = True

    def resume(self):
        self._is_paused = False

    def stop(self):
        self._is_stopped = True

    def get_dimensions(self, format):

        if format == "480p":
            return 854, 480
        elif format == "720p":
            return 1280, 720
        elif format == "1080p":
            return 1920, 1080
        elif format == "360p":
            return 640, 360
        else:
            return 640, 480

    def yunet_mechanism(self, frame, mask_size, replacewith, ellipse=True, draw_scores=False, replaceimg=None, mosaicsize=15):
        # loop over the detections
        (h, w) = frame.shape[:2]  # Get the height and width of the frame
        self.yunet.setInputSize((w, h))
        detections = self.yunet.infer(frame)
        # self.logger.info results
        # self.logger.info('{} faces detected.'.format(detections.shape[0]))
        # for idx, det in enumerate(detections):
        #     self.logger.info('{}: {:.0f} {:.0f} {:.0f} {:.0f} {:.0f} {:.0f} {:.0f} {:.0f} {:.0f} {:.0f} {:.0f} {:.0f} {:.0f} {:.0f}'.format(
        #         idx, *det[:-1])
        #     )
        # if detections.shape[0] == 0:
        #     return frame
        frame = self.yunet.visualize(frame, detections, mask_size, replacewith, ellipse=True, draw_scores=False, replaceimg=None, mosaicsize=15)
        return frame
