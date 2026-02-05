import os
from _shared import TIKI_URL, get_db_connection, setup_chrome_driver, create_all_tables
import re
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from time import sleep

MAX_CATEGORIES = int(os.getenv("PRODUCT_CRAWL_MAX_CATEGORIES", "10"))

def click_see_more(driver):
    try:
        # Tìm thẻ div có chứa chữ "Xem thêm"
        see_more_div = driver.find_element(By.XPATH, "//div[contains(text(), 'Xem thêm')]")
        
        # Cuộn màn hình đến vị trí nút để đảm bảo nó nạp vào tầm nhìn
        driver.execute_script("arguments[0].scrollIntoView();", see_more_div)
        sleep(1)
        
        # Dùng Javascript để click
        driver.execute_script("arguments[0].click();", see_more_div)
        print("✅ Đã bấm 'Xem thêm'")
        return True
    except Exception as e:
        print("ℹ️ Không tìm thấy nút 'Xem thêm' hoặc đã hết sản phẩm.")
        return False

def parse_tiki_products(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    products = []
    
    # Tìm tất cả các khối bao quanh sản phẩm
    items = soup.find_all('a', class_='product-item')
    
    for item in items:
        # 1. Href
        href = item.get('href')
        full_url = href if href.startswith('http') else f"https://tiki.vn{href}"
        
        # 2. Tên sản phẩm
        name_tag = item.find('h3')
        name = name_tag.text.strip() if name_tag else "N/A"
        
        # 3. Giá (Lấy số, bỏ chữ đ và dấu chấm)
        price_tag = item.find('div', class_='price-discount__price')
        price = re.sub(r'\D', '', price_tag.text) if price_tag else "0"
        
        # 4. Discount
        discount_tag = item.find('div', class_='price-discount__percent')
        discount = discount_tag.text.strip() if discount_tag else "0%"
        
        # 5. Thương hiệu / Tác giả
        author_tag = item.find('div', class_='above-product-name-info')
        author = author_tag.text.strip() if author_tag else "Nhiều tác giả"
        
        # 6. Đã bán (Dùng Regex lấy số)
        sold_tag = item.find('span', class_='quantity')
        sold_text = sold_tag.text.strip() if sold_tag else "0"
        sold_count = re.search(r'\d+', sold_text.replace('.', ''))
        sold = sold_count.group() if sold_count else "0"
        
        # 7. Link ảnh
        img_tag = item.find('img')
        img_url = img_tag.get('src') if img_tag else "N/A"
        
        products.append({
            'product_name': name,
            'price': int(price),
            'discount': discount,
            'author_brand': author,
            'sold_quantity': int(sold),
            'product_url': full_url,
            'image_url': img_url
        })
        
    return products

def main():
    conn = get_db_connection()
    cur = conn.cursor()
    create_all_tables(cur)

    driver = setup_chrome_driver()
    try:
        driver.get(TIKI_URL)
        cur.execute(
            """
            SELECT category_id, category_url, category_path, level
            FROM category c
            WHERE is_scanned = TRUE
            AND (
                category_path LIKE 'Nhà Sách Tiki%' OR 
                category_path LIKE 'Điện Thoại - Máy Tính Bảng%' OR 
                category_path LIKE 'Laptop - Máy Vi Tính - Linh kiện%' OR
                category_path LIKE 'Thiết Bị Số - Phụ Kiện Số%' OR
                category_path LIKE 'Điện Gia Dụng%' OR
                category_path LIKE 'Làm Đẹp - Sức Khỏe%' OR
                category_path LIKE 'Điện Tử - Điện Lạnh%' OR
                category_path LIKE 'Nhà Cửa - Đời Sống%' OR
                category_path LIKE 'Máy Ảnh - Máy Quay Phim%'
            )
            AND NOT EXISTS (
                SELECT 1 
                FROM category sub 
                WHERE sub.parent_category_id = c.category_id
            )
            ORDER BY level DESC, category_path ASC;
            """,
        )
        rows = cur.fetchall()
        print(f"Found {len(rows)} categories to crawl products from.")
        for row in rows:
            cat_id, url, path = row
            print(f"  {cat_id}: {path} -> {url}")
    finally:
        driver.quit()
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
