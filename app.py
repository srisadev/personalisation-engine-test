"""Mini mock of the Personalisation Engine (sample code for testing demo)."""
import time, random
from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse

app = FastAPI()
POPULAR = [f"item_{i}" for i in range(1, 501)]          # popularity list
USERS = {f"u{i}": True for i in range(1, 1001)}         # users with history
LLM_BUDGET = 0.5                                        # seconds (TBD-2)
llm_delay = 0.05                                        # simulated LLM latency
FEEDBACK_STREAM = []                                    # stand-in for Redis Stream

def candidate_generation(uid):
    if uid not in USERS:                                # FR-CG-4 cold start
        return POPULAR[:500]
    rnd = random.Random(uid)
    return rnd.sample(POPULAR, 500)                     # FR-CG-2 top 500

def ranking(cands):
    return sorted(cands)[:50]                           # FR-RK-2 top 50

def llm_rerank(top50):
    time.sleep(llm_delay)
    if llm_delay > LLM_BUDGET:
        raise TimeoutError("LLM over budget")
    return [{"item": i, "explanation": f"Recommended because you liked similar items ({i})"}
            for i in top50[:10]]                        # FR-RR-1/2

@app.get("/recommend/{user_id}")
def recommend(user_id: str):
    if not user_id.strip():
        raise HTTPException(400, "user_id required")
    top50 = ranking(candidate_generation(user_id))
    try:
        items, fallback = llm_rerank(top50), False
    except TimeoutError:                                # FR-RR-4 fallback
        items = [{"item": i, "explanation": "Popular pick"} for i in top50[:10]]
        fallback = True
    return {"user": user_id, "fallback": fallback, "items": items}

@app.post("/feedback")
def feedback(event: dict):
    if event.get("action") not in {"click", "watch", "skip", "like"}:
        raise HTTPException(422, "invalid action")
    FEEDBACK_STREAM.append(event)                       # FR-FB-1
    return {"status": "queued", "stream_len": len(FEEDBACK_STREAM)}

@app.post("/admin/llm_delay")                           # test hook: simulate slow LLM
def set_llm_delay(seconds: float):
    global llm_delay
    llm_delay = seconds
    return {"llm_delay": llm_delay}

@app.get("/loaderio-{token}.txt", response_class=PlainTextResponse)
def loaderio_verify(token: str):                        # Loader.io domain verification
       return f"loaderio-{token}"

@app.get("/")
def health():
    return {"status": "ok"}
