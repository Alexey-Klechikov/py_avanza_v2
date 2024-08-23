from datetime import datetime, time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.layers import LSTM, Dense, Dropout, Input  # type: ignore
from tensorflow.keras.models import Sequential, load_model  # type: ignore

from data.settings import OMX30_YAHOO
from services.storage import Storage


class Model:
    def __init__(self) -> None:
        self.model = None

    def create(self, X_train):
        print("Model > Build LSTM")

        model = Sequential()
        model.add(Input(shape=(X_train.shape[1], X_train.shape[2])))
        model.add(LSTM(units=50, return_sequences=True))
        model.add(Dropout(0.2))

        model.add(LSTM(units=50, return_sequences=True))
        model.add(Dropout(0.2))

        model.add(LSTM(units=50))
        model.add(Dropout(0.2))

        model.add(Dense(units=1))
        model.compile(optimizer="adam", loss="mean_squared_error")

        self.model = model

    def fit(self, X_train, y_train, epochs, batch_size, validation_data):
        print("Model > Train")

        if self.model is None:
            raise ValueError("Model not created")

        self.model.fit(X_train, y_train, epochs=epochs, batch_size=batch_size, validation_data=validation_data)

    def predict(self, X_test):
        print("Model > Make predictions")

        if self.model is None:
            raise ValueError("Model not created")

        return self.model.predict(X_test)

    def save(self, path: str) -> None:
        file_suffix = datetime.now().strftime("%Y-%m-%d_%H-%M")
        path = f"{path.replace('.keras', '')}_{file_suffix}.keras"

        print(f"Model > Save the model > {path}")

        if self.model is None:
            raise ValueError("Model not created")

        self.model.save(path)

    def load(self, path: str) -> None:
        print("Model > Load the model")

        self.model = load_model(path)


class Data:
    def __init__(self) -> None:
        self.data = pd.DataFrame()

        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.scaled_data = pd.DataFrame()

        self.X = np.array([])
        self.y = np.array([])

        self.X_train = np.array([])
        self.X_test = np.array([])
        self.y_train = np.array([])
        self.y_test = np.array([])

        self.datetime_test_index = []

    def read(self, resolution: str) -> None:
        print("Data > Read the data")

        data = Storage(OMX30_YAHOO, resolution=resolution).read()
        data = data.resample("2T").ffill()
        data = data[["Close", "Volume"]]

        self.data = data

    def transform(self) -> None:
        print("Data > Normalize the data using MinMaxScaler")

        scaled_data = self.scaler.fit_transform(self.data)
        scaled_data = pd.DataFrame(scaled_data, columns=self.data.columns, index=self.data.index)

        self.scaled_data = scaled_data

    def create_sequences(self, time_step: int):
        print("Data > Create Sequences for LSTM")

        if self.scaled_data.empty:
            raise ValueError("Data not transformed")

        X, y = [], []
        for i in range(len(self.scaled_data) - time_step):
            X.append(self.scaled_data.iloc[i : (i + time_step)].values)
            y.append(self.scaled_data.iloc[i + time_step]["Close"])  # Predict the closing price

        self.X, self.y = np.array(X), np.array(y)

    def split(self, time_step: int, train_size_percent: float):
        print("Data > Split the data into training and testing")

        train_size = int(len(self.X) * train_size_percent)

        self.X_train, self.X_test = self.X[:train_size], self.X[train_size:]
        self.y_train, self.y_test = self.y[:train_size], self.y[train_size:]

        self.datetime_test_index = self.data.index[time_step:][train_size:]

    def inverse_transform(self, predictions):
        print("Data > Inverse transform the predictions and actual values to their original scale")

        predictions = self.scaler.inverse_transform(
            np.concatenate((predictions, np.zeros((predictions.shape[0], self.scaled_data.shape[1] - 1))), axis=1),
        )[:, 0]
        self.y_test = self.scaler.inverse_transform(
            np.concatenate(
                (self.y_test.reshape(-1, 1), np.zeros((self.y_test.shape[0], self.scaled_data.shape[1] - 1))),
                axis=1,
            ),
        )[:, 0]

        return predictions

    def evaluate(self, predictions):
        rmse = np.sqrt(mean_squared_error(self.y_test, predictions))
        print(f"Data > Evaluate the model > RMSE: {rmse}")

    def plot(self, predictions):
        print("Data > Plot the results")

        result_datetime = []
        result_actual = []
        result_predicted = []
        for i, j, k in zip(self.datetime_test_index, self.y_test, predictions):
            if i.time() < time(hour=9, minute=0) or i.time() > time(hour=17, minute=30):
                continue

            result_datetime.append(i)
            result_actual.append(j)
            result_predicted.append(k)

        plt.figure(figsize=(14, 5))
        plt.scatter(result_datetime, result_actual, color="blue", label="Actual Stock Price")
        plt.scatter(result_datetime, result_predicted, color="red", label="Predicted Stock Price")
        plt.title("Stock Price Prediction")
        plt.xlabel("Time")
        plt.ylabel("Stock Price")
        plt.legend()
        plt.show()


if __name__ == "__main__":
    reuse_model = ""

    resolution = "2m"
    time_step = 300
    train_size_percent = 0.8
    epochs = 20
    batch_size = 32
    model_path = f"model_epochs-{epochs}_batch_size-{batch_size}.keras"

    data = Data()
    data.read(resolution)
    data.transform()
    data.create_sequences(time_step)
    data.split(time_step, train_size_percent)

    model = Model()
    model.create(data.X_train)
    if reuse_model:
        model.load(model_path)
    else:
        model.fit(
            data.X_train,
            data.y_train,
            epochs=epochs,
            batch_size=batch_size,
            validation_data=(data.X_test, data.y_test),
        )

    predictions = model.predict(data.X_test)
    predictions = data.inverse_transform(predictions)

    data.evaluate(predictions)

    model.save(model_path)

    data.plot(predictions)
