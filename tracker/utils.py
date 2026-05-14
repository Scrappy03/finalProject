def clamp_percent(value):
    """Keep progress bar widths within valid percentage bounds."""
    return max(0, min(100, value))

