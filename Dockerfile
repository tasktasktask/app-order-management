# Pythonの公式イメージをベースにする
FROM python:3.9-slim

# 作業ディレクトリを設定
WORKDIR /app

# 必要なパッケージをインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションのソースコードをコピー
COPY . .

# Streamlitを実行（ポートは docker-compose.yml で指定）
CMD ["streamlit", "run", "app.py"]
