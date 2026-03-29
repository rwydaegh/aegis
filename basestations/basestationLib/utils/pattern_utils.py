def sanitize_label(label: str) -> str:
    """
    Sanitize a label to be compatible with MATLAB variable names.
    Replaces invalid characters with underscores.
    """
    return (label
            .replace('(', '')
            .replace(')', '')
            .replace(' ', '_')
            .replace('-', '_')
            .replace('/', '_')
            .replace('.', '_')
            .replace("&", "_")
    )