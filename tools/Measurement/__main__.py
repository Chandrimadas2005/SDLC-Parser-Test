import sys

from tools.Measurement.MeasurementCli import MeasurementCli

if __name__ == "__main__":
    sys.exit(MeasurementCli.default().run(sys.argv[1:]))
