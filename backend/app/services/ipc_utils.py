import struct
from pathlib import Path

def write_prefixed(path: Path, data: str):
    """Writes data with a 4-byte big-endian frame-length prefix."""
    encoded_data = data.encode('utf-8')
    prefix = struct.pack('>I', len(encoded_data))
    with open(path, 'wb') as f:
        f.write(prefix)
        f.write(encoded_data)

def read_prefixed(path: Path) -> str:
    """Reads data with a 4-byte big-endian frame-length prefix."""
    with open(path, 'rb') as f:
        prefix = f.read(4)
        if len(prefix) < 4:
            raise ValueError("Incomplete frame-length prefix")
        length = struct.unpack('>I', prefix)[0]
        data = f.read(length)
        if len(data) < length:
            raise ValueError("Incomplete data frame")
        return data.decode('utf-8')
