# GPTScript Gateway Provider

## Usage Example

```
gptscript --default-model='gpt-4o from github.com/gptscript-ai/gateway/provider' examples/helloworld.gpt
```

## Development

* You need a GPTSCRIPT_GATEWAY_API_KEY set in your environment.

```
export GPTSCRIPT_GATEWAY_API_KEY=<your-api-key>
```

Run using the following commands

```
python -m venv .venv
source ./.venv/bin/activate
pip install --upgrade -r requirements.txt
./run.sh
```

```
export OPENAI_BASE_URL=http://127.0.0.1:8000/v1
export GPTSCRIPT_DEBUG=true

gptscript --default-model=openai examples/bob.gpt
```
