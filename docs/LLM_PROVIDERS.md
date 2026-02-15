# LLM Providers for iamtoxico Valet

## Quick Reference

| Provider | Free Tier | Speed | Best For | Get Key |
|----------|-----------|-------|----------|---------|
| ⚡ **Groq** | 14,400 req/day | **Fastest** | Real-time, RAG | [console.groq.com/keys](https://console.groq.com/keys) |
| 🔮 **Gemini** | 1,500 req/day | Fast | Default, reliable | [aistudio.google.com](https://aistudio.google.com/app/apikey) |
| 🚀 **DeepSeek** | Generous | Good | Cheapest paid | [platform.deepseek.com](https://platform.deepseek.com/api_keys) |
| 🧠 **Cerebras** | Available | Fastest chip | Speed testing | [cloud.cerebras.ai](https://cloud.cerebras.ai/) |
| 🌊 **SambaNova** | Available | Fast | Enterprise | [cloud.sambanova.ai](https://cloud.sambanova.ai/) |
| 🤝 **Together** | $1 credit | Good | Open models | [api.together.xyz](https://api.together.xyz/settings/api-keys) |
| 🔥 **Fireworks** | $1 credit | Good | Open models | [fireworks.ai](https://fireworks.ai/account/api-keys) |
| 💼 **Cohere** | 1K/month | Good | Structured | [dashboard.cohere.com](https://dashboard.cohere.com/api-keys) |
| 🌬️ **Mistral** | Limited | Fast | EU compliance | [console.mistral.ai](https://console.mistral.ai/api-keys/) |
| 🐦 **xAI Grok** | Limited | Good | Current events | [console.x.ai](https://console.x.ai/) |
| 🤖 **OpenAI** | None ($5 min) | Good | Best quality | [platform.openai.com](https://platform.openai.com/api-keys) |
| 🎭 **Claude** | None ($5 min) | Good | Personality | [console.anthropic.com](https://console.anthropic.com/settings/keys) |
| 🔍 **Perplexity** | None | Good | Search-augmented | [perplexity.ai/settings](https://www.perplexity.ai/settings/api) |

---

## Groq Models (Current as of Nov 2025)

Your key: `gsk_2QOt...xmQ` (stored in .env)

| Model | Context | Best For |
|-------|---------|----------|
| `llama-3.3-70b-versatile` | 131K | **Recommended** - Best quality |
| `llama-3.1-8b-instant` | 131K | Fastest, lighter tasks |
| `meta-llama/llama-4-maverick-17b-128e-instruct` | 131K | Latest Llama 4 |
| `meta-llama/llama-4-scout-17b-16e-instruct` | 131K | Latest Llama 4 |
| `moonshotai/kimi-k2-instruct` | 131K | Alternative |
| `qwen/qwen3-32b` | 131K | Chinese/multilingual |
| `openai/gpt-oss-120b` | 131K | Largest open model |
| `groq/compound` | 131K | Multi-model routing |
| `whisper-large-v3` | 448 | Speech-to-text |
| `playai-tts` | 8K | Text-to-speech |

### Speed Comparison
- **Groq**: ~500 tokens/sec (fastest)
- **Cerebras**: ~400 tokens/sec
- **Together/Fireworks**: ~100 tokens/sec
- **OpenAI/Claude**: ~50-80 tokens/sec

---

## Cost Comparison (per 1M tokens)

| Provider | Input | Output | Notes |
|----------|-------|--------|-------|
| **DeepSeek** | $0.07 | $0.14 | **Cheapest** |
| **Groq** | $0.05 | $0.08 | Free tier first |
| **Together** | $0.18 | $0.18 | Open models |
| **Mistral** | $0.25 | $0.25 | EU-based |
| **Gemini Flash** | Free | Free | 1,500/day limit |
| **GPT-4o** | $2.50 | $10.00 | Best quality |
| **Claude Sonnet** | $3.00 | $15.00 | Best personality |

---

## For vagina.college (4M+ Assets)

### Recommended Architecture:
```
User Query
    ↓
ChromaDB Vector Search (local, free)
    ↓
Top 50 Matches (embeddings)
    ↓
Groq LLM (fast, free tier)
    ↓
Final 10 Recommendations
```

### Why Groq for RAG:
1. **Speed**: Sub-second responses critical for search UI
2. **Free tier**: 14,400 req/day = ~10 req/min sustained
3. **Large context**: 131K tokens = can see many candidates
4. **Quality**: Llama 3.3 70B is excellent

### Embedding Model (for ChromaDB):
- `all-MiniLM-L6-v2` - 22MB, runs on CPU
- Or use OpenAI `text-embedding-3-small` for better quality

---

## Environment Variables

Add to `.env`:
```bash
# Primary (free tiers)
GROQ_API_KEY=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
GEMINI_API_KEY=your_gemini_key_here

# Optional (paid)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DEEPSEEK_API_KEY=sk-...
```

---

*Last updated: Nov 28, 2025*
