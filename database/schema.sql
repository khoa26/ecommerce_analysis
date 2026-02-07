
CREATE TABLE category (
    category_id        VARCHAR(50) PRIMARY KEY,
    category_name      TEXT NOT NULL,
	category_url                 TEXT,
    parent_category_id VARCHAR(50),
    level              INT,
	category_path TEXT,
	is_scanned BOOLEAN DEFAULT FALSE,
    CONSTRAINT fk_parent_category
        FOREIGN KEY (parent_category_id)
        REFERENCES category(category_id)
        ON DELETE SET NULL
);

CREATE TABLE seller (
    seller_id     VARCHAR(50) PRIMARY KEY,
    seller_name   TEXT NOT NULL,
    seller_rating FLOAT,
    total_reviews INT
);

CREATE TABLE product (
    product_id        VARCHAR(50) PRIMARY KEY,
    product_name      TEXT NOT NULL,
    short_description TEXT,
    category_id       VARCHAR(50),
    seller_id         VARCHAR(50),
    product_url       TEXT,
    image_url         TEXT,
    author_brand      TEXT,
    sold_quantity     INT,
    review_score      FLOAT,
    review_count      INT,

    CONSTRAINT fk_product_category
        FOREIGN KEY (category_id)
        REFERENCES category(category_id),

    CONSTRAINT fk_product_seller
        FOREIGN KEY (seller_id)
        REFERENCES seller(seller_id)
);

CREATE TABLE price_offer (
    offer_id         VARCHAR(50) PRIMARY KEY,
    product_id       VARCHAR(50) NOT NULL,
    current_price    FLOAT,
    original_price   FLOAT,
    discount_percent FLOAT,
    coupon_available TEXT,
    extra_services   TEXT,
    crawl_time       TIMESTAMP,

    CONSTRAINT fk_offer_product
        FOREIGN KEY (product_id)
        REFERENCES product(product_id)
        ON DELETE CASCADE
);

CREATE TABLE reviewer (
    reviewer_id            VARCHAR(50) PRIMARY KEY,
    reviewer_name          TEXT,
    reviewer_seniority     TEXT,
    reviewer_contributions INT,
    reviewer_received_thanks INT
);

CREATE TABLE review (
    review_id       VARCHAR(50) PRIMARY KEY,
    product_id      VARCHAR(50) NOT NULL,
    reviewer_id     VARCHAR(50) NOT NULL,
    rating_score    INT CHECK (rating_score BETWEEN 1 AND 5),
    review_content  TEXT,
    thank_count     INT,
    review_time     TEXT,
    usage_duration  TEXT,

    CONSTRAINT fk_review_product
        FOREIGN KEY (product_id)
        REFERENCES product(product_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_review_reviewer
        FOREIGN KEY (reviewer_id)
        REFERENCES reviewer(reviewer_id)
        ON DELETE CASCADE
);