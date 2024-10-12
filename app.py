import streamlit as st
from supabase import create_client, Client
import os

# Supabase setup
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(url, key)

TABLE_CUSTOMERS = "mikapi_customers"
TABLE_ORDERS = "mikapi_orders"

def main():
    st.set_page_config(page_title="注文内容管理アプリ", layout="wide")
    st.title("注文内容管理アプリ")

    # サイドバーでページ選択
    page = st.sidebar.selectbox("ページを選択", ["トップページ", "注文明細", "精算済み"])

    if page == "トップページ":
        show_top_page()
    elif page == "注文明細":
        show_order_details()
    elif page == "精算済み":
        show_settled_orders()

def show_top_page():
    st.header("お客様一覧")

    # 新規お客様の追加
    with st.form("new_customer"):
        new_name = st.text_input("新規お客様名")
        if st.form_submit_button("追加"):
            if new_name:
                # Supabaseに新規お客様を追加
                supabase.table(TABLE_CUSTOMERS).insert({"name": new_name}).execute()
                st.success(f"{new_name}様を追加しました。")

    # お客様一覧の表示
    customers = supabase.table(TABLE_CUSTOMERS).select("*").execute()
    for customer in customers.data:
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.write(customer['name'])
        with col2:
            if st.button("注文明細", key=f"detail_{customer['id']}"):
                st.session_state.customer_id = customer['id']
                st.session_state.page = "注文明細"
                st.rerun()
        with col3:
            if st.button("精算済み", key=f"settle_{customer['id']}"):
                # お客様を精算済みに更新
                supabase.table(TABLE_CUSTOMERS).update({"settled": True}).eq("id", customer['id']).execute()
                st.success(f"{customer['name']}様の注文を精算済みにしました。")
                st.rerun()

def show_order_details():
    if 'customer_id' not in st.session_state:
        st.warning("お客様が選択されていません。")
        return

    customer = supabase.table(TABLE_CUSTOMERS).select("*").eq("id", st.session_state.customer_id).execute().data[0]
    st.header(f"{customer['name']}様の注文明細")

    # 新規注文の追加
    with st.form("new_order"):
        col1, col2, col3 = st.columns(3)
        with col1:
            item = st.text_input("商品名")
        with col2:
            quantity = st.number_input("数量", min_value=1, value=1)
        with col3:
            price = st.number_input("金額", min_value=0, value=0)

        if st.form_submit_button("追加"):
            supabase.table(TABLE_ORDERS).insert({
                "customer_id": st.session_state.customer_id,
                "item": item,
                "quantity": quantity,
                "price": price
            }).execute()
            st.success("注文を追加しました。")
            st.rerun()

    # 注文一覧の表示と編集
    orders = supabase.table(TABLE_ORDERS).select("*").eq("customer_id", st.session_state.customer_id).execute()

    for order in orders.data:
        with st.form(f"edit_order_{order['id']}"):
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                new_item = st.text_input("商品名", value=order['item'])
            with col2:
                new_quantity = st.number_input("数量", min_value=1, value=order['quantity'])
            with col3:
                new_price = st.number_input("金額", min_value=0, value=order['price'])

            update_col, delete_col = st.columns(2)
            with update_col:
                if st.form_submit_button("更新", use_container_width=True):
                    supabase.table(TABLE_ORDERS).update({
                        "item": new_item,
                        "quantity": new_quantity,
                        "price": new_price
                    }).eq("id", order['id']).execute()
                    st.success("注文を更新しました。")
                    st.rerun()
            with delete_col:
                if st.form_submit_button("削除", use_container_width=True):
                    supabase.table(TABLE_ORDERS).delete().eq("id", order['id']).execute()
                    st.success("注文を削除しました。")
                    st.rerun()

def show_settled_orders():
    st.header("精算済み注文")

    settled_customers = supabase.table(TABLE_CUSTOMERS).select("*").eq("settled", True).execute()
    for customer in settled_customers.data:
        st.subheader(customer['name'])
        orders = supabase.table(TABLE_ORDERS).select("*").eq("customer_id", customer['id']).execute()
        for order in orders.data:
            st.write(f"{order['item']} - {order['quantity']}個 - {order['price']}円")
        st.divider()

if __name__ == "__main__":
    main()
