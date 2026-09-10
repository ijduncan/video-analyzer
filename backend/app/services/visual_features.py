"""Local, explainable visual measurements. Scores are not model confidence."""
import math

import cv2
import numpy as np


def describe(image):
    aspect_ratio = image.shape[1] / image.shape[0]
    scale = 320 / max(image.shape[:2])
    image = cv2.resize(image, (max(1, round(image.shape[1] * scale)), max(1, round(image.shape[0] * scale))))
    height, width = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1, 2], None, [12, 4, 4], [0, 180, 0, 256, 0, 256]).flatten()
    hist /= max(float(hist.sum()), 1)
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    layout = cv2.resize(lab, (4, 4), interpolation=cv2.INTER_AREA).astype(float) / 255
    edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 40, 100)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    shapes = []
    for contour in sorted(contours, key=cv2.contourArea, reverse=True):
        area = cv2.contourArea(contour)
        x, y, w, h = cv2.boundingRect(contour)
        if area < width * height * .0017 or area > width * height * .85 or w < 8 or h < 8:
            continue
        box = [x / width, y / height, w / width, h / height]
        if any(sum(abs(a - b) for a, b in zip(box, s['box'])) < .06 for s in shapes):
            continue
        perimeter = cv2.arcLength(contour, True)
        hu = cv2.HuMoments(cv2.moments(contour)).flatten()[:4]
        hu = (-np.sign(hu) * np.log10(np.abs(hu) + 1e-12)).tolist()
        shapes.append({'box': box, 'hu': hu, 'roundness': min(1., 4 * math.pi * area / max(perimeter ** 2, 1)),
                       'fill': area / (w * h), 'aspect': w / h})
        if len(shapes) >= 12:
            break
    return {'color': hist.tolist(), 'layout': layout.flatten().tolist(), 'aspect_ratio': aspect_ratio,
            'edges': (cv2.resize(edges, (12, 8), interpolation=cv2.INTER_AREA) / 255).flatten().tolist(),
            'shapes': shapes, 'usable': bool(gray.std() >= 7 and (gray > 25).mean() >= .005)}


def compare(source, target, weights, region=None):
    color = float(np.minimum(source['color'], target['color']).sum())
    layout = math.exp(-6 * float(np.mean(np.abs(np.array(source['layout']) - target['layout']))))
    edges = math.exp(-8 * float(np.mean(np.abs(np.array(source['edges']) - target['edges']))))
    composition = .55 * layout + .45 * edges
    source_shapes = source['shapes'][:5]
    if region:
        x, y, w, h = region
        source_shapes = [s for s in source['shapes'] if x <= s['box'][0] + s['box'][2] / 2 <= x + w
                         and y <= s['box'][1] + s['box'][3] / 2 <= y + h]
    best = None
    for a in source_shapes:
        for b in target['shapes']:
            # Hu invariants compare form; screen coordinates retain framing/scale.
            form = math.exp(-float(np.mean(np.abs(np.array(a['hu'])[:2] - np.array(b['hu'])[:2]))))
            form *= math.exp(-2 * abs(a['roundness'] - b['roundness']) - abs(a['fill'] - b['fill']))
            form *= math.exp(-abs(math.log(a['aspect'] / b['aspect'])))
            position = math.exp(-3 * sum(abs(v - u) for v, u in zip(a['box'], b['box'])))
            rank = weights['shape'] * form + weights['composition'] * position
            if best is None or rank > best[0]:
                best = (rank, form, position, a['box'], b['box'])
    shape = best[1] if best else 0.
    if best:
        composition = .5 * composition + .5 * best[2]
    scores = {'shape': shape, 'composition': composition, 'color': color}
    total = sum(weights.values())
    score = sum(scores[k] * weights[k] for k in scores) / total
    return {'score': round(score, 4), 'scores': {k: round(v, 4) for k, v in scores.items()},
            'source_box': best[3] if best else None, 'target_box': best[4] if best else None}
