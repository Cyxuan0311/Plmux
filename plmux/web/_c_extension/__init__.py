try:
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
except ImportError:
    FrameParser = None
    encode = None
    encode_text_frame = None
    encode_binary_frame = None
    encode_close_frame = None
    encode_pong_frame = None
    OPCODE_TEXT = 1
    OPCODE_BINARY = 2
    OPCODE_CLOSE = 8
    OPCODE_PING = 9
    OPCODE_PONG = 10
