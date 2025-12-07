-- SQLite версия базы данных для ресторана/кафе
-- Преобразовано из PostgreSQL дампа

PRAGMA foreign_keys = ON;

-- Таблица: admin_users
CREATE TABLE admin_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    login TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL
);

-- Таблица: bar_items
CREATE TABLE bar_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    price REAL NOT NULL,
    is_alcoholic BOOLEAN NOT NULL,
    strength REAL,
    is_available BOOLEAN DEFAULT 1
);

-- Таблица: ingredients
CREATE TABLE ingredients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    unit TEXT NOT NULL,
    current_stock REAL DEFAULT 0,
    min_stock_level REAL DEFAULT 0
);

-- Таблица: bar_ingredients
CREATE TABLE bar_ingredients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bar_item_id INTEGER,
    ingredient_id INTEGER,
    quantity REAL NOT NULL,
    FOREIGN KEY (bar_item_id) REFERENCES bar_items(id) ON DELETE CASCADE,
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(id)
);

-- Таблица: visit_categories
CREATE TABLE visit_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
);

-- Таблица: dishes
CREATE TABLE dishes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    price REAL NOT NULL,
    category_id INTEGER,
    is_available BOOLEAN DEFAULT 1,
    FOREIGN KEY (category_id) REFERENCES visit_categories(id)
);

-- Таблица: dish_ingredients
CREATE TABLE dish_ingredients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dish_id INTEGER,
    ingredient_id INTEGER,
    quantity REAL NOT NULL,
    FOREIGN KEY (dish_id) REFERENCES dishes(id) ON DELETE CASCADE,
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(id)
);

-- Таблица: dish_tags
CREATE TABLE dish_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

-- Таблица: dish_tag_map
CREATE TABLE dish_tag_map (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dish_id INTEGER,
    tag_id INTEGER,
    FOREIGN KEY (dish_id) REFERENCES dishes(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES dish_tags(id)
);

-- Таблица: users
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    login TEXT UNIQUE,
    password_hash TEXT,
    birth_date DATE,
    diet_type TEXT,
    meal_style TEXT
);

-- Таблица: user_allergies
CREATE TABLE user_allergies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    allergen TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Таблица: user_preferences
CREATE TABLE user_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    tag_id INTEGER,
    weight REAL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES dish_tags(id)
);

-- Таблица: orders
CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL,
    total_price REAL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Таблица: order_items
CREATE TABLE order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER,
    dish_id INTEGER,
    bar_item_id INTEGER,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (dish_id) REFERENCES dishes(id),
    FOREIGN KEY (bar_item_id) REFERENCES bar_items(id)
);

-- Таблица: stock_log
CREATE TABLE stock_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ingredient_id INTEGER,
    change_amount REAL NOT NULL,
    reason TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    order_item_id INTEGER,
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(id),
    FOREIGN KEY (order_item_id) REFERENCES order_items(id)
);

-- Таблица: tables
CREATE TABLE tables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_number INTEGER NOT NULL UNIQUE,
    device_id TEXT UNIQUE
);

-- Вставка данных

INSERT INTO admin_users (id, login, password_hash, role) VALUES
(1, 'Админ', '123', 'superuser'),
(2, 'Повар', '123', 'cook');

INSERT INTO bar_items (id, name, description, price, is_alcoholic, strength, is_available) VALUES
(1, 'Эспрессо', 'Крепкий чёрный кофе', 120.00, 0, NULL, 1),
(2, 'Мохито', 'Ром, мята, лайм', 350.00, 1, 12.50, 1),
(3, 'Апельсиновый сок', 'Свежевыжатый', 200.00, 0, NULL, 1);

INSERT INTO ingredients (id, name, unit, current_stock, min_stock_level) VALUES
(1, 'Куриная грудка', 'г', 5000.000, 1000.000),
(2, 'Лосось', 'г', 3000.000, 800.000),
(3, 'Яйцо', 'шт', 200.000, 30.000),
(4, 'Листья салата', 'г', 1500.000, 300.000),
(5, 'Сыр', 'г', 1000.000, 200.000),
(6, 'Кофейные зёрна', 'г', 800.000, 200.000),
(7, 'Ром', 'мл', 3000.000, 500.000),
(8, 'Мята', 'г', 400.000, 100.000),
(9, 'Лайм', 'шт', 50.000, 10.000),
(10, 'Апельсины', 'шт', 60.000, 10.000);

INSERT INTO bar_ingredients (id, bar_item_id, ingredient_id, quantity) VALUES
(6, 1, 6, 18.000),
(7, 2, 7, 50.000),
(8, 2, 8, 5.000),
(9, 2, 9, 1.000),
(10, 3, 10, 2.000);

INSERT INTO visit_categories (id, name) VALUES
(1, 'Завтрак'),
(2, 'Обед'),
(3, 'Ужин'),
(4, 'Праздник'),
(5, 'Выпить'),
(6, 'Прочее');

INSERT INTO dishes (id, name, description, price, category_id, is_available) VALUES
(1, 'Салат Цезарь', 'Классический с курицей', 450.00, 2, 1),
(2, 'Лосось на гриле', 'Лосось с лимонным соусом', 900.00, 3, 1),
(3, 'Омлет', 'Яйца с сыром', 300.00, 1, 1);

INSERT INTO dish_ingredients (id, dish_id, ingredient_id, quantity) VALUES
(8, 1, 1, 120.000),
(9, 1, 4, 40.000),
(10, 1, 5, 20.000),
(11, 2, 2, 200.000),
(12, 2, 4, 30.000),
(13, 3, 3, 3.000),
(14, 3, 5, 15.000);

INSERT INTO dish_tags (id, name) VALUES
(1, 'веганское'),
(2, 'острое'),
(3, 'богато_белком'),
(4, 'низкоуглеводное'),
(5, 'морепродукты');

INSERT INTO dish_tag_map (id, dish_id, tag_id) VALUES
(5, 1, 3),
(6, 2, 5),
(7, 2, 4),
(8, 3, 3);

INSERT INTO users (id, login, password_hash, birth_date, diet_type, meal_style) VALUES
(1, 'ivan', 'hash1', '1990-05-12', 'без ограничений', 'здоровый'),
(2, 'maria', 'hash2', '1985-11-02', 'веган', 'здоровый'),
(3, 'alex', 'hash3', '1998-01-22', 'Правильное питание', 'спортивный');

INSERT INTO user_allergies (id, user_id, allergen) VALUES
(1, 1, 'арахис'),
(2, 2, 'глютен'),
(3, 3, 'лактоза');

INSERT INTO user_preferences (id, user_id, tag_id, weight) VALUES
(1, 1, 3, 0.900),
(2, 2, 1, 1.000),
(3, 3, 4, 0.800);

INSERT INTO orders (id, user_id, created_at, status, total_price) VALUES
(1, 1, '2025-12-07 01:23:27.982653', 'новый', 1350.00),
(2, 2, '2025-12-07 01:23:27.982653', 'выполнен', 450.00);

INSERT INTO order_items (id, order_id, dish_id, bar_item_id) VALUES
(1, 1, 2, NULL),
(2, 1, NULL, 2),
(3, 2, 1, NULL);

INSERT INTO stock_log (id, ingredient_id, change_amount, reason, created_at, order_item_id) VALUES
(1, 2, -200.000, 'Списание по заказу', '2025-12-07 01:26:52.686032', 1),
(2, 7, -50.000, 'Списание по заказу', '2025-12-07 01:26:52.686032', 2),
(3, 8, -5.000, 'Списание по заказу', '2025-12-07 01:26:52.686032', 2),
(4, 9, -1.000, 'Списание по заказу', '2025-12-07 01:26:52.686032', 2),
(5, 1, -120.000, 'Списание по заказу', '2025-12-07 01:26:52.686032', 3),
(6, 4, -40.000, 'Списание по заказу', '2025-12-07 01:26:52.686032', 3),
(7, 5, -20.000, 'Списание по заказу', '2025-12-07 01:26:52.686032', 3);

INSERT INTO tables (id, table_number, device_id) VALUES
(1, 1, 'device_001'),
(2, 2, 'device_002'),
(3, 3, 'device_003'),
(4, 4, 'device_004'),
(5, 5, 'device_005');

-- Сброс последовательностей (для SQLite не требуется, но оставлю для совместимости)
-- SQLite использует AUTOINCREMENT для управления ID

-- Индексы для улучшения производительности
CREATE INDEX idx_bar_ingredients_bar_item_id ON bar_ingredients(bar_item_id);
CREATE INDEX idx_bar_ingredients_ingredient_id ON bar_ingredients(ingredient_id);
CREATE INDEX idx_dish_ingredients_dish_id ON dish_ingredients(dish_id);
CREATE INDEX idx_dish_ingredients_ingredient_id ON dish_ingredients(ingredient_id);
CREATE INDEX idx_dish_tag_map_dish_id ON dish_tag_map(dish_id);
CREATE INDEX idx_dish_tag_map_tag_id ON dish_tag_map(tag_id);
CREATE INDEX idx_dishes_category_id ON dishes(category_id);
CREATE INDEX idx_user_allergies_user_id ON user_allergies(user_id);
CREATE INDEX idx_user_preferences_user_id ON user_preferences(user_id);
CREATE INDEX idx_user_preferences_tag_id ON user_preferences(tag_id);
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_stock_log_ingredient_id ON stock_log(ingredient_id);