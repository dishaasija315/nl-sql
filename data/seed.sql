CREATE TABLE customers (
    customer_id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100),
    city VARCHAR(100)
);

CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    product_name VARCHAR(100),
    category VARCHAR(100),
    price DECIMAL(10, 2)
);

CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers(customer_id),
    order_date DATE,
    total_amount DECIMAL(10, 2)
);

CREATE TABLE order_items (
    order_item_id SERIAL PRIMARY KEY,
    order_id INT REFERENCES orders(order_id),
    product_id INT REFERENCES products(product_id),
    quantity INT
);

INSERT INTO customers (name, email, city) VALUES
('Rahul Sharma', 'rahul@gmail.com', 'Delhi'),
('Priya Singh', 'priya@gmail.com', 'Mumbai'),
('Aman Verma', 'aman@gmail.com', 'Bangalore'),
('Neha Gupta', 'neha@gmail.com', 'Delhi');

INSERT INTO products (product_name, category, price) VALUES
('Laptop', 'Electronics', 60000),
('Mouse', 'Electronics', 1000),
('Keyboard', 'Electronics', 2000),
('Headphones', 'Accessories', 3000);

INSERT INTO orders (customer_id, order_date, total_amount) VALUES
(1, '2026-08-01', 61000),
(2, '2026-08-05', 3000),
(3, '2026-08-10', 2000),
(1, '2026-08-15', 3000),
(4, '2026-08-20', 60000);

INSERT INTO order_items (order_id, product_id, quantity) VALUES
(1, 1, 1),
(1, 2, 1),
(2, 4, 1),
(3, 3, 1),
(4, 4, 1),
(5, 1, 1);