"""Command-line twin of the Wireshark GUI steps: decrypt a capture with the key log, pull the POST bodies, hash them, and
write them in the same format the analyzer reads.
  python scripts/extract_from_pcap.py capture.pcapng qpf.keylog [--out wcap]
Needs tshark (installed with Wireshark; on macOS: /Applications/Wireshark.app/Contents/MacOS/tshark -> pass --tshark)."""
import argparse, hashlib, json, pathlib, shutil, subprocess, sys
ap = argparse.ArgumentParser(); ap.add_argument("pcap"); ap.add_argument("keylog"); ap.add_argument("--out", default="wcap")
ap.add_argument("--tshark", default=shutil.which("tshark") or "/Applications/Wireshark.app/Contents/MacOS/tshark"); a = ap.parse_args()
cmd = [a.tshark, "-r", a.pcap, "-o", f"tls.keylog_file:{a.keylog}", "-Y", "http.request.method==POST",
       "-T", "fields", "-e", "frame.number", "-e", "tls.handshake.extensions_server_name", "-e", "http.request.uri", "-e", "http.file_data"]
out = subprocess.run(cmd, capture_output=True, text=True)
if out.returncode: sys.exit(out.stderr)
pathlib.Path(a.out).mkdir(exist_ok=True); n = 0
for line in out.stdout.splitlines():
    parts = line.split("\t")
    if len(parts) < 4 or not parts[3]: continue
    body = bytes.fromhex(parts[3].replace(":", "")); h = hashlib.sha256(body).hexdigest(); n += 1
    rec = {"source": "wireshark/tshark", "frame": parts[0], "host": parts[1] or "unknown", "path": parts[2], "body_bytes": len(body), "body_sha256": h}
    try: rec["body_json"] = json.loads(body)
    except Exception: pass
    (pathlib.Path(a.out) / f"wireshark_frame{parts[0]}.json").write_text(json.dumps(rec))
    print(f"frame {parts[0]}  {parts[2]}  {len(body)} bytes  sha256={h}")
if not n: sys.exit("no decrypted POST bodies found: is the key log from the SAME run as the capture, and is the TLS key log path correct?")
