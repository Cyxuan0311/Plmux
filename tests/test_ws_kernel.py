
from plmux.web._c_extension._ws_kernel import (
    FrameParser,
    encode,
    encode_text_frame,
    encode_binary_frame,
    encode_close_frame,
    encode_pong_frame,
    OPCODE_TEXT,
    OPCODE_BINARY,
    OPCODE_CLOSE,
    OPCODE_PING,
    OPCODE_PONG,
)


def _build_masked_text_frame(payload: str, mask_key: bytes = b"\x37\xfa\x21\x3d") -> bytes:
    payload_bytes = payload.encode("utf-8")
    length = len(payload_bytes)
    frame = bytearray()
    frame.append(0x81)
    if length < 126:
        frame.append(0x80 | length)
    elif length < 65536:
        frame.append(0x80 | 126)
        frame.extend(length.to_bytes(2, "big"))
    else:
        frame.append(0x80 | 127)
        frame.extend(length.to_bytes(8, "big"))
    frame.extend(mask_key)
    for i in range(length):
        frame.append(payload_bytes[i] ^ mask_key[i % 4])
    return bytes(frame)


def _build_unmasked_text_frame(payload: str) -> bytes:
    payload_bytes = payload.encode("utf-8")
    length = len(payload_bytes)
    frame = bytearray()
    frame.append(0x81)
    if length < 126:
        frame.append(length)
    elif length < 65536:
        frame.append(126)
        frame.extend(length.to_bytes(2, "big"))
    else:
        frame.append(127)
        frame.extend(length.to_bytes(8, "big"))
    frame.extend(payload_bytes)
    return bytes(frame)


def _build_ping_frame(payload: bytes = b"", mask_key: bytes = b"\x37\xfa\x21\x3d") -> bytes:
    length = len(payload)
    frame = bytearray()
    frame.append(0x89)
    frame.append(0x80 | length)
    frame.extend(mask_key)
    for i in range(length):
        frame.append(payload[i] ^ mask_key[i % 4])
    return bytes(frame)


def _build_close_frame(mask_key: bytes = b"\x37\xfa\x21\x3d") -> bytes:
    frame = bytearray()
    frame.append(0x88)
    frame.append(0x80)
    frame.extend(mask_key)
    return bytes(frame)


class TestFrameParserInit:
    def test_create_parser(self):
        p = FrameParser()
        assert p is not None

    def test_parse_empty(self):
        p = FrameParser()
        frames = p.parse()
        assert frames == []


class TestFrameParserMaskedText:
    def test_parse_short_text(self):
        p = FrameParser()
        raw = _build_masked_text_frame("hello")
        p.feed(raw)
        frames = p.parse()
        assert len(frames) == 1
        opcode, payload = frames[0]
        assert opcode == OPCODE_TEXT
        assert payload == "hello"

    def test_parse_empty_text(self):
        p = FrameParser()
        raw = _build_masked_text_frame("")
        p.feed(raw)
        frames = p.parse()
        assert len(frames) == 1
        opcode, payload = frames[0]
        assert opcode == OPCODE_TEXT
        assert payload == ""

    def test_parse_unicode_text(self):
        p = FrameParser()
        raw = _build_masked_text_frame("你好世界")
        p.feed(raw)
        frames = p.parse()
        assert len(frames) == 1
        opcode, payload = frames[0]
        assert payload == "你好世界"

    def test_parse_medium_text(self):
        text = "A" * 200
        p = FrameParser()
        raw = _build_masked_text_frame(text)
        p.feed(raw)
        frames = p.parse()
        assert len(frames) == 1
        opcode, payload = frames[0]
        assert opcode == OPCODE_TEXT
        assert len(payload) == 200


class TestFrameParserUnmaskedText:
    def test_parse_unmasked_text(self):
        p = FrameParser()
        raw = _build_unmasked_text_frame("world")
        p.feed(raw)
        frames = p.parse()
        assert len(frames) == 1
        opcode, payload = frames[0]
        assert opcode == OPCODE_TEXT
        assert payload == "world"


class TestFrameParserMultipleFrames:
    def test_parse_two_frames(self):
        p = FrameParser()
        raw1 = _build_masked_text_frame("first")
        raw2 = _build_masked_text_frame("second")
        p.feed(raw1 + raw2)
        frames = p.parse()
        assert len(frames) == 2
        assert frames[0][1] == "first"
        assert frames[1][1] == "second"

    def test_parse_incremental_feed(self):
        p = FrameParser()
        raw = _build_masked_text_frame("hello")
        half = raw[:3]
        rest = raw[3:]
        p.feed(half)
        frames = p.parse()
        assert len(frames) == 0
        p.feed(rest)
        frames = p.parse()
        assert len(frames) == 1
        assert frames[0][1] == "hello"


class TestFrameParserControlFrames:
    def test_parse_ping(self):
        p = FrameParser()
        raw = _build_ping_frame(b"ping")
        p.feed(raw)
        frames = p.parse()
        assert len(frames) == 1
        opcode, payload = frames[0]
        assert opcode == OPCODE_PING
        assert payload == b"ping"

    def test_parse_close(self):
        p = FrameParser()
        raw = _build_close_frame()
        p.feed(raw)
        frames = p.parse()
        assert len(frames) == 1
        opcode, _ = frames[0]
        assert opcode == OPCODE_CLOSE


class TestEncodeTextFrame:
    def test_encode_short_text(self):
        frame = encode_text_frame("hello")
        assert isinstance(frame, bytes)
        assert frame[0] == 0x81
        assert frame[1] == 5
        assert frame[2:] == b"hello"

    def test_encode_empty_text(self):
        frame = encode_text_frame("")
        assert isinstance(frame, bytes)
        assert frame[0] == 0x81
        assert frame[1] == 0
        assert len(frame) == 2

    def test_encode_unicode_text(self):
        text = "你好"
        frame = encode_text_frame(text)
        assert isinstance(frame, bytes)
        assert frame[0] == 0x81
        payload = frame[2:]
        assert payload.decode("utf-8") == text

    def test_encode_medium_text(self):
        text = "X" * 200
        frame = encode_text_frame(text)
        assert isinstance(frame, bytes)
        assert frame[0] == 0x81
        assert frame[1] == 126
        length = int.from_bytes(frame[2:4], "big")
        assert length == 200


class TestEncodeBinaryFrame:
    def test_encode_binary(self):
        data = b"\x00\x01\x02\x03"
        frame = encode_binary_frame(data)
        assert isinstance(frame, bytes)
        assert frame[0] == 0x82
        assert frame[1] == 4
        assert frame[2:] == data

    def test_encode_empty_binary(self):
        frame = encode_binary_frame(b"")
        assert isinstance(frame, bytes)
        assert frame[0] == 0x82
        assert frame[1] == 0


class TestEncodeCloseFrame:
    def test_encode_close(self):
        frame = encode_close_frame()
        assert isinstance(frame, bytes)
        assert frame[0] == 0x88
        assert frame[1] == 0


class TestEncodePongFrame:
    def test_encode_pong_empty(self):
        frame = encode_pong_frame()
        assert isinstance(frame, bytes)
        assert frame[0] == 0x8A
        assert frame[1] == 0

    def test_encode_pong_with_data(self):
        frame = encode_pong_frame(b"pong")
        assert isinstance(frame, bytes)
        assert frame[0] == 0x8A
        assert frame[1] == 4
        assert frame[2:] == b"pong"


class TestEncodeGeneric:
    def test_encode_text_opcode(self):
        frame = encode(OPCODE_TEXT, b"test")
        assert isinstance(frame, bytes)
        assert frame[0] == 0x81

    def test_encode_binary_opcode(self):
        frame = encode(OPCODE_BINARY, b"\xff\xfe")
        assert isinstance(frame, bytes)
        assert frame[0] == 0x82


class TestRoundTrip:
    def test_encode_parse_roundtrip(self):
        original = "Hello, World!"
        frame = encode_text_frame(original)
        p = FrameParser()
        p.feed(frame)
        frames = p.parse()
        assert len(frames) == 1
        opcode, payload = frames[0]
        assert opcode == OPCODE_TEXT
        assert payload == original

    def test_binary_roundtrip(self):
        original = b"\x00\x01\x02\xff\xfe\xfd"
        frame = encode_binary_frame(original)
        p = FrameParser()
        p.feed(frame)
        frames = p.parse()
        assert len(frames) == 1
        opcode, payload = frames[0]
        assert opcode == OPCODE_BINARY
        assert payload == original

    def test_multiple_roundtrip(self):
        texts = ["first", "second", "third"]
        combined = b""
        for t in texts:
            combined += encode_text_frame(t)
        p = FrameParser()
        p.feed(combined)
        frames = p.parse()
        assert len(frames) == 3
        for i, (_, payload) in enumerate(frames):
            assert payload == texts[i]


class TestOpcodes:
    def test_opcode_values(self):
        assert OPCODE_TEXT == 1
        assert OPCODE_BINARY == 2
        assert OPCODE_CLOSE == 8
        assert OPCODE_PING == 9
        assert OPCODE_PONG == 10
