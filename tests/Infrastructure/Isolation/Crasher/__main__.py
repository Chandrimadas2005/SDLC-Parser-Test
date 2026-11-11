"""Exit without writing any result, like a segfault in a native library."""

import os

os._exit(139)
