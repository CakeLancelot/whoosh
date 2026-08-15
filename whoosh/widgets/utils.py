import tempfile


def write_temp_file(data: bytes) -> str:
    """Write bytes to a temporary file and return the path."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(data)
        return tmp.name
