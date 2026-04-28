#!/bin/bash
set -e

echo "рџ”„ РћР¶РёРґР°РЅРёРµ Р·Р°РїСѓСЃРєР° Ollama..."
until curl -s http://ollama:11434/api/tags > /dev/null 2>&1; do
  echo "вЏі Ollama РµС‰С‘ РЅРµ РіРѕС‚РѕРІ, Р¶РґС‘Рј..."
  sleep 3
done

echo "вњ… Ollama Р·Р°РїСѓС‰РµРЅ"

# РџСЂРѕРІРµСЂРєР° РЅР°Р»РёС‡РёСЏ РјРѕРґРµР»Рё Phi-4-mini
if ! curl -s http://ollama:11434/api/tags | grep -q "phi4-mini"; then
  echo "рџ“Ґ Р—Р°РіСЂСѓР·РєР° РјРѕРґРµР»Рё phi4-mini (СЌС‚Рѕ Р·Р°Р№РјС‘С‚ РЅРµСЃРєРѕР»СЊРєРѕ РјРёРЅСѓС‚)..."
  curl -X POST http://ollama:11434/api/pull -d '{"name":"phi4-mini"}'
  echo "вњ… РњРѕРґРµР»СЊ phi4-mini Р·Р°РіСЂСѓР¶РµРЅР°"
else
  echo "вњ… РњРѕРґРµР»СЊ phi4-mini СѓР¶Рµ СѓСЃС‚Р°РЅРѕРІР»РµРЅР°"
fi

echo "рџљЂ Р—Р°РїСѓСЃРє AI-Р±РѕС‚Р° СЃ РіРёР±СЂРёРґРЅС‹Рј С‡Р°РЅРєРѕРІР°РЅРёРµРј..."
exec "$@"
