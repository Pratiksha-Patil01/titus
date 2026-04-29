from flask import Flask, render_template, request, redirect
from flask_mysqldb import MySQL
from Invent import app
import os

app = Flask(__name__)

# ---------------- DATABASE ----------------
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'mysql'
app.config['MYSQL_DB'] = 'bottle_business'

mysql = MySQL(app)

# ---------------- DASHBOARD ----------------
@app.route('/')
def dashboard():
    cur = mysql.connection.cursor()

    cur.execute("SELECT COUNT(*) FROM customers")
    customers = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM products")
    products = cur.fetchone()[0]

    cur.execute("SELECT SUM(total) FROM sales")
    sales = cur.fetchone()[0] or 0

    return render_template('dashboard.html',
                           customers=customers,
                           products=products,
                           sales=sales)

# ---------------- CUSTOMERS ----------------
@app.route('/customers', methods=['GET','POST'])
def customers():
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        cur.execute("INSERT INTO customers(name, phone) VALUES(%s,%s)",
                    (request.form['name'], request.form['phone']))
        mysql.connection.commit()

    cur.execute("SELECT * FROM customers")
    data = cur.fetchall()

    return render_template('customers.html', customers=data)

@app.route('/customer/edit/<int:id>', methods=['GET','POST'])
def edit_customer(id):
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        cur.execute("UPDATE customers SET name=%s, phone=%s WHERE id=%s",
                    (request.form['name'], request.form['phone'], id))
        mysql.connection.commit()
        return redirect('/customers')

    cur.execute("SELECT * FROM customers WHERE id=%s", (id,))
    data = cur.fetchone()

    return render_template('edit_customer.html', customer=data)

@app.route('/customer/delete/<int:id>')
def delete_customer(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM customers WHERE id=%s", (id,))
    mysql.connection.commit()
    return redirect('/customers')

# ---------------- PRODUCTS ----------------
@app.route('/products', methods=['GET','POST'])
def products():
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        cur.execute("INSERT INTO products(name, size, stock) VALUES(%s,%s,0)",
                    (request.form['name'], request.form['size']))
        mysql.connection.commit()

    cur.execute("SELECT * FROM products")
    data = cur.fetchall()

    return render_template('products.html', products=data)

@app.route('/product/edit/<int:id>', methods=['GET','POST'])
def edit_product(id):
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        cur.execute("UPDATE products SET name=%s, size=%s WHERE id=%s",
                    (request.form['name'], request.form['size'], id))
        mysql.connection.commit()
        return redirect('/products')

    cur.execute("SELECT * FROM products WHERE id=%s", (id,))
    data = cur.fetchone()

    return render_template('edit_product.html', product=data)

@app.route('/product/delete/<int:id>')
def delete_product(id):
    cur = mysql.connection.cursor()
    try:
        cur.execute("DELETE FROM products WHERE id=%s", (id,))
        mysql.connection.commit()
    except Exception as e:
        return "❌ Cannot delete! Product used in sales/purchase."

    return redirect('/products')

# ---------------- VENDORS ----------------
@app.route('/vendors', methods=['GET','POST'])
def vendors():
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        cur.execute("INSERT INTO vendors(name, phone) VALUES(%s,%s)",
                    (request.form['name'], request.form['phone']))
        mysql.connection.commit()

    cur.execute("SELECT * FROM vendors")
    data = cur.fetchall()

    return render_template('vendors.html', vendors=data)

@app.route('/vendor/edit/<int:id>', methods=['GET','POST'])
def edit_vendor(id):
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        cur.execute("UPDATE vendors SET name=%s, phone=%s WHERE id=%s",
                    (request.form['name'], request.form['phone'], id))
        mysql.connection.commit()
        return redirect('/vendors')

    cur.execute("SELECT * FROM vendors WHERE id=%s", (id,))
    data = cur.fetchone()

    return render_template('edit_vendor.html', vendor=data)

@app.route('/vendor/delete/<int:id>')
def delete_vendor(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM vendors WHERE id=%s", (id,))
    mysql.connection.commit()
    return redirect('/vendors')

# ---------------- PURCHASE ----------------
@app.route('/purchase', methods=['GET','POST'])
def purchase():
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        vendor = request.form['vendor']
        product = request.form['product']
        qty = int(request.form['qty'])
        price = float(request.form['price'])

        total = qty * price

        cur.execute("""
        INSERT INTO purchase(vendor_id, product_id, quantity, price, total)
        VALUES(%s,%s,%s,%s,%s)
        """, (vendor, product, qty, price, total))

        cur.execute("UPDATE products SET stock = stock + %s WHERE id=%s", (qty, product))

        mysql.connection.commit()
        return redirect('/purchase')

    cur.execute("SELECT * FROM vendors")
    vendors = cur.fetchall()

    cur.execute("SELECT * FROM products")
    products = cur.fetchall()

    return render_template('purchase.html', vendors=vendors, products=products)

# ---------------- SALES ----------------
@app.route('/sales', methods=['GET','POST'])
def sales():
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        customer = request.form['customer']
        product = request.form['product']
        qty = int(request.form['qty'])
        price = float(request.form['price'])

        cur.execute("SELECT stock FROM products WHERE id=%s", (product,))
        stock = cur.fetchone()[0]

        if stock < qty:
            return f"Only {stock} items available"

        cur.execute("SELECT COUNT(*) FROM sales")
        count = cur.fetchone()[0]
        bill_no = "B" + str(count + 1)

        total = qty * price

        cur.execute("""
        INSERT INTO sales(bill_no, customer_id, product_id, quantity, price, total)
        VALUES(%s,%s,%s,%s,%s,%s)
        """, (bill_no, customer, product, qty, price, total))

        cur.execute("UPDATE products SET stock = stock - %s WHERE id=%s", (qty, product))

        mysql.connection.commit()
        return redirect('/sales')

    cur.execute("""
    SELECT sales.bill_no, customers.name, products.name,
           sales.quantity, sales.price, sales.total
    FROM sales
    JOIN customers ON sales.customer_id = customers.id
    JOIN products ON sales.product_id = products.id
    """)
    sales_data = cur.fetchall()

    cur.execute("SELECT * FROM customers")
    customers = cur.fetchall()

    cur.execute("SELECT * FROM products")
    products = cur.fetchall()

    return render_template('sales.html', sales=sales_data, customers=customers, products=products)

# ---------------- REPORTS ----------------
@app.route('/reports', methods=['GET','POST'])
def reports():
    cur = mysql.connection.cursor()
    data = []
    grand_total = 0

    if request.method == 'POST':
        report_type = request.form.get('type')

        if report_type == "daily":
            date = request.form.get('date')
            cur.execute("""
            SELECT sales.bill_no, customers.name, products.name,
                   sales.quantity, sales.price, sales.total,
                   DATE(sales.created_at)
            FROM sales
            JOIN customers ON sales.customer_id = customers.id
            JOIN products ON sales.product_id = products.id
            WHERE DATE(sales.created_at) = %s
            """, (date,))
            data = cur.fetchall()

        elif report_type == "monthly":
            month = request.form.get('month')
            cur.execute("""
            SELECT sales.bill_no, customers.name, products.name,
                   sales.quantity, sales.price, sales.total,
                   DATE(sales.created_at)
            FROM sales
            JOIN customers ON sales.customer_id = customers.id
            JOIN products ON sales.product_id = products.id
            WHERE DATE_FORMAT(sales.created_at, '%%Y-%%m') = %s
            """, (month,))
            data = cur.fetchall()

        elif report_type == "customer":
            cid = request.form.get('customer')
            cur.execute("""
            SELECT sales.bill_no, customers.name, products.name,
                   sales.quantity, sales.price, sales.total,
                   DATE(sales.created_at)
            FROM sales
            JOIN customers ON sales.customer_id = customers.id
            JOIN products ON sales.product_id = products.id
            WHERE sales.customer_id = %s
            """, (cid,))
            data = cur.fetchall()

        elif report_type == "bill":
            bill = request.form.get('bill')
            cur.execute("""
            SELECT sales.bill_no, customers.name, products.name,
                   sales.quantity, sales.price, sales.total,
                   DATE(sales.created_at)
            FROM sales
            JOIN customers ON sales.customer_id = customers.id
            JOIN products ON sales.product_id = products.id
            WHERE sales.bill_no = %s
            """, (bill,))
            data = cur.fetchall()

        grand_total = sum(float(d[5]) for d in data) if data else 0

    cur.execute("SELECT * FROM customers")
    customers = cur.fetchall()

    return render_template('reports.html', data=data, customers=customers, grand_total=grand_total)

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True,port=8080)