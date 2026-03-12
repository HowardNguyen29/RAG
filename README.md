# RAG Lab (chunking + embedding playground)

Muc tieu: tao mot repo nho de test chunking, embedding vector, va pipeline RAG co the moi rong sau nay.

## Cau truc thu muc
- data/papers/ dat research paper (PDF/TXT/MD).
- index/ chua vector index da tao.
- scripts/ CLI ingest va query.
- src/raglab/ core modules.

## Cai dat
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
## Ingest (chunk + embed + tao index)
python scripts/ingest.py \
  --input data/papers/paper.pdf \
  --index index \
  --chunk-size 1200 \
  --overlap 200 \
  --strategy recursive \
  --embedder hash
## Query
python scripts/query.py \
  --index index \
  --question "Tom tat y chinh cua paper la gi?" \
  --top-k 5 \
  --llm mock
## LLM (GPT) integration
Mac dinh --llm mock chi tra ve doan trich tuong ung.
Neu muon dung GPT, hay su dung LLM endpoint tuong thich chat-completions:
export LLM_URL="https://<your-endpoint>/v1/chat/completions"
export LLM_API_KEY="..."
export LLM_MODEL="your-model-name"

python scripts/query.py --index index --question "..." --llm chat
Neu ban muon minh wire truc tiep provider cu the (hoac API chinh thuc), noi minh biet de minh tra docs va cap nhat dung thong so.

## Ghi chu
- hash embedder la cach nhanh de test pipeline, khong phai embedding that.
- Neu can embedding that, cai them sentence-transformers va dung --embedder sbert.

## Telegram agent (interactive)
Agent da duoc refactor thanh package traffic_agent/, script scripts/telegram_agent.py chi la entrypoint wrapper.

Structure:
- traffic_agent/config.py: load .env + parse app config
- traffic_agent/services/: integrations (routing, weather, telegram)
- traffic_agent/tools.py: LangChain tools cho agent
- traffic_agent/prompts.py: system prompt + config fallback logic
- traffic_agent/memory.py: offset/thread persistence
- traffic_agent/bot.py: command handling + run loop
- traffic_agent/cli.py: CLI entrypoint
- traffic_agent/mcp_server.py: MCP server (stdio/sse)
- traffic_agent/mcp_client.py: MCP clients (stdio + remote sse)

Agent goi cac tool:
- best_route(origin_lat, origin_lon, dest_lat, dest_lon)
- get_weather(lat, lon, num_hours=2)
- home_to_work() (dung HOME_*, WORK_* tu env)
- get_lat_lon(address)

### Env can co
export OPENAI_API_KEY="..."
export OPENAI_MODEL="gpt-4o-mini"
export TOMTOM_API_KEY="..."
export BOT_TOKEN="123456:ABC..."
export HOME_LAT="10.77"
export HOME_LON="106.70"
export WORK_LAT="10.80"
export WORK_LON="106.65"
### Chay bot
1) Chay MCP server mode SSE (mot process dung chung):
python -m traffic_agent.mcp_server --transport sse --host 127.0.0.1 --port 8765Neu ban dung MCP version cu va gap loi unexpected keyword argument 'host', van co the chay:
python -m traffic_agent.mcp_server --transport sse

Neu ban dung MCP version cu va gap loi unexpected keyword argument 'host', van co the chay:
python -m traffic_agent.mcp_server --transport sse

2) Chay bot va connect vao server do:
python scripts/telegram_agent.py
# hoac
python -m traffic_agent.cli
Mac dinh bot dung backend mcp + client sse (khong spawn server moi moi request).
Neu muon chay tool local truc tiep:
python -m traffic_agent.cli --tool-backend local
Neu muon quay ve MCP stdio (spawn process moi theo request):
python -m traffic_agent.cli --tool-backend mcp --mcp-client-mode stdio
Neu server SSE khong dung URL mac dinh, truyen URL:
python -m traffic_agent.cli --mcp-server-url http://127.0.0.1:8000/sse
Lenh Telegram:
- /start hoac /help: huong dan
- /ping: health check
- /home2work: tim duong nha -> cong ty + goi y ao mua
- /reset: xoa memory thread cua chat hien tai

Fallback thong minh:
- Neu user noi "nha/home" hoac "cong ty/work" ma khong dua lat,lon, agent se tu dong dung toa do HOME_* va WORK_* trong CONFIG.

Bot dung long-polling (getUpdates) nen khong can webhook/server web.
Thread duoc luu local theo chat_id tai .telegram/threads/ (mac dinh giu 12 turns gan nhat).
Co the doi bang tham so:
python scripts/telegram_agent.py --thread-dir .telegram/threads --max-turns 20