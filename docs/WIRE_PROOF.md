# Wire proof: what a real submission actually reveals

Claim under test: QPF's verified rewrites change the circuit that leaves the machine but do NOT hide a secret that the
full circuit encodes, so QPF must BLOCK. Evidence is taken from the bytes on the wire, not from QPF's own objects.

## A. Offline rehearsal (mock endpoint; practice only, proves nothing about any real service)
    python scripts/mock_runtime_server.py 8765 &
    mitmdump -q -p 8080 -s scripts/mitm_capture.py --set qpf_dir=captures &
    export HTTP_PROXY=http://127.0.0.1:8080 NO_PROXY=
    python scripts/submit_job.py --mode original  --target mock
    python scripts/submit_job.py --mode protected --target mock
    python scripts/analyze_capture.py            # exit 2 + BLOCK when the secret is recoverable

## B. Real service (your own account only; check the provider's terms)
1. `pip install qiskit-ibm-runtime mitmproxy`; save your account once with `QiskitRuntimeService.save_account(...)`.
2. Start `mitmdump -s scripts/mitm_capture.py` once so ~/.mitmproxy/mitmproxy-ca-cert.pem exists.
3. In the shell that runs the client:
       export HTTPS_PROXY=http://127.0.0.1:8080
       export REQUESTS_CA_BUNDLE=$HOME/.mitmproxy/mitmproxy-ca-cert.pem
       python scripts/submit_job.py --mode original  --target ibm
       python scripts/submit_job.py --mode protected --target ibm
4. `python scripts/analyze_capture.py`. The addon never stores IAM/login request bodies and redacts Authorization / CRN headers.
   Do NOT commit captures/: they are your job data.
If the client rejects the proxy certificate, say so in your write-up; do not disable verification globally.

## C. Wireshark (independent second tool)
Wireshark alone sees only TLS ciphertext: server name, packet sizes, timing. To see plaintext:
    export SSLKEYLOGFILE=$HOME/qpf.keylog     # honoured by Python's ssl/urllib3>=2 in most setups; verify keys appear
    # Wireshark > Settings > Protocols > TLS > (Pre)-Master-Secret log filename = ~/qpf.keylog
    # display filter:  tls.handshake.extensions_server_name contains "quantum"   then  http or http2
    # Follow > HTTP/TLS stream, or File > Export Objects > HTTP; sha256sum the body and compare with captures/*.json body_sha256.
Matching hashes between Wireshark and mitmproxy show the proxy did not alter what was sent.
Passive-observer note: even without keys, body size tracks circuit size. Record packet sizes for original vs protected.

## What this does and does not show
Shows: the plaintext job a real client emits; that the exact attacker recovers the marked state from it; that rewrites verify
(PASS) yet leave it recoverable. Does not show: leakage to any specific provider employee, timing channels, or anything about
secrets bigger than ~22 active qubits (exact attacker limit). The 4-bit secret is a pipeline demonstration, not a real key.
