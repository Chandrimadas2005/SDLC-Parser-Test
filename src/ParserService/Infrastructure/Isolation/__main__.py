"""Entry point of one isolated parse: ``python -m ParserService.Infrastructure.Isolation``."""

import sys

from ParserService.Infrastructure.Isolation.ParseWorkerProcess import ParseWorkerProcess

raise SystemExit(ParseWorkerProcess().run(sys.argv[1:]))
