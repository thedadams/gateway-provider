import os
import time
from typing import Any

import uvicorn
import asyncio
import httpx
import iso8601.iso8601
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

debug = os.environ.get("GPTSCRIPT_DEBUG", "false") == "true"
gateway_url = os.environ.get("GPTSCRIPT_GATEWAY_URL", "https://gateway-api.gptscript.ai")
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


async def die_on_expiration(expiration: str):
    if expiration == "":
        return
    await asyncio.sleep(iso8601.iso8601.parse_date(expiration).timestamp() - time.time())
    raise asyncio.CancelledError()


if __name__ == "__main__":
    try:
        config = uvicorn.Config("main:app", host="127.0.0.1", port=int(os.environ.get("PORT", "8000")),
                                log_level="debug" if debug else "critical", access_log=debug)
        server = uvicorn.Server(config)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        coros = asyncio.gather(
            loop.create_task(die_on_expiration(os.environ.get("GPTSCRIPT_CREDENTIAL_EXPIRATION", ""))),
            loop.create_task(server.serve()),
        )
        loop.run_until_complete(coros)
    except (KeyboardInterrupt, asyncio.CancelledError):
        loop.run_until_complete(server.shutdown())
        coros.cancel()
        coros.exception()
