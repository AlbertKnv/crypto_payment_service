class Queries:
    insert_address = """
        insert into addresses (address, priv_key, order_id)
        values ($1, $2, $3) returning *
    """

    select_address = """
        select * from addresses where address = $1
    """

    find_address = """
        select * from addresses where order_id = $1
    """

    select_address_payments = """
        select * from payments where address = $1 order by id
    """

    select_address_order_id = """
        select address, order_id from addresses
    """

    insert_payment = """
        insert into payments (txid, vout, amount, address, order_id)
        values ($1, $2, $3, $4, $5) returning *
    """

    select_priv_key = """
        select priv_key from addresses where address = $1
    """

    update_forward_txid = """
        update payments set forward_txid = $1 where id = $2
    """

    update_is_cb_active = """
        update payments set is_cb_active = False where id = $1
    """

    select_active_payments = """
        select * from payments where is_cb_active
    """
