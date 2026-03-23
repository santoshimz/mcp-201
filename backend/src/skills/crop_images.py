from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Iterable

from PIL import Image


CONTENT_BRIGHTNESS_THRESHOLD = 35.0


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = max(0.0, min(1.0, pct / 100.0)) * (len(ordered) - 1)
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    fraction = rank - low
    return ordered[low] * (1.0 - fraction) + ordered[high] * fraction


def mean(values: Iterable[float]) -> float:
    data = list(values)
    if not data:
        return 0.0
    return sum(data) / len(data)


def sample_positions(start: int, stop: int, target_points: int = 180) -> list[int]:
    length = max(0, stop - start)
    if length == 0:
        return []
    step = max(1, length // target_points)
    positions = list(range(start, stop, step))
    if positions[-1] != stop - 1:
        positions.append(stop - 1)
    return positions


def scan_rows(image: Image.Image, left: int, top: int, right: int, bottom: int) -> tuple[list[float], list[float], list[float]]:
    pixels = image.load()
    xs = sample_positions(left, right)
    energies: list[float] = []
    brightnesses: list[float] = []
    red_ratios: list[float] = []

    for y in range(top, bottom):
        previous = None
        diff_sum = 0.0
        brightness_sum = 0.0
        red_count = 0

        for x in xs:
            r, g, b = pixels[x, y]
            brightness_sum += (0.299 * r) + (0.587 * g) + (0.114 * b)
            if r >= 150 and r >= g + 35 and r >= b + 35:
                red_count += 1
            if previous is not None:
                pr, pg, pb = previous
                diff_sum += abs(r - pr) + abs(g - pg) + abs(b - pb)
            previous = (r, g, b)

        denom = max(1, len(xs) - 1)
        energies.append(diff_sum / denom)
        brightnesses.append(brightness_sum / len(xs))
        red_ratios.append(red_count / len(xs))

    return energies, brightnesses, red_ratios


def smooth(values: Iterable[float], radius: int = 3) -> list[float]:
    data = list(values)
    smoothed: list[float] = []
    for index in range(len(data)):
        start = max(0, index - radius)
        end = min(len(data), index + radius + 1)
        window = data[start:end]
        smoothed.append(sum(window) / len(window))
    return smoothed


def find_band(energies: list[float], brightnesses: list[float], min_run: int) -> tuple[int, int]:
    energy_smooth = smooth(energies)
    brightness_smooth = smooth(brightnesses)
    energy_threshold = max(18.0, percentile(energy_smooth, 70) * 0.52)
    brightness_threshold = max(12.0, percentile(brightness_smooth, 30) * 0.55)

    mask = [
        energy >= energy_threshold
        or (brightness >= brightness_threshold and energy >= energy_threshold * 0.45)
        for energy, brightness in zip(energy_smooth, brightness_smooth)
    ]

    start = 0
    while start < len(mask):
        if all(mask[start : min(len(mask), start + min_run)]):
            break
        start += 1

    end = len(mask) - 1
    while end >= 0:
        run_start = max(0, end - min_run + 1)
        if all(mask[run_start : end + 1]):
            break
        end -= 1

    if start >= end:
        return 0, len(mask)

    return start, end + 1


def fallback_box(width: int, height: int) -> tuple[int, int, int, int]:
    left = int(width * 0.03)
    right = width - int(width * 0.03)
    top = int(height * 0.09)
    bottom = height - int(height * 0.14)
    return left, top, right, bottom


def detect_top_ui_cut(brightnesses: list[float]) -> int | None:
    smoothed = smooth(brightnesses, radius=5)
    run = max(12, len(smoothed) // 60)
    threshold = max(CONTENT_BRIGHTNESS_THRESHOLD, percentile(smoothed, 60) * 0.65)
    tolerance = max(10, len(smoothed) // 80)

    for index in range(0, max(1, len(smoothed) // 2)):
        short_window = smoothed[index : min(len(smoothed), index + run)]
        long_window = smoothed[index : min(len(smoothed), index + (run * 3))]
        if mean(short_window) >= threshold and mean(long_window) >= threshold * 0.9:
            if index >= tolerance:
                return index
            return None
    return None


def detect_bottom_ui_cut(brightnesses: list[float]) -> int | None:
    smoothed = smooth(brightnesses, radius=5)
    run = max(12, len(smoothed) // 60)
    threshold = max(CONTENT_BRIGHTNESS_THRESHOLD, percentile(smoothed, 60) * 0.65)
    tolerance = max(10, len(smoothed) // 80)

    for index in range(len(smoothed) - (run * 2), max(run, len(smoothed) // 2), -1):
        content_rows = smoothed[max(0, index - run) : index]
        quiet_rows = smoothed[index : min(len(smoothed), index + run)]
        trailing_rows = smoothed[index : min(len(smoothed), index + (run * 3))]
        if (
            mean(content_rows) >= threshold
            and mean(quiet_rows) <= threshold * 0.45
            and max(trailing_rows, default=0.0) >= threshold * 0.55
        ):
            if len(smoothed) - index >= tolerance:
                return index
            return None
    return None


def trim_ui_bands(image: Image.Image, left: int, top: int, right: int, bottom: int) -> tuple[int, int]:
    horizontal_margin = max(0, (right - left) // 4)
    scan_left = left + horizontal_margin
    scan_right = right - horizontal_margin
    if scan_right - scan_left < max(120, (right - left) // 2):
        scan_left = left
        scan_right = right

    _, brightnesses, _ = scan_rows(image, scan_left, top, scan_right, bottom)

    for _ in range(2):
        top_cut = detect_top_ui_cut(brightnesses)
        if top_cut is None:
            break
        top += top_cut
        _, brightnesses, _ = scan_rows(image, scan_left, top, scan_right, bottom)

    bottom_cut = detect_bottom_ui_cut(brightnesses)
    if bottom_cut is not None:
        bottom = top + bottom_cut

    return top, bottom


def trim_red_seek_bar(image: Image.Image, left: int, top: int, right: int, bottom: int) -> int:
    probe_height = min(160, max(30, (bottom - top) // 3))
    probe_top = max(top, bottom - probe_height)
    _, brightnesses, red_ratios = scan_rows(image, left, probe_top, right, bottom)
    cut_row: int | None = None

    for offset in range(len(red_ratios) - 1, -1, -1):
        if red_ratios[offset] >= 0.02 and brightnesses[offset] >= 10:
            cut_row = max(top + 1, probe_top + offset - 3)

    return cut_row if cut_row is not None else bottom


def detect_crop_box(image: Image.Image) -> tuple[int, int, int, int]:
    rgb = image.convert("RGB")
    width, height = rgb.size

    row_start, row_end = find_band(*scan_rows(rgb, 0, 0, width, height)[:2], min_run=max(6, height // 140))
    top = row_start
    bottom = row_end

    if bottom - top < int(height * 0.45):
        return fallback_box(width, height)

    top, bottom = trim_ui_bands(rgb, 0, top, width, bottom)
    bottom = trim_red_seek_bar(rgb, 0, top, width, bottom)
    top, bottom = trim_ui_bands(rgb, 0, top, width, bottom)
    top = min(bottom - 1, top + max(2, height // 300))
    bottom = max(top + 1, bottom - max(3, height // 200))

    if bottom - top < int(height * 0.35):
        return fallback_box(width, height)

    return 0, max(0, top), width, min(height, bottom)


def validate_crop_box(image: Image.Image, crop_box: tuple[int, int, int, int]) -> None:
    left, top, right, bottom = crop_box
    width, height = image.size
    if right - left < int(width * 0.45) or bottom - top < int(height * 0.35):
        raise RuntimeError(f"Crop box is too small: {crop_box}")


def crop_image_bytes(image_bytes: bytes) -> bytes:
    with Image.open(BytesIO(image_bytes)) as image:
        rgb = image.convert("RGB")
        crop_box = detect_crop_box(rgb)
        validate_crop_box(rgb, crop_box)
        cropped = rgb.crop(crop_box)
        with BytesIO() as output:
            cropped.save(output, format="JPEG", quality=95, optimize=True)
            return output.getvalue()


def output_filename(source_name: str) -> str:
    return f"{Path(source_name).stem}-cropped.jpg"
