import sys

from tools.PdfComparison.PdfComparisonCli import PdfComparisonCli

if __name__ == "__main__":
    sys.exit(PdfComparisonCli.default().run(sys.argv[1:]))
