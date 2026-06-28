"""Manufacturing units and physical constants."""

# All manufacturing values in millimeters unless otherwise noted.
UNIT = "mm"

# Standard FDM nozzle sizes
NOZZLE_SIZES = [0.25, 0.4, 0.6, 0.8, 1.0]

# Common layer heights per nozzle
LAYER_HEIGHTS = {
    0.25: 0.10,
    0.4: 0.20,
    0.6: 0.30,
    0.8: 0.40,
    1.0: 0.50,
}
