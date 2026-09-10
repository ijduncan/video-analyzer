"""Nominal editing rates need complete source timing evidence, not average rounding."""
from fractions import Fraction

import pytest

from app.services.media_probe import _packet_cadence


def source_timing(count=2239, extra_ticks=0):
    video = {'r_frame_rate': '24000/1001', 'avg_frame_rate': '100755000/4202323',
             'time_base': '1/90000', 'nb_frames': str(count)}
    period = Fraction(15015, 4) + extra_ticks
    packets = [{'pts': round(index * period)} for index in range(count)]
    return video, packets


def test_nominal_rate_requires_complete_quantized_presentation_cadence():
    video, packets = source_timing()
    result = _packet_cadence(video, list(reversed(packets)))  # Presentation order differs from decode order.
    assert result['nominal_frame_rate_fraction'] == '24000/1001'
    assert result['nominal_frame_rate_verified'] is True
    assert result['frame_rate_verification'] == 'ffprobe_full_packet_pts'
    assert result['frame_rate_verified_frames'] == 2239
    assert video['avg_frame_rate'] == '100755000/4202323'


def test_small_systematic_per_frame_drift_cannot_pass_as_constant_nominal_rate():
    video, packets = source_timing(extra_ticks=1)
    assert _packet_cadence(video, packets)['nominal_frame_rate_verified'] is False


@pytest.mark.parametrize('failure', ['missing_packet', 'missing_pts', 'duplicate_pts', 'irregular', 'unknown_count', 'unknown_rate'])
def test_incomplete_or_irregular_cadence_never_becomes_verified(failure):
    video, packets = source_timing(20)
    if failure == 'missing_packet':
        packets.pop()
    elif failure == 'missing_pts':
        packets[2] = {}
    elif failure == 'duplicate_pts':
        packets[2]['pts'] = packets[1]['pts']
    elif failure == 'irregular':
        packets[10]['pts'] += 500
    elif failure == 'unknown_count':
        video['nb_frames'] = 'N/A'
    else:
        video['r_frame_rate'] = '0/0'
    result = _packet_cadence(video, packets)
    assert result['nominal_frame_rate_verified'] is False
    assert result['frame_rate_verification'] == 'unverified'
