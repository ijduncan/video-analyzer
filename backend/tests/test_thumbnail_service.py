import asyncio
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from app.services import thumbnail_service


class ThumbnailServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    async def test_midpoint_and_legacy_fallbacks_reach_extractor_without_invalid_shot_blocking_others(self):
        scenes = [{"shots": [
            {"shot_number": 1, "start_time": "00:10.125", "end_time": "00:14.625"},
            {"shot_number": 2, "start_time": "00:05"},
            {"shot_number": 3, "start_time": "00:06", "end_time": "invalid"},
            {"shot_number": 4, "start_time": "00:07", "end_time": "00:07"},
            {"shot_number": 5, "start_time": "00:08", "end_time": "00:01"},
            {"shot_number": 6, "start_time": "invalid", "end_time": "00:09"},
        ]}]
        with patch.object(thumbnail_service, "_extract_frame", AsyncMock(return_value=True)) as extract:
            result = await thumbnail_service.extract_thumbnails("source.mp4", "asset", scenes, str(self.root))
        calls = {Path(call.args[2]).name: call.args[1] for call in extract.call_args_list}
        self.assertEqual(calls, {"shot_1.jpg": 12.375, "shot_2.jpg": 5, "shot_3.jpg": 6,
                                 "shot_4.jpg": 7, "shot_5.jpg": 8})
        self.assertEqual(Path(result), self.root / "asset" / "thumbs")

    async def test_successful_extraction_replaces_stale_frame_only_after_nonempty_output(self):
        target = self.root / "shot_1.jpg"
        target.write_bytes(b"old frame")

        async def start(*args, **_kwargs):
            self.assertEqual(target.read_bytes(), b"old frame")
            temporary = Path(args[-1])
            self.assertNotEqual(temporary, target)
            temporary.write_bytes(b"new midpoint frame")
            return SimpleProcess(returncode=0)

        with patch.object(thumbnail_service.asyncio, "create_subprocess_exec", side_effect=start):
            self.assertTrue(await thumbnail_service._extract_frame("source.mp4", 1.5, str(target)))
        self.assertEqual(target.read_bytes(), b"new midpoint frame")
        self.assertEqual(list(self.root.glob("*.tmp.jpg")), [])

    async def test_failure_or_success_without_frame_removes_stale_evidence(self):
        target = self.root / "shot_1.jpg"
        for returncode, content in ((1, b"partial frame"), (0, None), (0, b"")):
            with self.subTest(returncode=returncode, content=content):
                target.write_bytes(b"old frame")

                async def start(*args, **_kwargs):
                    if content is not None:
                        Path(args[-1]).write_bytes(content)
                    return SimpleProcess(returncode=returncode)

                with patch.object(thumbnail_service.asyncio, "create_subprocess_exec", side_effect=start):
                    self.assertFalse(await thumbnail_service._extract_frame("source.mp4", 100, str(target)))
                self.assertFalse(target.exists())
                self.assertEqual(list(self.root.glob("*.tmp.jpg")), [])

    async def test_cancellation_stops_process_and_removes_partial_and_stale_files(self):
        target = self.root / "shot_1.jpg"
        target.write_bytes(b"old frame")
        waiting = asyncio.Event()
        process = Mock(returncode=None)

        async def wait():
            if process.returncode is None:
                waiting.set()
                await asyncio.Event().wait()
            return process.returncode

        process.wait = AsyncMock(side_effect=wait)
        process.kill.side_effect = lambda: setattr(process, "returncode", -9)

        async def start(*args, **_kwargs):
            Path(args[-1]).write_bytes(b"partial new frame")
            return process

        with patch.object(thumbnail_service.asyncio, "create_subprocess_exec", side_effect=start):
            task = asyncio.create_task(thumbnail_service._extract_frame("source.mp4", 1, str(target)))
            await asyncio.wait_for(waiting.wait(), timeout=1)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        process.kill.assert_called_once()
        self.assertFalse(target.exists())
        self.assertEqual(list(self.root.glob("*.tmp.jpg")), [])

    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg is not installed")
    async def test_real_ffmpeg_thumbnail_is_blue_midpoint_not_red_opening(self):
        video = self.root / "red-then-blue.mp4"
        subprocess.run([
            "ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=red:s=64x64:d=1:r=4",
            "-f", "lavfi", "-i", "color=c=blue:s=64x64:d=1:r=4",
            "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]", "-map", "[v]",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-y", str(video),
        ], check=True, capture_output=True, timeout=15)
        await thumbnail_service.extract_thumbnails(str(video), "asset", [{"shots": [
            {"shot_number": 1, "start_time": "00:00", "end_time": "00:02"},
        ]}], str(self.root))
        frame = self.root / "asset" / "thumbs" / "shot_1.jpg"
        pixels = subprocess.run([
            "ffmpeg", "-loglevel", "error", "-i", str(frame), "-vf", "scale=1:1",
            "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1",
        ], check=True, capture_output=True, timeout=15).stdout
        self.assertEqual(len(pixels), 3)
        self.assertGreater(pixels[2], pixels[0] + 100)


class SimpleProcess:
    def __init__(self, returncode):
        self.returncode = returncode

    async def wait(self):
        return self.returncode
