# =============================================================================
# HYDRA-UMC EDITOR-URDF - gallery.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# A short starter list of real, public, currently-active robot-description
# repositories. Each one is verified to
# actually exist and contain real URDF/xacro files before being added
# here (WebFetch against the live repo, not assumed from memory), per
# [[No reference -> reuse, don't invent]]. This is a STARTER list, not a
# curated claim that every URDF this app finds inside these repos will
# pass DOF validation for HYDRA-UMC-STUDIO specifically - the app's own
# existing dof.py check still runs on whatever gets picked, same as any
# other GitHub fetch.
#
# Deliberately a short, hand-picked list rather than an auto-scraped one:
# a "gallery" that silently linked to a dead or malicious repo would be
# worse than no gallery. Add entries here by hand, after actually
# checking the repo exists and is what it claims to be - the same bar
# every entry below was held to.
# =============================================================================
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GalleryEntry:
    name: str
    description: str
    github_url: str  # includes an explicit /tree/<branch> when the repo's default branch isn't "main" (this app's own fetcher accepts both forms)


GALLERY: list[GalleryEntry] = [
    GalleryEntry(
        name="Universal Robots (ur_description)",
        description="ROS-Industrial's official UR3/UR5/UR10/UR16 description package - real xacro-based arms, MoveIt configs included.",
        github_url="https://github.com/ros-industrial/universal_robot/tree/noetic-devel",
    ),
    GalleryEntry(
        name="ROBOTIS OpenMANIPULATOR",
        description="ROBOTIS' own official 4-DOF manipulator description (open_manipulator_description) - a compact real-hardware arm, ROS 2.",
        github_url="https://github.com/ROBOTIS-GIT/open_manipulator",
    ),
]
