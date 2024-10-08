import json
import random

import requests
from flask import Flask, Response
app = Flask(__name__)



def get_meme_coin_token(block_height):
    upshot_url = f"https://api.upshot.xyz/v2/allora/tokens-oracle/token/{block_height}"
    headers = {
        "accept": "application/json",
        "x-api-key": "UP-4b008a1aaf194a27b65dcf15"  # replace with your API key
    }

    response = requests.get(upshot_url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        name_token = str(data["data"]["token_id"])  # return "boshi"
        return name_token
    else:
        raise ValueError("Unsupported token")


@app.route("/inference/<string:token_or_block_height>")
def get_inference(token_or_block_height):
        name_coin = get_meme_coin_token(token_or_block_height)
        try:
            base_url = "https://api.coingecko.com/api/v3/simple/price?ids="
            url = f"{base_url}{current_token}&vs_currencies=usd"
            headers = {
            "accept": "application/json",
            "x-cg-demo-api-key": "CG-fn5Dnv5ujTE8SoQvQP5APwDu"  # replace with your API key
            }

            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                tempValue = str(data[token_id]["usd"])
                
                current_price = float(tempValue)
                adjustment_factor = random.uniform(0.99, 1.01)
                adjusted_price = current_price * adjustment_factor
                return str(format(adjusted_price, ".7f"))
            # return str(inference)
            return Response(str(inference), status=200)
        except Exception as e:
            return Response(json.dumps({"error": str(e)}), status=500, mimetype='application/json')



@app.route("/healthcheck")
def healthcheck():
    return Response(str("OK"), status=200)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8011)
