"""Reusable ArUco marker detection and center geometry."""

from pathlib import Path

import cv2
import numpy as np


def aruco_dictionary(family):
  name = str(family or "6X6_250")
  if not name.startswith("DICT_"):
    name = "DICT_" + name
  candidates = [name, name.upper()]
  for candidate in candidates:
    if hasattr(cv2.aruco, candidate):
      return cv2.aruco.getPredefinedDictionary(
        getattr(cv2.aruco, candidate)
      ), candidate
  available = sorted(
    value[5:] for value in dir(cv2.aruco)
    if value.startswith("DICT_")
  )
  raise ValueError(
    "unknown marker_family {}; available families include {}".format(
      family, ", ".join(available)
    )
  )


def diagonal_center(corners):
  """Return the projectively correct intersection of marker diagonals."""
  points = np.asarray(corners, dtype=np.float64).reshape(4, 2)
  homogeneous = np.column_stack([points, np.ones(4)])
  diagonal_02 = np.cross(homogeneous[0], homogeneous[2])
  diagonal_13 = np.cross(homogeneous[1], homogeneous[3])
  center = np.cross(diagonal_02, diagonal_13)
  if abs(center[2]) < 1e-12:
    raise ValueError("marker diagonals do not have a finite intersection")
  return center[:2] / center[2]


def marker_center(corners, camera=None):
  points = np.asarray(corners, dtype=np.float64).reshape(4, 2)
  if camera is None:
    return diagonal_center(points)

  intrinsic = np.asarray(camera["K"], dtype=np.float64)
  distortion = np.asarray(camera["dist"], dtype=np.float64).reshape(-1)
  normalized = cv2.undistortPoints(
    points.reshape(-1, 1, 2),
    intrinsic,
    distortion
  ).reshape(4, 2)
  normalized_center = diagonal_center(normalized)
  distorted_center, _ = cv2.projectPoints(
    np.array([
      [normalized_center[0], normalized_center[1], 1.0]
    ], dtype=np.float64),
    np.zeros(3),
    np.zeros(3),
    intrinsic,
    distortion
  )
  return distorted_center.reshape(2)


def _same_marker_detection(left, right):
  """Return whether two detections represent the same physical marker."""
  edge_lengths = []
  for detection in (left, right):
    corners = np.asarray(detection["corners"], dtype=np.float64)
    edge_lengths.extend(
      np.linalg.norm(corners - np.roll(corners, 1, axis=0), axis=1)
    )
  marker_edge = float(np.median(edge_lengths))
  center_distance = np.linalg.norm(left["center"] - right["center"])
  return center_distance < max(5.0, marker_edge * 0.25)


def detect_marker_centers(
    image_file, family, camera=None, preserve_duplicates=False):
  image_path = Path(image_file)
  image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
  if image is None:
    raise ValueError("could not read marker image {}".format(image_path))
  gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
  dictionary, dictionary_name = aruco_dictionary(family)
  detected = {}
  # Large close-range markers and small distant markers can require very
  # different adaptive-threshold scales. Detect at several resolutions, map
  # corners back to the original image and retain the highest-resolution hit.
  for scale in (1.0, 0.75, 0.5, 0.25):
    scaled = (
      gray if scale == 1.0 else
      cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    )
    parameters = cv2.aruco.DetectorParameters_create()
    parameters.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
    corners, ids, _ = cv2.aruco.detectMarkers(
      scaled, dictionary, parameters=parameters
    )
    if ids is None:
      continue
    for marker_id, marker_corners in zip(ids.reshape(-1), corners):
      marker_id = int(marker_id)
      if not preserve_duplicates and marker_id in detected:
        continue
      refined_corners = (
        np.asarray(marker_corners, dtype=np.float32).reshape(4, 2) /
        float(scale)
      )
      cv2.cornerSubPix(
        gray,
        refined_corners,
        (5, 5),
        (-1, -1),
        (
          cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
          30,
          0.01
        )
      )
      refined_corners = refined_corners.astype(np.float64)
      detection = {
        "corners": refined_corners,
        "center": marker_center(refined_corners, camera)
      }
      if preserve_duplicates:
        instances = detected.setdefault(marker_id, [])
        # The same physical marker can be found again at another image
        # scale. Keep spatially distinct instances, not scale duplicates.
        if any(
            _same_marker_detection(existing, detection)
            for existing in instances):
          continue
        instances.append(detection)
      else:
        detected[marker_id] = detection
  return image, detected, dictionary_name
