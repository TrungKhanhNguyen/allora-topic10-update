import os
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
from sklearn.svm import SVR
from config import data_base_path
import random
import requests
import retrying

forecast_price = {}

binance_data_path = os.path.join(data_base_path, "binance/futures-klines")
MAX_DATA_SIZE = 100  # Giới hạn số lượng dữ liệu tối đa khi lưu trữ
INITIAL_FETCH_SIZE = 100  # Số lượng nến lần đầu tải về


@retrying.retry(wait_exponential_multiplier=1000, wait_exponential_max=10000, stop_max_attempt_number=5)
def fetch_prices_from_defined(symbol_address, limit: int):
    try:
        # Define the parameters for the token data request
        network = "base"
        token_address = symbol_address
        apikey = "CGAPIKEY"
        
        # Construct the API URL for the token data
        token_url = f"https://api.geckoterminal.com/api/v2/networks/{network}/tokens/{token_address}"
        
        # Define the headers
        headers = {
            "Authorization": f"Bearer {apikey}"
        }
        
        # Make the API request to get the token data
        token_response = requests.get(token_url, headers=headers)
        responses = []
        # Check if the request was successful
        if token_response.status_code == 200:
            token_data = token_response.json()
            top_pools = token_data['data']['relationships']['top_pools']['data']
            
            if top_pools:
                # Get the first pool address
                pool_address = top_pools[0]['id'].split('_')[1]
                
                # Define the parameters for the OHLCV data request
                timeframe = "minute"
                aggregate = 5
                limit = limit
                
                # Construct the API URL for the OHLCV data
                ohlcv_url = f"https://api.geckoterminal.com/api/v2/networks/{network}/pools/{pool_address}/ohlcv/{timeframe}"
                
                # Define the query parameters
                params = {
                    "aggregate": aggregate,
                    "limit": limit
                }
                
                # Make the API request to get the OHLCV data
                ohlcv_response = requests.get(ohlcv_url, headers=headers, params=params)
                
                # Check if the request was successful
                if ohlcv_response.status_code == 200:
                    ohlcv_data = ohlcv_response.json()
                    ohlcv_list = ohlcv_data['data']['attributes']['ohlcv_list']
                    
                    # Extract unixtimestamp and close values
                    extracted_data = [(entry[0], entry[4]) for entry in ohlcv_list]
                    
                    # Print the extracted data
                    for timestamp, close in extracted_data:
                        tmp = [close, timestamp]
                        responses.append(tmp)
                else:
                    print(f"Error fetching OHLCV data: {ohlcv_response.status_code}, {ohlcv_response.text}")
            else:
                print("No top pools found for the given token address.")
        else:
            print(f"Error fetching token data: {token_response.status_code}, {token_response.text}")
        return responses
    except Exception as e:
        print(f'Failed to fetch prices for {symbol_address} from GeckoTerminal API: {str(e)}')
        raise e


def download_data_for_meme_coins(token, platform):
    current_datetime = datetime.now()
    download_path = os.path.join(binance_data_path, token.lower())

    # network_id = get_network_id(platform)
    network_id = 8453

    # Đường dẫn file CSV để lưu trữ
    file_path = os.path.join(download_path, f"{token.lower()}_5m_data.csv")
    # file_path = os.path.join(data_base_path, f"{token.lower()}_price_data.csv")

    # Kiểm tra xem file có tồn tại hay không
    if os.path.exists(file_path):
        new_data = fetch_prices_from_defined(token, 10)
    else:
        new_data = fetch_prices_from_defined(token, 1000)

    # Chuyển dữ liệu thành DataFrame
    new_df = pd.DataFrame(new_data, columns=[
        "close", "start_time"
    ])

    # Kiểm tra và đọc dữ liệu cũ nếu tồn tại
    if os.path.exists(file_path):
        old_df = pd.read_csv(file_path)
        # Kết hợp dữ liệu cũ và mới
        combined_df = pd.concat([old_df, new_df])
        # Loại bỏ các bản ghi trùng lặp dựa trên 'start_time'
        combined_df = combined_df.drop_duplicates(subset=['start_time'], keep='last')
    else:
        combined_df = new_df

    # Giới hạn số lượng dữ liệu tối đa
    if len(combined_df) > MAX_DATA_SIZE:
        combined_df = combined_df.iloc[-MAX_DATA_SIZE:]

    # Lưu dữ liệu đã kết hợp vào file CSV
    if not os.path.exists(download_path):
        os.makedirs(download_path)
    combined_df.to_csv(file_path, index=False)
    print(f"Updated data for {token} saved to {file_path}. Total rows: {len(combined_df)}")


def format_data_for_meme_coins(token):
    path = os.path.join(binance_data_path, token.lower())
    file_path = os.path.join(path, f"{token.lower()}_5m_data.csv")

    if not os.path.exists(file_path):
        print(f"No data file found for {token}")
        return

    df = pd.read_csv(file_path)

    # Sử dụng các cột sau (đúng với dữ liệu bạn đã lưu)
    columns_to_use = [
        "close", "start_time"
    ]

    # Kiểm tra nếu tất cả các cột cần thiết tồn tại trong DataFrame
    if set(columns_to_use).issubset(df.columns):
        df = df[columns_to_use]
        df.columns = [
            "close", "start_time"
        ]
        df.index = pd.to_datetime(df["start_time"]*1000, unit='ms')
        df.index.name = "date"

        output_path = os.path.join(data_base_path, f"{token.lower()}_price_data.csv")
        df.sort_index().to_csv(output_path)
        print(f"Formatted data saved to {output_path}")
    else:
        print(f"Required columns are missing in {file_path}. Skipping this file.")


def train_model(token):
    # Load the token price data
    price_data = pd.read_csv(os.path.join(data_base_path, f"{token.lower()}_price_data.csv"))
    df = pd.DataFrame()

    # Convert 'date' to datetime
    price_data["date"] = pd.to_datetime(price_data["date"])

    # Set the date column as the index for resampling
    price_data.set_index("date", inplace=True)

    # Resample the data to 10-minute frequency and compute the mean price
    df = price_data.resample('60T').mean()

    # Prepare data for Linear Regression
    df = df.dropna()  # Loại bỏ các giá trị NaN (nếu có)
    X = np.array(range(len(df))).reshape(-1, 1)  # Sử dụng chỉ số thời gian làm đặc trưng
    y = df['close'].values  # Sử dụng giá đóng cửa làm mục tiêu

    # Khởi tạo mô hình Linear Regression
    model = SVR(kernel='rbf')
    model.fit(X, y)  # Huấn luyện mô hình

    # Dự đoán giá tiếp theo
    next_time_index = np.array([[len(df)]])  # Giá trị thời gian tiếp theo
    predicted_price = model.predict(next_time_index)[0]  # Dự đoán giá

    # Xác định khoảng dao động xung quanh giá dự đoán
    fluctuation_range = 0.001 * predicted_price  # Lấy 0.1% của giá dự đoán làm khoảng dao động
    min_price = predicted_price - fluctuation_range
    max_price = predicted_price + fluctuation_range
    #
    # # Chọn ngẫu nhiên một giá trị trong khoảng dao động
    price_predict = random.uniform(min_price, max_price)
    forecast_price[token] = price_predict

    print(f"Predicted_price: {predicted_price}")
    print(f"Forecasted price for {token}: {forecast_price[token]}")
