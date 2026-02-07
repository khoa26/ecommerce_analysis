import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)

DB_USER = os.getenv("DB_USER")
PASSWORD = os.getenv("PASSWORD")
HOST = os.getenv("HOST")
DATABASE = os.getenv("DATABASE")
PORT = os.getenv("PORT")


def get_db_connection(autocommit=True):
    conn = psycopg2.connect(
        user=DB_USER,
        database=DATABASE,
        password=PASSWORD,
        host=HOST,
        port=PORT,
    )
    conn.autocommit = autocommit
    return conn


def setup_chrome_driver():
    desktop_ua = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    options = Options()
    options.add_argument(f"user-agent={desktop_ua}")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--incognito")
    options.add_argument("no-sandbox")
    options.add_argument("window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu-sandbox")
    options.add_experimental_option(
        "prefs",
        {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_setting_values.geolocation": 2,
            "useAutomationExtension": False,
        },
    )
    options.add_experimental_option(
        "excludeSwitches", ["enable-automation", "enable-logging"]
    )
    options.add_argument("--allow-insecure-localhost")
    options.add_argument("--disable-web-security")
    options.add_argument("--log-level=3")

    service = Service()
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            """
        },
    )
    return driver

def create_all_tables(cur):
    queries = [
        """
        CREATE TABLE IF NOT EXISTS category (
            category_id         VARCHAR(50) PRIMARY KEY,
            category_name       TEXT NOT NULL,
            category_url        TEXT,
            parent_category_id  VARCHAR(50),
            level               INT,
            category_path       TEXT,
            is_scanned          BOOLEAN DEFAULT FALSE,
            CONSTRAINT fk_parent_category
                FOREIGN KEY (parent_category_id)
                REFERENCES category(category_id)
                ON DELETE SET NULL
        );
        """,

        """
        CREATE TABLE IF NOT EXISTS seller (
            seller_id     VARCHAR(50) PRIMARY KEY,
            seller_name   TEXT NOT NULL,
            seller_rating FLOAT,
            total_reviews INT
        );
        """,

        """
        CREATE TABLE IF NOT EXISTS product (
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
        """,

        """
        CREATE TABLE IF NOT EXISTS price_offer (
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
        """,

        """
        CREATE TABLE IF NOT EXISTS reviewer (
            reviewer_id              VARCHAR(50) PRIMARY KEY,
            reviewer_name            TEXT,
            reviewer_seniority       TEXT,
            reviewer_contributions   INT,
            reviewer_received_thanks INT
        );
        """,

        """
        CREATE TABLE IF NOT EXISTS review (
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
        """
    ]

    try:
        for query in queries:
            cur.execute(query)
        print("Success! All database structures have been created/updated successfully.")
    except Exception as err:
        print(f"Error creating tables: {err}")