try:
    from plmux.terminal._c_extension._fastscreen import (
        Screen,
        Stream,
    )
except ImportError:
    Screen = None
    Stream = None
