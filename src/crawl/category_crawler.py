import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import sleep

from bs4 import BeautifulSoup
from _shared import get_db_connection, setup_chrome_driver, create_all_tables

TIKI_URL = "https://tiki.vn/"
MAX_WORKERS = 1
_print_lock = threading.Lock()

def _log(msg):
    with _print_lock:
        print(msg)


def initialize_driver(driver, url):
    driver.get(url)
    sleep(2)
    
    driver.execute_script("""
        var popup = document.getElementById('VIP_BUNDLE');
        if (popup) {
            popup.remove();
        }
    """)


def crawl_main_categories(driver):
    html_source = driver.page_source
    soup = BeautifulSoup(html_source, 'html.parser')
    
    category_items = soup.find_all('div', class_='sc-602cd749-1')
    category_list = []
    
    for item in category_items:
        link_tag = item.find('a')
        if link_tag:
            title = link_tag.get('title')
            href = link_tag.get('href')
            id_match = re.search(r'/c(\d+)', href)
            cat_id = id_match.group(1) if id_match else None
            full_url = href if href.startswith('http') else f"https://tiki.vn{href}"
            
            if title and href and cat_id:
                category_list.append({
                    'category_id': cat_id,
                    'category_name': title,
                    'category_url': full_url,
                    'level': 1,
                    'category_path': f"{title}",
                    'is_scanned': False
                })
    
    category_list = category_list[:len(category_list) - 4]
    return category_list


def crawl_sub_categories(driver, parent_id=None, level=1, parent_path=""):
    html_source = driver.page_source
    soup = BeautifulSoup(html_source, 'html.parser')
    
    category_items = soup.find_all('div', class_=re.compile(r'sc-36d678cb-1'))
    category_list = []
    
    for item in category_items:
        link_tag = item.find('a')
        title_tag = item.find('div', class_=re.compile(r'sc-.*-3'))
        title = title_tag.text.strip() if title_tag else link_tag.get('title')
        
        if link_tag and title:
            href = link_tag.get('href')
            full_url = href if href.startswith('http') else f"https://tiki.vn{href}"
            
            id_match = re.search(r'/c(\d+)', href)
            cat_id = id_match.group(1) if id_match else None
            
            if cat_id:
                category_list.append({
                    'category_id': cat_id,
                    'category_name': title,
                    'category_url': full_url,
                    'parent_category_id': parent_id,
                    'level': level,
                    'category_path': f"{parent_path} > {title}" if parent_path else title,
                    'is_scanned': False
                })
    
    return category_list


def _claim_one_category(cur):
    cur.execute("""
        SELECT category_id, category_url, level, category_path 
        FROM category 
        WHERE is_scanned = FALSE 
        ORDER BY level ASC 
        LIMIT 1
        FOR UPDATE SKIP LOCKED
    """)
    return cur.fetchone()


def _process_one_category(driver, cur, cat_id, category_url, level, category_path):
    driver.get(category_url)
    # sleep(1)
    sub_categories = crawl_sub_categories(
        driver,
        parent_id=cat_id,
        level=level + 1,
        parent_path=category_path,
    )
    for sub_cat in sub_categories:
        cur.execute("""
            INSERT INTO category (
                category_id, category_name, category_url,
                parent_category_id, level, category_path, is_scanned
            )
            VALUES (%s, %s, %s, %s, %s, %s, FALSE)
            ON CONFLICT (category_id)
            DO UPDATE SET
                category_name = EXCLUDED.category_name,
                category_url = EXCLUDED.category_url,
                parent_category_id = EXCLUDED.parent_category_id,
                level = EXCLUDED.level,
                category_path = EXCLUDED.category_path;
        """, (
            sub_cat['category_id'],
            sub_cat['category_name'],
            sub_cat['category_url'],
            sub_cat['parent_category_id'],
            sub_cat['level'],
            sub_cat['category_path'],
        ))
    cur.execute(
        "UPDATE category SET is_scanned = TRUE WHERE category_id = %s",
        (cat_id,),
    )


def _worker_loop(worker_id):
    driver = None
    conn = get_db_connection(autocommit=False)
    cur = conn.cursor()
    try:
        driver = setup_chrome_driver()
        count = 0
        while True:
            try:
                row = _claim_one_category(cur)
                if not row:
                    break
                cat_id, category_url, level, category_path = row
                _log(f"[Worker {worker_id}] Crawling: {category_path} (Level {level})")
                _process_one_category(driver, cur, cat_id, category_url, level, category_path)
                conn.commit()
                count += 1
            except Exception as err:
                conn.rollback()
                _log(f"[Worker {worker_id}] Error: {err}")
        _log(f"[Worker {worker_id}] Done. Processed {count} categories.")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        cur.close()
        conn.close()


def main_crawler_loop(driver, cur):
    while True:
        cur.execute("""
            SELECT category_id, category_url, level, category_path 
            FROM category 
            WHERE is_scanned = FALSE 
            ORDER BY level ASC LIMIT 1
        """)
        target = cur.fetchone()
        
        if not target:
            print("Done! All categories have been crawled.")
            break
            
        cat_id, category_url, level, category_path = target
        print(f"Crawling sub-categories of: {category_path} (Level {level})")
        
        try:
            driver.get(category_url)
            
            sub_categories = crawl_sub_categories(
                driver, 
                parent_id=cat_id, 
                level=level+1, 
                parent_path=category_path
            )
            
            for sub_cat in sub_categories:
                cur.execute("""
                    INSERT INTO category (
                        category_id, category_name, category_url, 
                        parent_category_id, level, category_path, is_scanned
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, FALSE)
                """, (
                    sub_cat['category_id'], 
                    sub_cat['category_name'], 
                    sub_cat['category_url'], 
                    sub_cat['parent_category_id'], 
                    sub_cat['level'], 
                    sub_cat['category_path']
                ))
            
            cur.execute(
                "UPDATE category SET is_scanned = TRUE WHERE category_id = %s", 
                (cat_id,)
            )
            
        except Exception as err:
            print(f"Error crawling {category_url}: {err}")

def save_categories_to_db(categories, cur):
    for category in categories:
        cur.execute("""
            INSERT INTO category (
                category_id, category_name, category_url, 
                level, category_path, is_scanned
            )
            VALUES (%s, %s, %s, %s, %s, FALSE)
            ON CONFLICT (category_id) 
            DO UPDATE SET 
                category_name = EXCLUDED.category_name,
                category_url = EXCLUDED.category_url,
                category_path = EXCLUDED.category_path;
        """, (
            category['category_id'], 
            category['category_name'], 
            category['category_url'], 
            category['level'], 
            category['category_path']
        ))


def run_multi_threaded_crawler():
    workers = min(MAX_WORKERS, 5)
    _log(f"Starting {workers} worker(s)...")
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(_worker_loop, i) for i in range(workers)]
        for f in as_completed(futures):
            try:
                f.result()
            except Exception as e:
                _log(f"Worker exception: {e}")
    _log("Done! All categories have been crawled.")


def main():
    conn = get_db_connection()
    cur = conn.cursor()
    
    create_all_tables(cur)
    
    driver = setup_chrome_driver()
    initialize_driver(driver, TIKI_URL)
    
    try:
        categories = crawl_main_categories(driver)
        save_categories_to_db(categories, cur)
    finally:
        driver.quit()
        conn.close()
    
    run_multi_threaded_crawler()


if __name__ == "__main__":
    main()