# Sample Code File containing deliberate security flaws and code smells for audit testing

import os

AWS_SECRET_KEY = "AKIAIOSFODNN7EXAMPLE_SECRET_KEY"

def fetch_user_record(db_cursor, user_input_id):
    # SQL Injection Vulnerability
    query = "SELECT * FROM users WHERE id = '" + str(user_input_id) + "'"
    db_cursor.execute(query)
    
    try:
        results = db_cursor.fetchall()
        return results
    except:
        # Bare except code smell
        pass

def calculate_discount(price, customer_type):
    # Duplicate logic / code smell
    if customer_type == "VIP":
        return price * 0.80
    elif customer_type == "VIP":
        return price * 0.80
    else:
        return price
