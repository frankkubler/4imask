# 4iMask Anonymizer
## Description
4iMask Anonymizer is an application for anonymizing videos using various techniques such as blurring, masking, and mosaicking.

## Features
- Select video to anonymize
- Choose output format (360p, 480p, 720p, 1080p)
- Anonymization options: Mosaic, Blur, Mask
- Pause, resume, and stop anonymization
- Live view of anonymization
- Change detection model (YOLOv11, CenterFace, YUNET)

## Prerequisites
- Python 3.12 or later
- [uv](https://docs.astral.sh/uv/) for dependency management
- PySide6
- OpenCV
- imutils
- skimage
- onnx

For Windows:
- onnxruntime-directml

For Linux:
- onnxruntime-openvino

With NVIDIA GPU:
- onnxruntime-gpu

## Installation
Clone the repository and install the dependencies:
```sh
git clone https://github.com/your-username/4imask.git
cd 4imask
uv sync
```
`uv` creates the virtual environment and installs the exact versions pinned in `uv.lock`.

## Usage
To launch the application, run:
```sh
uv run 4imask_anonymizer.py
```

The interface is bilingual: click the flag at the bottom of the window to switch
between French and English. The flag shows the language currently in use, and the
choice is remembered across launches. Labels live in `apps/i18n.py` — the single
place to edit or extend translations.

## Development
Install the development tools (pytest, ruff, pip-audit, pyinstaller):
```sh
uv sync --group dev
uv run pytest        # tests
uv run ruff check    # linting
uv run pip-audit     # dependency CVE audit
```

## Usage restriction
Released builds can be restricted to a list of Windows domains. The list is **not**
versioned: it is written at build time from the `AUTHORIZED_DOMAINS` repository
secret (one domain per line) into `res/.dummy`, which `.gitignore` excludes.

When no list is embedded — running from source, or building without the secret —
no restriction applies. The check is a usage guard, not a security measure: the
list ships inside the binary and the environment variable it reads is
user-controlled.

## Data protection (GDPR / RGPD)
4iMask processes video that may contain identifiable people. Everything runs locally:
no video, image or usage data ever leaves the machine, and no network connection is made.
The models locate faces, people and posture points — they identify nobody and build no
biometric template.

**Masking covers detected faces, plus heads when the `Back-facing (pose)` option is
enabled — nothing else.** Silhouettes, tattoos, badges, licence plates, screens and
documents remain fully visible in the output. Hiding those requires manual editing.

**The output must not be assumed anonymous without review.** Detection is never
exhaustive, and blur and mosaic reduce information without destroying it. Always watch
the produced video before releasing it.

The application shows this information to the user: a permanent banner in the main
window, a detailed notice on first launch, and a *Privacy / GDPR* link to reopen it at
any time. All of it is available **in French and in English**, like the rest of the
interface; the initial language follows the machine locale (see `apps/privacy.py`).

Full data-protection assessment — data processed, retention, roles, limits of the
anonymisation and the controller's obligations:
**[docs/GDPR.md](./docs/GDPR.md)** (English) · **[docs/RGPD.md](./docs/RGPD.md)**
(français).

## Compilation
The Windows executable is built by the `PyInstaller build` GitHub workflow on every `v*` tag.
To build locally:
```sh
uv sync --group dev
uv run pyinstaller 4imask_anonymizer.py --noconsole --add-data "res:res" --add-data "docs:docs" --add-data "LICENSE:." --add-data "pyproject.toml:." --icon "res/icons/4imask.ico" --hidden-import ultralytics --hidden-import skimage._shared.geometry --collect-submodules openvino --collect-binaries openvino --collect-data openvino
```
No `--splash`: the startup screen is a Qt `QSplashScreen` (`apps/splash.py`), shown
while the detection models load. It works when running from source too, and reports
the current step in the user's language.

## Contribute
Contributions are welcome. Please open an issue or submit a pull request.

## License
This project is licensed under AGPL-3.0. See the [LICENSE](./LICENSE) file for details.

The libraries used in this project are under the following licenses:
- OpenCV: Apache 2.0
- PySide6: LGPL
- imutils: MIT
- skimage: BSD
- onnx: MIT
- onnxruntime-directml: MIT
- onnxruntime-openvino: MIT
- onnxruntime-gpu: MIT
- Ultralytics: AGPL-3.0

## Contact
For any questions, please contact via github issues.

## Sources
- [OpenCV Zoo - Face Detection Yunet](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet)
- [ORB-HD - Deface](https://github.com/ORB-HD/deface)
- [Akanametov - YOLO Face](https://github.com/akanametov/yolo-face)