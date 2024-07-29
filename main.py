import os
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

debug = os.environ.get("GPTSCRIPT_DEBUG", "false") == "true"
gateway_url = os.environ.get("GPTSCRIPT_GATEWAY_URL", "http://localhost:8080")
api_key = os.environ.get("GPTSCRIPT_GATEWAY_API_KEY", "")
app = FastAPI()


@app.middleware("http")
async def log_body(request: Request, call_next):
    if debug:
        body = await request.body()
        print("HTTP REQUEST BODY: ", body)
    return await call_next(request)


@app.get("/")
@app.post("/")
async def root():
    return 'ok'


@app.get("/v1/models")
async def list_models() -> JSONResponse:
    # Collect all the LLM providers
    resp = httpx.get(f"{gateway_url}/api/models", headers={"Authorization": f"Bearer {api_key}"})
    if resp.status_code != 200:
        return JSONResponse({"data": [], "error": resp.text}, status_code=resp.status_code)

    return JSONResponse(resp.json(), status_code=200)


@app.post("/v1/chat/completions")
async def completions(request: Request) -> StreamingResponse:
    resp = _stream_chat_completion(await request.json())
    status_code = 0
    async for code in resp:
        status_code = code
        break

    return StreamingResponse(
        resp,
        media_type='text/event-stream',
        status_code=status_code,
    )


async def _stream_chat_completion(content: Any):
    async with httpx.AsyncClient(timeout=httpx.Timeout(30 * 60.0)) as client:
        async with client.stream(
                "POST",
                f"{gateway_url}/llm/chat/completions",
                json=content,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Accept": "text/event-stream",
                    "Accept-Encoding": "gzip",
                },
        ) as resp:
            yield resp.status_code
            async for chunk in resp.aiter_bytes():
                yield chunk


if __name__ == "__main__":
    import uvicorn
    import asyncio

    try:
        uvicorn.run("main:app", host="127.0.0.1", port=int(os.environ.get("PORT", "8000")),
                    log_level="debug" if debug else "critical", access_log=debug)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
