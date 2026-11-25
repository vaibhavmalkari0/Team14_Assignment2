import numpy as np


def quantise(x, bits, S=1.0):
    qmax = 2**(bits - 1) - 1
    qmin = -(2**(bits - 1))

    # Calculate scaled samples
    scaled = np.asarray(x, dtype=np.float64) / S * qmax

    # Round the samples
    rounded = np.round(scaled)

    # Clip the samples
    clipped = np.clip(rounded, qmin, qmax)

    # Select the datatype
    if bits == 8:
        dtype = np.int8
    elif bits == 16:
        dtype = np.dtype("<i2")
    else:
        raise ValueError("Only 8 and 16 bits are supported")

    return clipped.astype(dtype)


def pack(x, bits, S=1.0):
    # Quantise the original audio
    q = quantise(x, bits, S)

    # Convert into little-endian bytes
    data = q.astype(q.dtype.newbyteorder("<")).tobytes()

    return data


def unpack(payload, bits, S=1.0):
    qmax = 2**(bits - 1) - 1

    # Select the datatype
    if bits == 8:
        dtype = np.int8
    elif bits == 16:
        dtype = np.dtype("<i2")
    else:
        raise ValueError("Only 8 and 16 bits are supported")

    # Reconstruct the integer array
    q = np.frombuffer(payload, dtype=dtype)

    # Convert to float32
    q = q.astype(np.float32)

    # Dequantise
    x = q / qmax * S

    return x.astype(np.float32)


if __name__ == "__main__":
    x = np.array([-1.0, -0.5, 0.0, 0.5, 1.0])

    print("Original:", x)
    print("Int8:", quantise(x, 8))
    print("Int16:", quantise(x, 16))