from flask import Flask, jsonify
import requests
import statistics

app = Flask(__name__)

BASE_URL = "https://api.mexc.com/api/v3"

def get_top_100_usdt_pairs():
    tickers = requests.get(f"{BASE_URL}/ticker/24hr").json()
    usdt_pairs = [t for t in tickers if t['symbol'].endswith("USDT")]
    sorted_pairs = sorted(usdt_pairs, key=lambda x: float(x['quoteVolume']), reverse=True)
    return [pair['symbol'] for pair in sorted_pairs[:100]]

def get_klines(symbol):
    url = f"{BASE_URL}/klines"
    params = {
        "symbol": symbol,
        "interval": "15m",
        "limit": 50
    }
    return requests.get(url, params=params).json()

def analyze_symbol(symbol):
    klines = get_klines(symbol)
    if len(klines) < 30:
        return None

    closes = [float(k[4]) for k in klines]
    highs = [float(k[2]) for k in klines]
    lows = [float(k[3]) for k in klines]
    volumes = [float(k[5]) for k in klines]

    ema_short = statistics.mean(closes[-9:])
    ema_long = statistics.mean(closes[-21:])

    if ema_short <= ema_long:
        return None

    last_price = closes[-1]
    recent_low = min(lows[-10:])
    recent_high = max(highs[-10:])

    risk = last_price - recent_low
    reward = recent_high - last_price

    if risk <= 0 or reward / risk < 2:
        return None

    score = round(min(9.5, 6 + (reward / risk)), 1)
    probability = min(75, 55 + int((reward / risk) * 5))

    leverage = 1
    if reward / risk > 2.5:
        leverage = 2
    if reward / risk > 3:
        leverage = 3

    return {
        "symbol": symbol,
        "entry_zone": f"{round(last_price*0.998,4)} - {round(last_price*1.002,4)}",
        "stop": round(recent_low,4),
        "target": round(recent_high,4),
        "score": score,
        "probability": probability,
        "leverage": leverage
    }

@app.route("/analyze", methods=["GET"])
def analyze():
    pairs = get_top_100_usdt_pairs()
    results = []

    for symbol in pairs:
        result = analyze_symbol(symbol)
        if result:
            results.append(result)
        if len(results) == 5:
            break

    return jsonify(results)

@app.route("/")
def home():
    return """
    <html>
    <head>
    <title>Pullback 15m MEXC</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    </head>
    <body style="font-family: Arial; text-align: center; padding: 20px;">
        <h2>Sistema Pullback 15m - MEXC</h2>
        <button onclick="analyze()" style="padding:15px;font-size:16px;">ANALISAR MERCADO</button>
        <div id="result" style="margin-top:20px;"></div>

        <script>
        async function analyze() {
            document.getElementById("result").innerHTML = "Analisando...";
            const response = await fetch("/analyze");
            const data = await response.json();

            if (data.length === 0) {
                document.getElementById("result").innerHTML = "Nenhuma oportunidade validada.";
                return;
            }

            let html = "";
            data.forEach((item, index) => {
                html += `
                <div style="margin-bottom:20px; border:1px solid #ccc; padding:10px;">
                    <strong>${index+1}️⃣ ${item.symbol}</strong><br><br>
                    Entrada: ${item.entry_zone}<br>
                    Stop: ${item.stop}<br>
                    Alvo: ${item.target}<br><br>
                    Alavancagem sugerida: ${item.leverage}x<br>
                    Score: ${item.score}<br>
                    Probabilidade estimada: ${item.probability}%
                </div>
                `;
            });

            document.getElementById("result").innerHTML = html;
        }
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
