import json
import random

import requests
from flask import Flask, Response
from model import train_model, download_data_for_meme_coins, format_data_for_meme_coins
from model import forecast_price

app = Flask(__name__)


def get_token_inference_for_meme(token, network):
    download_data_for_meme_coins(token, network)
    format_data_for_meme_coins(token)
    train_model(token)
    return forecast_price.get(token, 0)


def get_meme_coin_token(block_height):
    upshot_url = f"https://api.upshot.xyz/v2/allora/tokens-oracle/token/{block_height}"
    headers = {
        "accept": "application/json",
        "x-api-key": "UP-4b008a1aaf194a27b65dcf15"  # replace with your API key
    }

    response = requests.get(upshot_url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        name_token = str(data["data"]["address"])  # return "boshi"
        network = str(data["data"]["platform"])
        return name_token, network
    else:
        raise ValueError("Unsupported token")


@app.route("/inference/<string:token_or_block_height>")
def get_inference(token_or_block_height):
    if token_or_block_height.isnumeric():
        name_coin, network = get_meme_coin_token(token_or_block_height)
        try:
            inference = get_token_inference_for_meme(name_coin, network)
            # return str(inference)
            return Response(str(inference), status=200)
        except Exception as e:
            return Response(json.dumps({"error": str(e)}), status=500, mimetype='application/json')
    else:
        name_coin = token_or_block_height
        try:
            inference = get_last_price(name_coin, get_simple_price(name_coin))
            # return inference
            return Response(str(inference), status=200)
        except Exception as e:
            return Response(json.dumps({"error": str(e)}), status=500, mimetype='application/json')


@app.route("/healthcheck")
def healthcheck():
    return Response(str("OK"), status=200)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8011)
