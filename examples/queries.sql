-- Example 1: classic inner join — clean
SELECT o.id, o.amount, c.name, c.email
FROM orders o
INNER JOIN customers c ON o.customer_id = c.id
WHERE o.amount > 100
ORDER BY o.amount DESC
LIMIT 50;

-- Example 2: SELECT * plus missing WHERE — two warnings
SELECT *
FROM big_events;

-- Example 3: left join with group by
SELECT c.region, COUNT(o.id) AS n_orders, SUM(o.amount) AS total
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.id
GROUP BY c.region
ORDER BY total DESC;

-- Example 4: non-sargable LIKE
SELECT id, name FROM customers
WHERE name LIKE '%smith%';

-- Example 5: NOT IN with subquery (NULL gotcha)
SELECT id FROM products
WHERE id NOT IN (SELECT product_id FROM order_items);

-- Example 6: implicit join
SELECT o.id, c.name
FROM orders o, customers c
WHERE o.customer_id = c.id;
