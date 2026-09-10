"""Compare one fixed silhouette across objects. Labels never influence the score."""
import base64
import math

import cv2
import numpy as np
from pydantic import BaseModel, Field, model_validator


class Form(BaseModel):
    label: str = Field(min_length=1, max_length=160)
    # Whole-image coordinates, not coordinates relative to the object's box.
    outline: list[list[float]] = Field(min_length=3, max_length=96)

    @model_validator(mode='after')
    def geometry(self):
        if any(len(p) != 2 or not all(math.isfinite(v) and 0 <= v <= 1000 for v in p) for p in self.outline):
            raise ValueError('Invalid silhouette coordinates')
        pts = np.array(self.outline, np.float32)
        if cv2.contourArea(pts) < 400 or np.min(np.ptp(pts, axis=0)) < 10:
            raise ValueError('Silhouette is too small or degenerate')
        # Reject crossings: a self-intersecting outline is not a usable mask.
        def cross(a, b, c):
            u, v = b-a, c-a
            return float(u[0]*v[1]-u[1]*v[0])
        for i in range(len(pts)):
            a, b = pts[i], pts[(i+1) % len(pts)]
            for j in range(i+2, len(pts)):
                if i == 0 and j == len(pts)-1:
                    continue
                c, d = pts[j], pts[(j+1) % len(pts)]
                if cross(a, b, c)*cross(a, b, d) < 0 and cross(c, d, a)*cross(c, d, b) < 0:
                    raise ValueError('Silhouette outline crosses itself')
        return self


def describe(form, aspect):
    points = np.array(form['outline'], dtype=float) / 1000
    lo, hi = points.min(axis=0), points.max(axis=0)
    box = [*lo.tolist(), *(hi-lo).tolist()]
    # Preserve physical proportions even between portrait and landscape sources.
    pixels = points * [aspect, 1]
    size = np.ptp(pixels, axis=0)
    normalized = (pixels - (pixels.min(axis=0) + pixels.max(axis=0)) / 2) / max(size) * 54 + 31.5
    mask = np.zeros((64, 64), np.uint8)
    cv2.fillPoly(mask, [np.round(normalized).astype(np.int32)], 1)
    return {**form, 'box': box, 'mask': base64.b64encode(np.packbits(mask).tobytes()).decode(),
            'area': float(cv2.contourArea(pixels.astype(np.float32))), 'aspect_ratio': aspect}


def select(forms, region=None, form_id=None):
    if form_id is not None:
        if not 0 <= form_id < len(forms):
            raise ValueError('This shape is no longer available. Identify shapes again.')
        return forms[form_id]
    if not forms:
        return None
    if not region:
        return forms[0]  # Provider salience order; fixed before any candidate is scored.
    x, y, w, h = region
    def overlap(form):
        a, b, c, d = form['box']
        intersection = max(0, min(x+w, a+c)-max(x, a)) * max(0, min(y+h, b+d)-max(y, b))
        return intersection / max(w*h+c*d-intersection, 1e-9)
    best = max(forms, key=overlap)
    if overlap(best) < .18:
        raise ValueError('No identified shape fits that region. Draw around a visible object or choose one from the Shape list.')
    return best


def compare(source, target, align=False):
    def mask(form):
        return np.unpackbits(np.frombuffer(base64.b64decode(form['mask']), np.uint8)).reshape(64, 64).astype(bool)
    a, b = mask(source), mask(target)
    iou = float((a & b).sum() / max((a | b).sum(), 1))
    # Actual mask overlap retains a useful tolerance for approximate model boundaries.
    silhouette = iou
    ax, ay, aw, ah = source['box']; bx, by, bw, bh = target['box']
    position = math.exp(-4 * math.hypot(ax+aw/2-bx-bw/2, ay+ah/2-by-bh/2))
    # Screen occupancy is distinct from the uniform scale used to compare form.
    scale = math.exp(-abs(math.log(max(aw*ah, 1e-9) / max(bw*bh, 1e-9))))
    if silhouette < .78 or (align and (position < .65 or scale < .6)):
        return None
    return {'score': round(.7*silhouette+.2*position+.1*scale if align else silhouette, 4),
            'silhouette': round(silhouette, 4), 'position': round(position, 4), 'scale': round(scale, 4)}
