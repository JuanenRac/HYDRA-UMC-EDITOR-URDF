# =============================================================================
# HYDRA-UMC EDITOR-URDF - ui/about_dialog.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Real About dialog, matching HYDRA-UMC-STUDIO's own About.tsx and
# HYDRA-UMC-SUITE's own ui/about_dialog.py: animated logo, colored
# HYDRA-UM-C wordmark, tagline, one-paragraph description, and a real
# Version/Author/Email/License info block - not a single-line QMessageBox.
# =============================================================================
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from hydra_editor_urdf.i18n import _

AUTHOR_NAME = "JuanenRac (Electro Hobby 3D)"
AUTHOR_EMAIL = "electrohobby3d@gmail.com"
LICENSE_NAME = "GNU General Public License v3.0 (GPL-3.0)"

# Same accent triad as HYDRA-UMC-SUITE's own command deck/About dialog -
# keeps every desktop tool in this ecosystem visually consistent.
_COLOR_EMERALD = "#43db9b"
_COLOR_ROSE = "#ee6b80"
_COLOR_CYAN = "#38d4e6"


class AboutDialog(QDialog):
    def __init__(self, version: str, logo_path: Path | None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("aboutDialog")
        self.setWindowTitle(_("TITLE_ABOUT"))
        self.setFixedWidth(440)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 20)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        if logo_path is not None and logo_path.is_file():
            logo = QSvgWidget(str(logo_path), self)
            logo.renderer().setAnimationEnabled(True)
            logo.setFixedSize(88, 88)
            logo_row = QHBoxLayout()
            logo_row.addStretch()
            logo_row.addWidget(logo)
            logo_row.addStretch()
            layout.addLayout(logo_row)
            layout.addSpacing(8)

        title = QLabel(
            f'HYDRA<span style="color:{_COLOR_EMERALD};">-UM</span>'
            f'<span style="color:{_COLOR_ROSE};">C</span>'
            f' <span style="color:{_COLOR_CYAN};">EDITOR-URDF</span>'
        )
        title.setObjectName("aboutTitle")
        title.setTextFormat(Qt.TextFormat.RichText)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setWordWrap(True)
        layout.addWidget(title)

        tagline = QLabel(_("ABOUT_TAGLINE"))
        tagline.setObjectName("aboutTagline")
        tagline.setWordWrap(True)
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(tagline)

        description = QLabel(_("ABOUT_DESCRIPTION"))
        description.setObjectName("aboutDescription")
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(description)

        layout.addSpacing(6)
        layout.addWidget(_info_row(_("ABOUT_VERSION"), version))
        layout.addWidget(_info_row(_("ABOUT_AUTHOR"), AUTHOR_NAME))
        email_value = QLabel(f'<a href="mailto:{AUTHOR_EMAIL}">{AUTHOR_EMAIL}</a>')
        email_value.setObjectName("aboutInfoValue")
        email_value.setOpenExternalLinks(True)
        layout.addWidget(_info_row(_("ABOUT_EMAIL"), value_widget=email_value))
        layout.addWidget(_info_row(_("ABOUT_LICENSE"), LICENSE_NAME))

        layout.addSpacing(10)
        close_button = QPushButton(_("BTN_CLOSE"))
        close_button.setObjectName("aboutCloseButton")
        close_button.clicked.connect(self.accept)
        close_row = QHBoxLayout()
        close_row.addStretch()
        close_row.addWidget(close_button)
        close_row.addStretch()
        layout.addLayout(close_row)


def _info_row(label: str, value: str | None = None, value_widget: QWidget | None = None) -> QWidget:
    row = QWidget()
    row.setObjectName("aboutInfoRow")
    row_layout = QHBoxLayout(row)
    row_layout.setContentsMargins(10, 6, 10, 6)
    label_widget = QLabel(label.upper())
    label_widget.setObjectName("aboutInfoLabel")
    row_layout.addWidget(label_widget)
    row_layout.addStretch()
    if value_widget is not None:
        row_layout.addWidget(value_widget)
    else:
        value_label = QLabel(value)
        value_label.setObjectName("aboutInfoValue")
        row_layout.addWidget(value_label)
    return row
