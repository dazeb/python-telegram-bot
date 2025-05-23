#!/usr/bin/env python
#
# A library that provides a Python interface to the Telegram Bot API
# Copyright (C) 2015-2025
# Leandro Toledo de Souza <devs@python-telegram-bot.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser Public License for more details.
#
# You should have received a copy of the GNU Lesser Public License
# along with this program.  If not, see [http://www.gnu.org/licenses/].
import contextlib
import subprocess
import sys
from io import BufferedReader, BytesIO

import pytest

from telegram import InputFile
from telegram._utils.strings import TextEncoding
from tests.auxil.files import data_file
from tests.auxil.slots import mro_slots


@pytest.fixture(scope="module")
def png_file():
    return data_file("game.png")


class TestInputFileWithoutRequest:
    def test_slot_behaviour(self):
        inst = InputFile(BytesIO(b"blah"), filename="tg.jpg")
        for attr in inst.__slots__:
            assert getattr(inst, attr, "err") != "err", f"got extra slot '{attr}'"
        assert len(mro_slots(inst)) == len(set(mro_slots(inst))), "duplicate slot"

    def test_subprocess_pipe(self, png_file):
        cmd_str = "type" if sys.platform == "win32" else "cat"
        cmd = [cmd_str, str(png_file)]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=(sys.platform == "win32"))
        in_file = InputFile(proc.stdout)

        assert in_file.input_file_content == png_file.read_bytes()
        assert in_file.mimetype == "application/octet-stream"
        assert in_file.filename == "application.octet-stream"

        with contextlib.suppress(ProcessLookupError):
            proc.kill()
            # This exception may be thrown if the process has finished before we had the chance
            # to kill it.

    @pytest.mark.parametrize("attach", [True, False])
    def test_attach(self, attach):
        input_file = InputFile("contents", attach=attach)
        if attach:
            assert isinstance(input_file.attach_name, str)
            assert input_file.attach_uri == f"attach://{input_file.attach_name}"
        else:
            assert input_file.attach_name is None
            assert input_file.attach_uri is None

    @pytest.mark.parametrize("read_file_handle", [True, False])
    def test_mimetypes_file_handle(self, read_file_handle):
        # Only test a few to make sure logic works okay
        assert (
            InputFile(
                data_file("telegram.jpg").open("rb"), read_file_handle=read_file_handle
            ).mimetype
            == "image/jpeg"
        )
        # For some reason python can guess the type on macOS
        assert InputFile(
            data_file("telegram.webp").open("rb"), read_file_handle=read_file_handle
        ).mimetype in [
            "application/octet-stream",
            "image/webp",
        ]
        assert (
            InputFile(
                data_file("telegram.mp3").open("rb"), read_file_handle=read_file_handle
            ).mimetype
            == "audio/mpeg"
        )
        # For some reason windows drops the trailing i
        assert InputFile(
            data_file("telegram.midi").open("rb"), read_file_handle=read_file_handle
        ).mimetype in [
            "audio/mid",
            "audio/midi",
        ]

        # Test string file
        assert (
            InputFile(
                data_file("text_file.txt").open("rb"), read_file_handle=read_file_handle
            ).mimetype
            == "text/plain"
        )

    def test_mimetypes_other(self):
        # Test guess from file
        assert InputFile(BytesIO(b"blah"), filename="tg.jpg").mimetype == "image/jpeg"
        assert InputFile(BytesIO(b"blah"), filename="tg.mp3").mimetype == "audio/mpeg"

        # Test fallback
        assert (
            InputFile(BytesIO(b"blah"), filename="tg.notaproperext").mimetype
            == "application/octet-stream"
        )
        assert InputFile(BytesIO(b"blah")).mimetype == "application/octet-stream"

    @pytest.mark.parametrize("read_file_handle", [True, False])
    def test_filenames(self, read_file_handle):
        assert (
            InputFile(
                data_file("telegram.jpg").open("rb"), read_file_handle=read_file_handle
            ).filename
            == "telegram.jpg"
        )
        assert (
            InputFile(
                data_file("telegram.jpg").open("rb"),
                filename="blah",
                read_file_handle=read_file_handle,
            ).filename
            == "blah"
        )
        assert (
            InputFile(
                data_file("telegram.jpg").open("rb"),
                filename="blah.jpg",
                read_file_handle=read_file_handle,
            ).filename
            == "blah.jpg"
        )
        assert (
            InputFile(data_file("telegram").open("rb"), read_file_handle=read_file_handle).filename
            == "telegram"
        )
        assert (
            InputFile(
                data_file("telegram").open("rb"),
                filename="blah",
                read_file_handle=read_file_handle,
            ).filename
            == "blah"
        )
        assert (
            InputFile(
                data_file("telegram").open("rb"),
                filename="blah.jpg",
                read_file_handle=read_file_handle,
            ).filename
            == "blah.jpg"
        )

        class MockedFileobject:
            # A open(?, 'rb') without a .name
            def __init__(self, f):
                self.f = f.open("rb")

            def read(self):
                return self.f.read()

        assert (
            InputFile(MockedFileobject(data_file("telegram.jpg"))).filename
            == "application.octet-stream"
        )
        assert (
            InputFile(MockedFileobject(data_file("telegram.jpg")), filename="blah").filename
            == "blah"
        )
        assert (
            InputFile(MockedFileobject(data_file("telegram.jpg")), filename="blah.jpg").filename
            == "blah.jpg"
        )
        assert (
            InputFile(MockedFileobject(data_file("telegram"))).filename
            == "application.octet-stream"
        )
        assert (
            InputFile(MockedFileobject(data_file("telegram")), filename="blah").filename == "blah"
        )
        assert (
            InputFile(MockedFileobject(data_file("telegram")), filename="blah.jpg").filename
            == "blah.jpg"
        )

    @pytest.mark.parametrize("read_file_handle", [True, False])
    def test_read_file_handle(self, read_file_handle):
        input_file = InputFile(
            data_file("telegram.jpg").open("rb"), read_file_handle=read_file_handle
        )
        content = input_file.field_tuple[1]
        if read_file_handle:
            assert isinstance(content, bytes)
            assert content == data_file("telegram.jpg").read_bytes()
        else:
            assert isinstance(content, BufferedReader)
            assert content.read() == data_file("telegram.jpg").read_bytes()


class TestInputFileWithRequest:
    async def test_send_bytes(self, bot, chat_id):
        # We test this here and not at the respective test modules because it's not worth
        # duplicating the test for the different methods
        message = await bot.send_document(chat_id, data_file("text_file.txt").read_bytes())
        out = BytesIO()

        await (await message.document.get_file()).download_to_memory(out=out)
        out.seek(0)

        assert out.read().decode(TextEncoding.UTF_8) == "PTB Rocks! ⅞"

    async def test_send_string(self, bot, chat_id):
        # We test this here and not at the respective test modules because it's not worth
        # duplicating the test for the different methods
        message = await bot.send_document(
            chat_id, InputFile(data_file("text_file.txt").read_text(encoding=TextEncoding.UTF_8))
        )
        out = BytesIO()

        await (await message.document.get_file()).download_to_memory(out=out)
        out.seek(0)

        assert out.read().decode(TextEncoding.UTF_8) == "PTB Rocks! ⅞"
