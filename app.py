import os
from dotenv import load_dotenv
import pandas as pd
import streamlit as st
from supabase import create_client, Client
from streamlit_extras.switch_page_button import switch_page

# Load environment variables from .env file
load_dotenv()

# Supabase setup
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(url, key)

TABLE_CUSTOMERS = "mikapi_customers"
TABLE_ORDERS = "mikapi_orders"

def main():
    st.set_page_config(page_title="注文管理アプリ", layout="wide")

    # カスタムCSS
    st.markdown("""
    <style>
    # .stApp {
    #     background-color: #f0f2f6;
    # }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 5px;
    }
    .stTextInput>div>div>input {
        background-color: white;
    }
    </style>
    """, unsafe_allow_html=True)

    st.title("注文管理アプリ")

    # サイドバーでページ選択
    page = st.sidebar.radio("ページを選択", ["トップページ", "精算済み一覧"])

    if page == "トップページ":
        show_top_page()
    elif page == "精算済み一覧":
        show_settled_customers()

def show_top_page():
    st.header("現在のお客さん一覧")

    # 新規お客さんの追加
    with st.form("new_customer"):
        new_name = st.text_input("新規お客様名")
        if st.form_submit_button("明細追加", use_container_width=True):
            if new_name:
                result = supabase.table(TABLE_CUSTOMERS).insert({"name": new_name, "settled": False}).execute()
                if result.data:
                    st.success(f"{new_name}様の明細を追加しました。")
                    st.session_state.customer_id = result.data[0]['id']
                    switch_page("customer_details")
                else:
                    st.error("明細の追加に失敗しました。")

    # 現在のお客様一覧の表示
    customers = supabase.table(TABLE_CUSTOMERS).select("*").eq("settled", False).execute()
    for customer in customers.data:
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button(customer['name'], key=f"customer_{customer['id']}", use_container_width=True):
                st.session_state.customer_id = customer['id']
                switch_page("customer_details")
        with col2:
            if st.button("精算済み", key=f"settle_{customer['id']}", use_container_width=True):
                supabase.table(TABLE_CUSTOMERS).update({"settled": True}).eq("id", customer['id']).execute()
                st.success(f"{customer['name']}様の注文を精算済みにしました。")
                st.rerun()

def show_settled_customers():
    st.header("精算済みお客さん一覧")

    settled_customers = supabase.table(TABLE_CUSTOMERS).select("*").eq("settled", True).execute()
    for customer in settled_customers.data:
        if st.button(customer['name'], key=f"settled_customer_{customer['id']}", use_container_width=True):
            st.session_state.customer_id = customer['id']
            switch_page("customer_details")

def show_customer_details():
    if 'customer_id' not in st.session_state:
        st.warning("お客様が選択されていません。")
        return

    customer = supabase.table(TABLE_CUSTOMERS).select("*").eq("id", st.session_state.customer_id).execute().data[0]

    # お客様名の編集
    new_name = st.text_input("お客様名", value=customer['name'])

    st.write("お会計票")
    st.write(f"名前: {new_name}")

    # メモ欄
    memo = st.text_area("メモ", value=customer.get('memo', ''))

    # 注文一覧の表示と編集
    orders = supabase.table(TABLE_ORDERS).select("*").eq("customer_id", st.session_state.customer_id).execute()

    if orders.data:
        df = pd.DataFrame(orders.data)
        df = df[['id', 'item', 'quantity', 'price']]
    else:
        df = pd.DataFrame(columns=['id', 'item', 'quantity', 'price'])

    for index, row in df.iterrows():
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        with col1:
            df.at[index, 'item'] = st.text_input(f"品目 {index + 1}", value=row['item'], key=f"item_{index}")
        with col2:
            df.at[index, 'quantity'] = st.number_input(f"数量 {index + 1}", value=row['quantity'], min_value=0, step=1, key=f"quantity_{index}")
        with col3:
            st.button("-", key=f"minus_{index}", on_click=lambda i=index: decrease_quantity(df, i))
            st.button("+", key=f"plus_{index}", on_click=lambda i=index: increase_quantity(df, i))
        with col4:
            df.at[index, 'price'] = st.number_input(f"金額 {index + 1}", value=row['price'], min_value=0, step=100, key=f"price_{index}")

    # 新しい行を追加するボタン
    if st.button("新しい品目を追加", use_container_width=True):
        new_row = pd.DataFrame({'id': [None], 'item': [''], 'quantity': [1], 'price': [0]})
        df = pd.concat([df, new_row], ignore_index=True)

    total_amount = (df['quantity'] * df['price']).sum()
    st.subheader(f"合計金額: ¥{total_amount}")

    if st.button("確定", use_container_width=True):
        # お客様名とメモの更新
        supabase.table(TABLE_CUSTOMERS).update({"name": new_name, "memo": memo}).eq("id", st.session_state.customer_id).execute()

        # 注文の更新
        for index, row in df.iterrows():
            if pd.isna(row['id']):  # 新規追加の行
                supabase.table(TABLE_ORDERS).insert({
                    "customer_id": st.session_state.customer_id,
                    "name": new_name,
                    "item": row['item'],
                    "quantity": row['quantity'],
                    "price": row['price']
                }).execute()
            else:  # 既存の行の更新
                supabase.table(TABLE_ORDERS).update({
                    "name": new_name,
                    "item": row['item'],
                    "quantity": row['quantity'],
                    "price": row['price']
                }).eq("id", row['id']).execute()

        st.success("お客様情報と注文を更新しました。")
        st.rerun()

    if not customer['settled']:
        if st.button("精算済みにする", use_container_width=True):
            supabase.table(TABLE_CUSTOMERS).update({"settled": True}).eq("id", st.session_state.customer_id).execute()
            st.success(f"{new_name}様の注文を精算済みにしました。")
            st.rerun()

def decrease_quantity(df, index):
    if df.at[index, 'quantity'] > 0:
        df.at[index, 'quantity'] -= 1

def increase_quantity(df, index):
    df.at[index, 'quantity'] += 1

if __name__ == "__main__":
    main()
