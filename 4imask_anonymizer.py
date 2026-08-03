import apps.compat  # noqa: F401  must stay first, see apps/compat.py
import sys
import cv2
import qdarktheme
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QFileDialog,
    QDoubleSpinBox, QSpacerItem, QSizePolicy,
    QHBoxLayout, QVBoxLayout, QWidget, QLabel,
    QProgressBar, QComboBox, QMessageBox, QCheckBox)
from PySide6.QtGui import QImage, QPixmap, QIcon, QDesktopServices
from PySide6.QtCore import QTimer, QUrl, Qt
from apps.worker import AnonymizationWorker
from apps.utils import resource_path
from apps.version import VERSION_UNKNOWN, get_version, get_copyright_years
from apps.authorization import (
    AUTHORIZED_DOMAINS_FILE, DOMAIN_ENV_VAR, is_authorized, load_authorized_domains)
from apps import i18n
from apps.flags import LanguageFlagButton
from apps.i18n import tr
from apps.privacy import PrivacyDialog, short_notice, should_show_notice
import logging
from datetime import datetime
import platform

try:
    import pyi_splash
    pyi_splash.update_text("Loading...")
    pyi_splash.close()
except ImportError:
    print("pyi_splash not found, continuing without splash screen.")

# Nom du produit : il reste identique dans toutes les langues.
APPLICATION_TITLE = "4iMask Anonymizer"


class VideoAnonymizer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.version = get_version()
        self.setWindowIcon(QIcon(resource_path("res/icons/4imask.png")))
        self.setWindowTitle(APPLICATION_TITLE)
        self.logger = logging.getLogger(__name__).getChild(self.__class__.__name__)
        if not self.check_authorization():
            sys.exit()

        self.ffmpeg_path = self.get_ffmpeg_path()
        self.ffmpeg_env = FFmpegPathManager(self.ffmpeg_path)
        self.ffmpeg_env.set_ffmpeg_env_path()
        self.logger.info(f"FFmpeg path in environment: {self.ffmpeg_env.is_ffmpeg_path_in_env()}")
        self.mask_size = 1.6
        self.setGeometry(100, 100, 800, 600)

        # Etat affiche, defini avant les widgets : retranslate() le relit pour
        # reconstruire les libelles qui en dependent (fichier choisi, temps
        # restant, resultat du traitement) au lieu de traduire du texte deja pose.
        self.video_path = None
        self.cap = None
        # Renseigne par on_worker_error : anonymization_complete s'en sert pour ne pas
        # annoncer une reussite alors que le traitement s'est interrompu sur une erreur.
        self._worker_error = None
        self._remaining_seconds = None
        self._notification = None
        self.timer = QTimer()
        self.pause_updates = False
        self.is_playing = False

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        self.privacy_banner = QLabel()
        self.privacy_banner.setWordWrap(True)
        self.privacy_banner.setObjectName("privacyBanner")
        self.privacy_banner.setStyleSheet(
            "#privacyBanner { background-color: #fff8e1; color: #5c4600;"
            " border: 1px solid #e0b400; border-radius: 4px; padding: 6px; }")
        self.layout.addWidget(self.privacy_banner)

        self.select_button = QPushButton()
        self.select_button.clicked.connect(self.select_video)
        self.video_label = QLabel()
        self.layout.addWidget(self.select_button)
        self.layout.addWidget(self.video_label)

        self.format_label = QLabel()
        self.layout.addWidget(self.format_label)

        self.format_combo = QComboBox()
        self.format_combo.addItems(["480p", "360p", "720p", "1080p"])
        self.layout.addWidget(self.format_combo)

        self.anonymization_options_layout = QHBoxLayout()
        self.mosaic_checkbox = QCheckBox()
        self.mosaic_checkbox.setEnabled(True)
        self.blur_checkbox = QCheckBox()
        self.blur_checkbox.setChecked(True)
        self.mask_checkbox = QCheckBox()
        self.mask_checkbox.setEnabled(True)
        self.mosaic_checkbox.toggled.connect(self.update_checkboxes)
        self.blur_checkbox.toggled.connect(self.update_checkboxes)
        self.mask_checkbox.toggled.connect(self.update_checkboxes)
        self.anonymization_options_layout.addWidget(self.mosaic_checkbox)
        self.anonymization_options_layout.addWidget(self.blur_checkbox)
        self.anonymization_options_layout.addWidget(self.mask_checkbox)
        self.spin_label = QLabel()
        self.anonymization_options_layout.addWidget(self.spin_label)
        self.spinbox = QDoubleSpinBox()
        self.spinbox.setMinimum(1.0)
        self.spinbox.setMaximum(5.0)
        self.spinbox.setSingleStep(0.1)
        self.spinbox.setValue(self.mask_size)
        self.spinbox.valueChanged.connect(self.update_mask_size)

        self.anonymization_options_layout.addWidget(self.spinbox)
        self.layout.addLayout(self.anonymization_options_layout)

        self.detection_models_layout = QHBoxLayout()
        self.yolo_checkbox = QCheckBox("Yolov11n Face")
        self.yolo_checkbox.setChecked(True)
        self.centerface_checkbox = QCheckBox("Center Face")
        self.yunet_checkbox = QCheckBox("Yunet")
        self.yolo_checkbox.toggled.connect(self.update_model_checkboxes)
        self.centerface_checkbox.toggled.connect(self.update_model_checkboxes)
        self.yunet_checkbox.toggled.connect(self.update_model_checkboxes)
        self.detection_models_layout.addWidget(self.yolo_checkbox)
        self.detection_models_layout.addWidget(self.centerface_checkbox)
        self.detection_models_layout.addWidget(self.yunet_checkbox)
        # Volontairement hors du groupe exclusif ci-dessus : ce detecteur ne
        # remplace pas le modele de visage, il s'y ajoute pour couvrir les
        # personnes de dos, qu'aucun detecteur de visage ne peut trouver.
        self.pose_checkbox = QCheckBox()
        self.detection_models_layout.addWidget(self.pose_checkbox)
        self.layout.addLayout(self.detection_models_layout)

        self.buttons_layout = QHBoxLayout()
        self.start_button = QPushButton()
        self.start_button.clicked.connect(self.start_anonymization)
        self.buttons_layout.addWidget(self.start_button)

        self.pause_button = QPushButton()
        self.pause_button.clicked.connect(self.pause_anonymization)
        self.pause_button.setEnabled(False)
        self.buttons_layout.addWidget(self.pause_button)

        self.resume_button = QPushButton()
        self.resume_button.clicked.connect(self.resume_anonymization)
        self.resume_button.setEnabled(False)
        self.buttons_layout.addWidget(self.resume_button)

        self.stop_button = QPushButton()
        self.stop_button.clicked.connect(self.stop_anonymization)
        self.stop_button.setEnabled(False)
        self.buttons_layout.addWidget(self.stop_button)

        self.play_button = QPushButton()
        self.play_button.clicked.connect(self.toggle_play_pause)
        self.buttons_layout.addWidget(self.play_button)

        self.layout.addLayout(self.buttons_layout)

        self.progress_bar = QProgressBar()
        self.layout.addWidget(self.progress_bar)

        self.time_label = QLabel()
        self.layout.addWidget(self.time_label)

        # self.layout.addWidget(self.play_button)
        self.notification_label = QLabel()
        self.layout.addWidget(self.notification_label)

        self.original_label = QLabel()
        self.layout.addWidget(self.original_label)
        # Ajouter un espaceur flexible pour pousser l'étiquette de version vers le bas
        spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.layout.addItem(spacer)

        last_line = QHBoxLayout()

        # Ajouter un lien hypertexte pour ouvrir le fichier LICENSE
        self.license_link = QLabel()
        self.license_link.setOpenExternalLinks(False)
        self.license_link.linkActivated.connect(self.open_license)

        # Accès permanent à l'information RGPD (transparence, art. 5.1.a RGPD)
        self.privacy_link = QLabel()
        self.privacy_link.setOpenExternalLinks(False)
        self.privacy_link.linkActivated.connect(self.show_privacy_notice)

        # Bascule français / anglais de toute l'interface, d'un clic sur le drapeau.
        self.language_button = LanguageFlagButton(self)

        self.version_label = QLabel()
        last_line.addWidget(self.version_label)
        last_line.addStretch(1)
        last_line.addWidget(self.privacy_link)
        last_line.addWidget(self.license_link)
        last_line.addWidget(self.language_button)
        last_line.setAlignment(self.privacy_link, Qt.AlignRight)
        last_line.setAlignment(self.license_link, Qt.AlignRight)
        self.layout.addLayout(last_line)
        # self.anonymized_label = QLabel("Anonymized Video")
        # self.layout.addWidget(self.anonymized_label)

        # self.timer.timeout.connect(self.update_frame)

        self.retranslate()
        i18n.notifier.language_changed.connect(self.on_language_changed)

        # Affichée une fois la fenêtre peinte, au démarrage de la boucle d'évènements.
        QTimer.singleShot(0, self.maybe_show_privacy_notice)

    def retranslate(self):
        """Réécrit tous les libellés dans la langue courante.

        Appelée à la construction et à chaque bascule du drapeau : les textes qui
        dépendent de l'état de l'application sont reconstruits depuis cet état,
        et non retraduits depuis ce qui est affiché.
        """
        self.privacy_banner.setText(short_notice())
        self.privacy_link.setText(f'<a href="#">{tr("privacy_link")}</a>')
        self.license_link.setText(f'<a href="#">{tr("license_link")}</a>')

        self.select_button.setText(tr("select_video"))
        self.video_label.setText(
            os.path.basename(self.video_path) if self.video_path
            else tr("no_video_selected"))
        self.format_label.setText(tr("output_format"))

        self.mosaic_checkbox.setText(tr("mosaic"))
        self.blur_checkbox.setText(tr("blur"))
        self.mask_checkbox.setText(tr("solid_mask"))
        self.spin_label.setText(tr("mask_size"))

        # Les noms des modeles de detection ne sont pas traduits : ce sont des
        # noms propres, que l'utilisateur retrouve dans la documentation amont.
        self.pose_checkbox.setText(tr("pose_option"))
        self.pose_checkbox.setToolTip(tr("pose_tooltip"))

        self.start_button.setText(tr("start"))
        self.pause_button.setText(tr("pause"))
        self.resume_button.setText(tr("resume"))
        self.stop_button.setText(tr("stop"))
        self.play_button.setText(
            tr("stop_preview") if self.is_playing else tr("play_preview"))

        self.time_label.setText(self.time_remaining_text())
        self.notification_label.setText(self.notification_text())
        # Ce meme label porte l'image de l'apercu : lui poser du texte
        # l'effacerait. Il n'est retraduit que tant qu'il ne montre rien.
        if self.original_label.pixmap().isNull():
            self.original_label.setText(tr("original_video"))

        version = self.version if self.version != VERSION_UNKNOWN else tr("version_unknown")
        self.version_label.setText(
            tr("version_label", years=get_copyright_years(), version=version))

    def time_remaining_text(self):
        if self._remaining_seconds is None:
            return tr("time_remaining_unknown")
        hours, remainder = divmod(self._remaining_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return tr("time_remaining", hours=int(hours), minutes=int(minutes),
                  seconds=int(seconds))

    def notification_text(self):
        if self._notification == "failed":
            return tr("failed", error=self._worker_error)
        if self._notification == "complete":
            return tr("complete")
        return ""

    def on_language_changed(self, _language):
        self.retranslate()

    def maybe_show_privacy_notice(self):
        """Notice RGPD au premier lancement, ou après évolution de son contenu."""
        if should_show_notice():
            self.show_privacy_notice(startup=True)

    def show_privacy_notice(self, _link=None, startup=False):
        # La bascule de langue faite depuis la notice remonte par i18n.notifier,
        # qui retraduit aussi bien le dialogue que cette fenêtre.
        PrivacyDialog(self, startup=startup).exec()

    def check_authorization(self):
        """Applique le garde-fou d'usage decrit dans apps/authorization.py.

        La liste de domaines n'est pas versionnee : quand elle est absente, ce
        qui est le cas d'une execution depuis les sources, aucune restriction
        n'est appliquee.
        """
        domain = os.getenv(DOMAIN_ENV_VAR)
        authorized_domains = load_authorized_domains(resource_path(AUTHORIZED_DOMAINS_FILE))
        if authorized_domains is None:
            self.logger.info("No embedded domain list, running without usage restriction.")
            return True
        if is_authorized(domain, authorized_domains):
            return True
        self.logger.warning(f"Unauthorized domain: {domain!r}")
        QMessageBox.warning(self, tr("warning_title"), tr("warn_not_authorized"))
        return False

    def select_video(self):
        if hasattr(self, 'worker') and self.worker.isRunning():
            QMessageBox.warning(self, tr("warning_title"), tr("warn_in_progress"))
            return
        options = QFileDialog.Options()
        self.video_path, _ = QFileDialog.getOpenFileName(
            self, tr("select_video_dialog"), "", tr("video_filter"), options=options)
        # Le libelle est reconstruit depuis video_path, y compris quand la
        # selection est annulee : il annoncait jusqu'ici un nom de fichier vide.
        self.video_label.setText(
            os.path.basename(self.video_path) if self.video_path
            else tr("no_video_selected"))
        if self.video_path:
            self.cap = cv2.VideoCapture(self.video_path)
            self.timer.start(30)
        else:
            QMessageBox.warning(self, tr("warning_title"), tr("no_video_selected"))

    def start_anonymization(self):
        # self.ffmpeg_path = self.get_ffmpeg_path()
        # self.set_ffmpeg_env_path()
        # self.logger.info(self.is_ffmpeg_path_in_env())
        # self.net = self.load_model()
        if self.video_path:
            self.pause_updates = True
            output_format = self.format_combo.currentText()
            replacewith = self.get_replacewith_option()
            model = self.get_model_option()
            if hasattr(self, 'worker') and self.worker.isRunning():
                self.worker.stop()
                self.worker.wait()
            self.worker = AnonymizationWorker(self.video_path, output_format, self.mask_size, write_output=True)
            self.logger.info(f'Model: {model}')
            self.logger.info(f'Replacewith: {replacewith}')
            self.worker.model = model
            self.worker.use_pose = self.pose_checkbox.isChecked()
            self.worker.replacewith = replacewith
            self._worker_error = None
            self._notification = None
            self.notification_label.setText("")
            self.worker.progress_updated.connect(self.update_progress)
            self.worker.time_remaining_updated.connect(self.update_time)
            self.worker.anonymization_complete.connect(self.anonymization_complete)
            self.worker.error_occurred.connect(self.on_worker_error)
            self.worker.frame_emited.connect(self.update_frame)
            self.worker.start()
            self.select_button.setEnabled(False)
            self.pause_button.setEnabled(True)
            self.resume_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.blur_checkbox.setEnabled(False)
            self.mask_checkbox.setEnabled(False)
            self.mosaic_checkbox.setEnabled(False)
            self.play_button.setEnabled(False)  # Disable play button during anonymization
            self.yolo_checkbox.setEnabled(False)
            self.centerface_checkbox.setEnabled(False)
            self.yunet_checkbox.setEnabled(False)
            self.pose_checkbox.setEnabled(False)
        else:
            QMessageBox.warning(self, tr("warning_title"), tr("warn_select_first"))

    def update_checkboxes(self, checked):
        if checked:
            sender = self.sender()
            if sender == self.mosaic_checkbox:
                self.blur_checkbox.setChecked(False)
                self.mask_checkbox.setChecked(False)
            elif sender == self.blur_checkbox:
                self.mosaic_checkbox.setChecked(False)
                self.mask_checkbox.setChecked(False)
            elif sender == self.mask_checkbox:
                self.mosaic_checkbox.setChecked(False)
                self.blur_checkbox.setChecked(False)
        self.get_replacewith_option()

    def update_model_checkboxes(self, checked):
        if checked:
            sender = self.sender()
            if sender == self.yolo_checkbox:
                self.centerface_checkbox.setChecked(False)
                self.yunet_checkbox.setChecked(False)
            elif sender == self.centerface_checkbox:
                self.yolo_checkbox.setChecked(False)
                self.yunet_checkbox.setChecked(False)
            elif sender == self.yunet_checkbox:
                self.yolo_checkbox.setChecked(False)
                self.centerface_checkbox.setChecked(False)
        self.get_model_option()
    
    def get_model_option(self):
        if self.yolo_checkbox.isChecked():
            if hasattr(self, 'worker'):
                self.worker.model = 'yolo'
            return 'yolo'
        elif self.centerface_checkbox.isChecked():
            if hasattr(self, 'worker'):
                self.worker.model = 'centerface'
            return 'centerface'
        elif self.yunet_checkbox.isChecked():
            if hasattr(self, 'worker'):
                self.worker.model = 'yunet'
            return 'yunet'
        else:
            return 'none'

    def update_mask_size(self, value):
        value = round(value,2)
        self.logger.info(value)
        if hasattr(self, 'worker'):
            self.worker.mask_size = value
        else:
            self.mask_size = round(value,2)


    def get_replacewith_option(self):
        if self.mosaic_checkbox.isChecked():
            if hasattr(self, 'worker'):
                self.worker.replacewith = 'mosaic'
            return 'mosaic'
        elif self.blur_checkbox.isChecked():
            if hasattr(self, 'worker'):
                self.worker.replacewith = 'blur'
            return 'blur'
        elif self.mask_checkbox.isChecked():
            if hasattr(self, 'worker'):
                self.worker.replacewith = 'solid'
            return 'solid'
        else:
            return 'none'

    def pause_anonymization(self):
        if hasattr(self, 'worker'):
            self.worker.pause()
            self.pause_button.setEnabled(False)
            self.resume_button.setEnabled(True)

    def resume_anonymization(self):
        if hasattr(self, 'worker'):
            self.worker.resume()
            self.pause_button.setEnabled(True)
            self.resume_button.setEnabled(False)

    def stop_anonymization(self):
        if hasattr(self, 'worker'):
            self.worker.stop()
            self.select_button.setEnabled(True)
            self.pause_button.setEnabled(False)
            self.resume_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            self.blur_checkbox.setEnabled(True)
            self.mask_checkbox.setEnabled(True)
            self.mosaic_checkbox.setEnabled(True)
            self.yolo_checkbox.setEnabled(True)
            self.centerface_checkbox.setEnabled(True)
            self.yunet_checkbox.setEnabled(True)
            self.pose_checkbox.setEnabled(True)
            self.play_button.setEnabled(True)  # Enable play button after stopping
            self.is_playing = False
            self.play_button.setText(tr("play_preview"))

    def get_ffmpeg_path(self):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "res/ffmpeg", "bin")

    def update_progress(self, progress):
        self.progress_bar.setValue(progress)

    def update_time(self, remaining_time):
        self._remaining_seconds = remaining_time
        self.time_label.setText(self.time_remaining_text())

    def on_worker_error(self, message):
        """Affiche une erreur remontee par le thread de traitement.

        Le worker ne peut pas creer de widget lui-meme : il emet error_occurred et
        c'est ici, dans le thread GUI, que la boite de dialogue est construite.
        """
        self._worker_error = message
        self.logger.error(f'Anonymization failed for {self.video_path}: {message}')
        QMessageBox.critical(self, tr("error_title"), message)

    def anonymization_complete(self):
        self._notification = "failed" if self._worker_error else "complete"
        self.notification_label.setText(self.notification_text())
        if not self._worker_error:
            self.logger.info(f'Anonymization complete for {self.video_path}, time remaining : {self.time_label.text()}')
        self.select_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.play_button.setEnabled(True)
        self.yolo_checkbox.setEnabled(True)
        self.centerface_checkbox.setEnabled(True)
        self.yunet_checkbox.setEnabled(True)
        self.pose_checkbox.setEnabled(True)
        # Reactivees ici aussi : start_anonymization les desactive, et sans cela elles
        # restaient grisees jusqu'au redemarrage de l'application.
        self.blur_checkbox.setEnabled(True)
        self.mask_checkbox.setEnabled(True)
        self.mosaic_checkbox.setEnabled(True)
        self.format_combo.setEnabled(True)
        self.is_playing = False
        self.play_button.setText(tr("play_preview"))

    def update_frame(self, frame=None, rotate_code=None):
        if not self.pause_updates and frame is not None:
        #     if not hasattr(self, 'paused_frame_displayed') or not self.paused_frame_displayed:
        #         rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        #         h, w, ch = rgb_image.shape
        #         bytes_per_line = ch * w
        #         convert_to_Qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        #         p = convert_to_Qt_format.scaled(720, 480)
        #         self.original_label.setPixmap(QPixmap.fromImage(p))
        #         self.paused_frame_displayed = True
        #     return

        # # Reset the flag when updates are not paused
        
        # self.paused_frame_displayed = False
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            convert_to_Qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            if rotate_code is None or rotate_code == 0 or rotate_code == 180:
                p = convert_to_Qt_format.scaled(720, 480)
            else:
                p = convert_to_Qt_format.scaled(320, 480)
            self.original_label.setPixmap(QPixmap.fromImage(p))

    def toggle_play_pause(self):
        if self.is_playing:
            self.stop_preview()
            self.start_button.setEnabled(True)
        else:
            self.play_preview()
            self.start_button.setEnabled(False)

    def play_preview(self):
        if self.video_path:
            self.pause_updates = False
            output_format = self.format_combo.currentText()
            replacewith = self.get_replacewith_option()
            model = self.get_model_option()
            if hasattr(self, 'worker') and self.worker.isRunning():
                self.logger.info(self.worker.isRunning())

                self.worker.stop()
                self.worker.quit()
                self.worker.wait()
                self.logger.info("Worker stopped.")
            self.worker = AnonymizationWorker(self.video_path, output_format, self.mask_size, write_output=False)
            self.worker.model = model
            self.worker.use_pose = self.pose_checkbox.isChecked()
            self.worker.replacewith = replacewith
            self.logger.info(f'Model  : {model}')
            self.logger.info(f'Replacewith : {replacewith}')
            self._worker_error = None
            self.worker.error_occurred.connect(self.on_worker_error)
            self.worker.frame_emited.connect(self.update_frame)
            self.worker.start()
            self.timer.timeout.connect(self.update_frame)
            self.timer.start(30)
            self.is_playing = True
            self.play_button.setText(tr("stop_preview"))
            self.stop_button.setEnabled(False)
            self.select_button.setEnabled(False)
            self.format_combo.setEnabled(False)
            self.resume_button.setEnabled(False)
            self.pause_button.setEnabled(False)
            self.yolo_checkbox.setEnabled(False)
            self.centerface_checkbox.setEnabled(False)
            self.yunet_checkbox.setEnabled(False)
            self.pose_checkbox.setEnabled(False)
        else:
            QMessageBox.warning(self, tr("warning_title"), tr("warn_select_first"))

    def stop_preview(self):
        self.timer.stop()
        self.worker.stop()
        self.worker.quit()
        self.worker.wait()

        self.pause_updates = True
        self.is_playing = False
        self.play_button.setText(tr("play_preview"))
        self.select_button.setEnabled(True)
        self.format_combo.setEnabled(True)
        self.yolo_checkbox.setEnabled(True)
        self.centerface_checkbox.setEnabled(True)
        self.yunet_checkbox.setEnabled(True)
        self.pose_checkbox.setEnabled(True)

        # self.resume_button.setEnabled(True)
        # self.pause_button.setEnabled(True)

    def open_license(self):
        license_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "LICENSE")
        QDesktopServices.openUrl(QUrl.fromLocalFile(license_path))

    def closeEvent(self, event):
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        # self.ffmpeg_env.remove_ffmpeg_env_path()
        event.accept()


class FFmpegPathManager:
    def __init__(self, ffmpeg_path):
        self.ffmpeg_path = ffmpeg_path

    def set_ffmpeg_env_path(self):
        if platform.system() == "Windows":
            os.environ["PATH"] += os.pathsep + self.ffmpeg_path
        else:
            os.environ["PATH"] += os.pathsep + self.ffmpeg_path
        # self.logger.info(f"Updated PATH: {os.environ['PATH']}")

    def remove_ffmpeg_env_path(self):
        os.environ["PATH"] = os.pathsep.join(
            [p for p in os.environ["PATH"].split(os.pathsep) if p != self.ffmpeg_path]
        )

    def is_ffmpeg_path_in_env(self):
        return self.ffmpeg_path in os.environ["PATH"]


def mainloop():
    qdarktheme.enable_hi_dpi()
    logs_settings()
    app = QApplication(sys.argv)
    path = resource_path("res/icons/4imask.png")
    app.setWindowIcon(QIcon(path))
    app.setStyle('Fusion')
    qdarktheme.setup_theme("light")
    window = VideoAnonymizer()
    window.show()
    sys.exit(app.exec())


def logs_settings():
    try:
        os.mkdir('logs')
    except FileExistsError:
        pass
    log_dir = 'logs/'
    # List all log files in the directory
    log_files = [f for f in os.listdir(log_dir) if f.endswith('.log')]

    # Sort the log files by creation time
    log_files.sort(key=lambda f: os.path.getctime(os.path.join(log_dir, f)))

    # Keep only the last 10 files
    if len(log_files) > 5:
        for log_file in log_files[:-5]:
            os.remove(os.path.join(log_dir, log_file))

    # Configure the root logger to log messages to a file and the console
    # file_handler = logging.FileHandler('logs/' + 'app.log')
    log_file_path = os.path.join(log_dir, datetime.now().strftime('%Y-%m-%d %H-%M-%S.log'))
    file_handler = logging.FileHandler(log_file_path)
    console_handler = logging.StreamHandler(sys.stdout)

    logging.basicConfig(level=logging.DEBUG,
                        format='Line: %(lineno)d - %(message)s - %(levelname)s - %(name)s',
                        handlers=[file_handler, console_handler])
    # Suppress all Matplotlib loggers
    for logger_name in logging.Logger.manager.loggerDict:
        if logger_name.startswith('matplotlib'):
            logging.getLogger(logger_name).setLevel(logging.WARNING)
    # Function to log uncaught exceptions

    def log_uncaught_exceptions(exctype, value, tb):
        logging.error("Uncaught exception", exc_info=(exctype, value, tb))
        file_handler.flush()
    # Set the exception hook
    sys.excepthook = log_uncaught_exceptions
    # Flush and close the log file
    file_handler.flush()
    file_handler.close()


if __name__ == "__main__":
    mainloop()
