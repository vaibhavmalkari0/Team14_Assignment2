import numpy as np
from quantisation import quantise

x = np.array([-1.0, -0.5, 0.0, 0.5, 1.0])

q8 = quantise(x, 8, 1.0)
q16 = quantise(x, 16, 1.0)

# Check quantised values
np.testing.assert_array_equal(
    q8, [-127, -64, 0, 64, 127]
)

np.testing.assert_array_equal(
    q16, [-32767, -16384, 0, 16384, 32767]
)

# Check data types
assert q8.dtype == np.dtype("int8")
assert q16.dtype == np.dtype("<i2")

# Check clipping
x2 = np.array([-2.0, 2.0])

np.testing.assert_array_equal(
    quantise(x2, 8), [-128, 127]
)

# Check smaller scale
x3 = np.array([-0.25, 0.0, 0.25])

np.testing.assert_array_equal(
    quantise(x3, 8, 0.25), [-127, 0, 127]
)
from quantisation import pack, unpack

for bits in [8, 16]:
    payload = pack(x, bits, 1.0)
    reconstructed = unpack(payload, bits, 1.0)

    print(f"\nTesting int{bits}")
    print("Packed size:", len(payload), "bytes")
    print("Original:", x)
    print("Reconstructed:", reconstructed)
    print("Maximum error:", np.max(np.abs(x - reconstructed)))

    assert len(payload) == len(x) * (bits // 8)
    assert reconstructed.dtype == np.float32

    tolerance = 0.5 / (2**(bits - 1) - 1) + 1e-7

    np.testing.assert_allclose(
        x, reconstructed, atol=tolerance, rtol=0
    )

print("\nAll packing and unpacking tests passed!")
print("Int8:", q8)
print("Int16:", q16)
print("All quantisation tests passed!")
np.savez(
    "srijan/mission2/results/quantisation_test_data.npz",
    original=x,
    int8_reconstructed=unpack(pack(x, 8), 8),
    int16_reconstructed=unpack(pack(x, 16), 16)
)