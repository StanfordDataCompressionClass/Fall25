# compression key idea demo

import random, string, shutil, subprocess, textwrap
from io import BytesIO
import gzip, lzma

random.seed(42)  # deterministic for class

# ===== 1) Build three equally long ASCII texts =====
N = 480  # pick a length that fits nicely on screen (multiple of 80 for wrapping)

# A salient, non-repeating English paragraph (ASCII only).
english_paragraph = (
    "Data compression turns structure into savings. Natural language carries patterns in words, phrases, and grammar, "
    "and good compressors learn to reuse those patterns. Repetition, predictable syntax, and limited vocabularies all "
    "push the description length down. When nearby characters and words look familiar, the model can guess the next ones "
    "with fewer surprises. Fewer surprises mean fewer bits. That is the core idea: the more regularity we uncover, the "
    "shorter the message that still recovers the original text exactly."
)

# Make it exactly N ASCII bytes (truncate if longer; pad with spaces if shorter)
def to_len(s, n):
    if len(s) >= n:
        return s[:n]
    return (s + " " * (n - len(s)))  # pad with spaces (ASCII)

english = to_len(english_paragraph, N)

# Shuffled: same characters as 'english', just permuted (destroys local structure)
chars = list(english)
random.shuffle(chars)
shuffled = "".join(chars)

# Random ASCII: same length as english
alphabet = string.ascii_letters + string.digits + string.punctuation + " "
random_text = "".join(random.choice(alphabet) for _ in range(N))

assert len(english) == len(shuffled) == len(random_text) == N

# ===== 2) Helpers to compress =====
def gzip_bytes(b: bytes, level: int = 9) -> bytes:
    bio = BytesIO()
    with gzip.GzipFile(fileobj=bio, mode="wb", compresslevel=level, mtime=0) as f:
        f.write(b)
    return bio.getvalue()

def zstd_bytes(b: bytes, level: int = 19) -> tuple[bytes, str]:
    """Try system `zstd`; else try python `zstandard`; else fallback to lzma."""
    if shutil.which("zstd") is not None:
        out = subprocess.run(["zstd", f"-{level}", "-q", "-c", "-"], input=b, capture_output=True, check=True)
        return out.stdout, "zstd"
    try:
        import zstandard as zstd
        return zstd.ZstdCompressor(level=level).compress(b), "zstd"
    except Exception:
        return lzma.compress(b, preset=6), "lzma (fallback)"

# ===== 3) Display blocks neatly =====
def show_block(title: str, text: str, width: int = 80):
    print(f"\n=== {title} (length = {len(text)} ASCII bytes) ===")
    print(textwrap.fill(text, width=width))

show_block("ENGLISH (structured)", english)
show_block("SHUFFLED (same characters, permuted)", shuffled)
show_block("RANDOM (same length, uniform ASCII)", random_text)

# ===== 4) Compress & report =====
samples = {
    "ENGLISH": english.encode("ascii"),
    "SHUFFLED": shuffled.encode("ascii"),
    "RANDOM": random_text.encode("ascii"),
}

# Decide the “better” codec label once (zstd or lzma fallback)
probe_bytes, best_label = zstd_bytes(b"probe")
del probe_bytes

print("\n=== Sizes (bytes) and compression ratios (× smaller than RAW) ===")
print(f"(Comparing RAW vs gzip vs {best_label})\n")
print("Sample     RAW   gzip   {:>12}   gzip×   {:>6}×".format(best_label, best_label))
print("--------  -----  -----  -------------  ------  --------")

for name, b in samples.items():
    raw = len(b)
    gz = len(gzip_bytes(b))
    best_b, _ = zstd_bytes(b)
    best = len(best_b)

    def ratio(sz): return raw / sz if sz else float("inf")

    print(f"{name:<8}  {raw:5d}  {gz:5d}  {best:13d}  {ratio(gz):6.2f}  {ratio(best):8.2f}")

print("\nQuick read:")
print(" • ENGLISH < SHUFFLED: same letters, but local structure makes ENGLISH more compressible.")
print(" • RANDOM ≈ worst: near-incompressible baseline at this scale.")
print(f" • {best_label.upper()} typically beats gzip here (stronger modeling/entropy coding).")
print()

