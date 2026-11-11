# Private macOS ARM64 candidate 0.3.0

## Minimal repair

The 0.2.0 private candidate omitted the complete ONNX Runtime LICENSE and
ThirdPartyNotices, and several Python dependency texts. The product version
0.2.0 already identifies another released source. Rebuild the product as 0.3.0;
do not rename, replace or retag either historical package.

Collect complete license/notice/copyright files from the actual locked Python
build environment, including package-directory files, not only dist-info.
Preserve every collected file's package/version, original relative path, byte
count and SHA-256 in a generated inventory. Missing license files are an error,
not an implicit exemption: use reviewed, version-bound upstream texts for the
FlatBuffers and tokenizers wheels that omit them. Retain Python's full license.

For macOS, derive copied-library notices from PyInstaller's actual Analysis
inputs: CPython, OpenSSL, liblzma, mpdecimal and SQLite. Preserve the selected
Homebrew texts and bind source library hashes to their inventory. Do not infer
Linux GNU runtime obligations from this Mac. Keep the existing Linux guard,
Bun/JSC/TinyCC materials and frozen pi-ai identity checks unchanged. Include
generated inventories and complete texts in both frozen engine and app resources.

## Verification boundary

The existing live-stream test can receive flushed bytes before the upstream
thread sets its diagnostic event. Synchronize that event with a bounded wait;
keep the byte-delivery and cancellation assertions unchanged. This is a test
fixture scheduling repair, not a router transport change.

Behavior tests first demonstrate omitted ONNX/package notices and the wrong
product version. Native verification compares the collected texts byte-for-byte
with the frozen archive and app resources, inventories actual native dependencies,
and checks source/package/frontend version 0.3.0. Preserve the exact source,
private DMG, native checks and isolated launch/quit evidence for independent
review. Inspect remaining npm/Rust notices against the built application rather
than assuming the sidecar inventory covers those components.

Only macOS ARM64 is rebuilt. No Windows changes or qualification, historical
universal source rebuild, new provider attempt, personal process termination,
Apple release operation or publication is part of this repair. The real provider
response and Apple/public-delivery gates remain owned by t_c350e5cc.
