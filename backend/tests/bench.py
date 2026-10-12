import os, sys, time, tempfile, statistics
root = sys.argv[1]
os.environ.update(MOCK_MODE="1", ANTHROPIC_API_KEY="", OPENAI_API_KEY="", STATE_FILE=os.path.join(tempfile.mkdtemp(), "s.json"))
sys.path.insert(0, root)
import logging; logging.disable(logging.CRITICAL)
from fastapi.testclient import TestClient
from main import app
c = TestClient(app); c.post("/reset"); c.post("/sample")
def bench(label, fn, n):
    ts = []
    for i in range(n):
        t = time.perf_counter(); fn(i); ts.append((time.perf_counter() - t) * 1000)
    print(f"{label:52} median {statistics.median(ts):7.1f} ms   p95 {sorted(ts)[int(n*.95)-1]:7.1f} ms")
big = ("filler text about the platform team " * 30000).encode()   # ~1 MB each
for i in range(5): c.post("/upload", files={"file": (f"big{i}.txt", big, "text/plain")})
bench("ask (5 x 1MB docs loaded, unique questions)", lambda i: c.post("/ask", json={"question": f"platform team {i}", "graph": False}), 40)
from whybot.state import state
state.add_edges([f"svc{i} --[DEPENDS_ON]--> payments-api-v1" for i in range(3000)])
bench("ask with graph (3k known edges)", lambda i: c.post("/ask", json={"question": f"what uses payments-api-v1 {i}"}), 30)
bench("blast radius (3k known edges)", lambda i: c.post("/impact", json={"change": f"Deprecate payments-api-v1 v{i}"}), 15)
bench("compare (graph off+on)", lambda i: c.post("/compare", json={"question": f"who owns billing-service {i}"}), 20)
bench("repeat question (cache hit)", lambda i: c.post("/ask", json={"question": "who owns billing-service"}), 40)
t = time.perf_counter()
for i in range(300): c.post("/upload", files={"file": ("same.md", f"rev {i}\n\ntwo\n\nthree".encode(), "text/plain")})
print(f"{'300 re-uploads of one file':52} total {1000*(time.perf_counter()-t):7.0f} ms   index units kept: {len(state.index.units)}")
