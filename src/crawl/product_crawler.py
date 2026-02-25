import os
import re
import time
import uuid
from datetime import datetime, timezone, timedelta
import hashlib
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

from _shared import create_all_tables, get_db_connection, setup_chrome_driver
MAX_CATEGORIES = int(os.getenv("PRODUCT_CRAWL_MAX_CATEGORIES", "10"))

def click_see_more(driver, timeout=10):
    try:
        wait = WebDriverWait(driver, timeout)
        see_more_btn = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "div[data-view-id='category_infinity_view.more']")
        ))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", see_more_btn)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", see_more_btn)
        time.sleep(0.5)
        print("Clicked 'See more', loading more products...")
        return True
    except Exception:
        print("All products in this category loaded.")
        return False

def parse_tiki_products(html_content, category_id):
    soup = BeautifulSoup(html_content, 'html.parser')
    products = []
    
    items = soup.find_all('div', class_=re.compile(r'sc-d785edce-0'))
    
    for item in items:
        try:
            a_tag = item.find('a', class_='product-item')
            href = a_tag.get('href', '')
            full_url = href if href.startswith('http') else f"https://tiki.vn{href}"
            
            pid_match = re.search(r'p(\d+)\.html', full_url)
            product_id = pid_match.group(1) if pid_match else None
            
            if not product_id:
                continue

            name_tag = item.find('h3')
            product_name = name_tag.text.strip() if name_tag else "N/A"
            
            author_brand = item.find('div', class_='above-product-name-info')
            author_brand = author_brand.text.strip() if author_brand else ""

            sold_tag = item.find('span', class_='quantity')
            sold_quantity = 0
            if sold_tag:
                sold_text = sold_tag.text
                sold_numbers = re.findall(r'\d+', sold_text.replace('.', '').replace(',', ''))
                sold_quantity = int(sold_numbers[0]) if sold_numbers else 0

            img_tag = item.find('img')
            image_url = "N/A"
            if img_tag:
                image_url = img_tag.get('srcset', '').split(' ')[0] or img_tag.get('src')

            products.append({
                'product_id': product_id,
                'product_name': product_name,
                'category_id': category_id,
                'product_url': full_url,
                'image_url': image_url,
                'author_brand': author_brand,
                'sold_quantity': sold_quantity,
            })
        except Exception as e:
            print(f"Error parsing one product: {e}")
            continue
    return products

def parse_review(html_content, product_id):
    soup = BeautifulSoup(html_content, 'html.parser')
    reviews_in_page = []
    reviewers_in_page = []
    
    review_items = soup.find_all('div', class_='review-comment')
    for rev in review_items:
        rev_name = rev.find('div', class_='review-comment__user-name').text.strip()
        rev_date_join = rev.find('div', class_='review-comment__user-date').text.strip()

        combined_info = f"{rev_name}_{rev_date_join}"
        rev_id = hashlib.md5(combined_info.encode('utf-8')).hexdigest()[-10:]
        
        info_chunks = soup.find_all('div', class_='review-comment__user-info')
    
        written_reviews = 0
        received_thanks = 0
        
        for chunk in info_chunks:
            text = chunk.get_text(strip=True)
            match = re.search(r'(\d+)', text)
            if match:
                number = int(match.group(1))
                
                if "Đã viết" in text:
                    written_reviews = number
                elif "Đã nhận" in text:
                    received_thanks = number

        rating_wrapper = soup.find('div', class_='review-comment__rating')
        stars = 0
        if rating_wrapper:
            overlay_div = rating_wrapper.find('div', style=re.compile(r'width:'))
            if overlay_div:
                style_text = overlay_div.get('style', '')
                match = re.search(r'width:\s*(\d+)%', style_text)
                if match:
                    percentage = int(match.group(1))
                    stars = int(percentage / 20)
        
        content = rev.find('div', class_='review-comment__content').get_text(strip=True)
        content = content.replace("Xem thêm", "").replace("Thu gọn", "").strip()

        thank_tag = rev.find('span', class_='review-comment__thank')
        thank_count = 0
        if thank_tag:
            thank_text = thank_tag.get_text(strip=True)
            match = re.search(r'\d+', thank_text)
            if match:
                thank_count = int(match.group())
        
        time_container = rev.find('div', class_='review-comment__created-date')
        usage_duration = ""
        review_time = ""
        if time_container:
            usage_tag = time_container.find('span', class_='review-comment__time-line')
            usage_duration = usage_tag.get_text(strip=True) if usage_tag else ""
            all_spans = time_container.find_all('span')
            review_time = all_spans[0].get_text(strip=True) if all_spans else ""

        reviewers_in_page.append({
            'reviewer_id': rev_id,
            'reviewer_name': rev_name,
            'reviewer_seniority': rev_date_join,
            'reviewer_contributions': written_reviews,
            'reviewer_received_thanks': received_thanks
        })

        reviews_in_page.append({
            'review_id': str(uuid.uuid4())[:12],
            'product_id': product_id,
            'reviewer_id': rev_id,
            'rating_score': stars,
            'review_content': content,
            'thank_count': thank_count,
            'review_time': review_time,
            'usage_duration': usage_duration
        })

    return reviews_in_page, reviewers_in_page

def crawl_all_reviews(driver, product_id, review_count):
    if review_count == 0:
        print(f"Product {product_id} has no reviews. Skipping.")
        return [], []
    
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
    time.sleep(0.5)

    all_page_reviews = []
    all_page_reviewers = []
    current_page = 1
    max_empty_retries = 3
    
    while True:
        if len(all_page_reviews) >= review_count:
            break

        print(f"Crawling reviews page {current_page}...")
        
        try:
            buttons = driver.find_elements(By.CSS_SELECTOR, "span.show-more-content")
            for btn in buttons:
                if btn.is_displayed() and "Xem thêm" in btn.text:
                    driver.execute_script("arguments[0].click();", btn)
        except:
            pass

        html_content = driver.page_source
        reviews_in_page, reviewers_in_page = parse_review(html_content, product_id)

        if not reviews_in_page:
            if max_empty_retries > 0:
                print(f"No reviews found, scrolling more... ({max_empty_retries} retries left)")
                driver.execute_script("window.scrollBy(0, 800);")
                time.sleep(0.5)
                max_empty_retries -= 1
                continue 
            else:
                print("Could not find reviews. Stopping to avoid infinite loop.")
                break

        all_page_reviews.extend(reviews_in_page)
        all_page_reviewers.extend(reviewers_in_page)
        max_empty_retries = 3

        try:
            next_btns = driver.find_elements(By.CSS_SELECTOR, "div.customer-reviews__pagination a.next")
            
            if not next_btns:
                break
                
            btn = next_btns[0]
            if "disabled" in btn.get_attribute("class") or not btn.is_displayed():
                print("Reached last page.")
                break
            
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
            time.sleep(0.5)
            btn.click()
            
            current_page += 1
            time.sleep(0.5)
            
        except Exception as e:
            print(f"Pagination error: {e}")
            break
            
    return all_page_reviews, all_page_reviewers

def parse_seller_info(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    name_tag = soup.select_one('.seller-name span')
    seller_name = name_tag.get_text(strip=True) if name_tag else "N/A"
    
    link_tag = soup.find('a', href=re.compile(r'/cua-hang/'))
    seller_id = "N/A"
    if link_tag:
        href = link_tag.get('href')
        parts = href.split('/')
        if len(parts) >= 3:
            seller_id = parts[2].split('?')[0]

    rating_tag = soup.select_one('.item.review .title span')
    seller_rating = float(rating_tag.get_text(strip=True)) if rating_tag else 0.0

    count_tag = soup.select_one('.item.review .sub-title')
    total_reviews = 0
    if count_tag:
        count_text = count_tag.get_text(strip=True).lower()
        numbers = re.findall(r'\d+\.?\d*', count_text)
        if numbers:
            base_number = float(numbers[0])
            if 'k' in count_text:
                total_reviews = int(base_number * 1000)
            else:
                total_reviews = int(base_number)

    return {
        'seller_id': seller_id,
        'seller_name': seller_name,
        'seller_rating': seller_rating,
        'total_reviews': total_reviews
    }

def parse_tiki_detail_page(driver, product):
    product_url = product['product_url']
    driver.get(product_url)

    html_content = driver.page_source

    if "Trang bạn đang tìm kiếm không tồn tại" in html_content:
        print(f"Product {product['product_id']} does not exist. Skipping.")
        return None
    
    wait = WebDriverWait(driver, 10)
    try:
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "product-price__current-price")))
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "seller-name")))
        driver.execute_script("window.scrollTo(0, 1000);")
        time.sleep(1) 
    except Exception as e:
        print(f"Page load slow or structure error: {product_url}")
    
    html_content = driver.page_source
    is_out_of_stock = "Sản phẩm đã hết hàng" in html_content
    is_coming_soon = "Sản phẩm sắp có hàng" in html_content

    soup = BeautifulSoup(html_content, 'html.parser')
    
    product_id = product['product_id']
    product_name = product['product_name']
    category_id = product['category_id']
    image_url = product['image_url']
    author_brand = product['author_brand']
    sold_quantity = product['sold_quantity']

    desc_items = soup.find_all('div', class_='sc-c86b1a3d-0')
    short_description = "\n".join([item.text.strip() for item in desc_items]) if desc_items else "N/A"

    count_tag = soup.select_one('a[data-view-id="pdp_main_view_review"]')
    review_count = 0
    if count_tag:
        count_match = re.search(r'(\d+)', count_tag.text)
        review_count = int(count_match.group(1)) if count_match else 0

    score_tag = soup.find('div', style=re.compile(r'margin-right:\s*4px'))
    review_score = 0.0
    if score_tag:
        review_score = float(score_tag.text.strip())

    seller_data = parse_seller_info(html_content)
    if seller_data['seller_id'] == "N/A":
        if is_out_of_stock:
            seller_data = {
                'seller_id': 'out_of_stock',
                'seller_name': 'Sản phẩm đã hết hàng',
                'seller_rating': 0.0,
                'total_reviews': 0
            }
        elif is_coming_soon:
            seller_data = {
                'seller_id': 'coming_soon',
                'seller_name': 'Sản phẩm sắp có hàng',
                'seller_rating': 0.0,
                'total_reviews': 0
            }

    product_data = {
        'product_id': product_id,
        'product_name': product_name,
        'short_description': short_description,
        'category_id': category_id,
        'seller_id': seller_data['seller_id'],
        'product_url': product_url,
        'image_url': image_url,
        'author_brand': author_brand,
        'sold_quantity': sold_quantity,
        'review_count': review_count,
        'review_score': review_score,
    }
        
    curr_tag = soup.find('div', class_='product-price__current-price')
    current_price = 0.0
    if curr_tag:
        price_text = re.sub(r'\D', '', curr_tag.get_text())
        current_price = float(price_text) if price_text else 0.0

    disc_tag = soup.find('div', class_='product-price__discount-rate')
    discount_percent = 0.0
    if disc_tag:
        disc_match = re.search(r'\d+', disc_tag.get_text())
        discount_percent = float(disc_match.group()) if disc_match else 0.0
    
    orig_tag = soup.find('div', class_='product-price__original-price')
    original_price = 0.0
    if orig_tag:
        orig_text = orig_tag.get_text()
        original_price = float(re.sub(r'\D', '', orig_text))

    if original_price == 0 and discount_percent > 0:
        original_price = round(current_price / (1 - (discount_percent / 100)), -2)
    elif original_price == 0:
        original_price = current_price

    coupons = [c.text for c in soup.find_all('div', class_='sc-14beda0e-0')]
    
    service_items = soup.find_all('div', class_='sc-34e0efdc-3 jcYGog benefit-item')

    services = []

    for item in service_items:
        service_name_tag = item.find('div')
        if service_name_tag:
            service_text = service_name_tag.text.strip()
            if service_text and service_text not in ["Đăng ký", "Chi tiết"]:
                services.append(service_text)

    vn_tz = timezone(timedelta(hours=7))
    current_time_vn = datetime.now(vn_tz).isoformat()

    combined_offer = f"{product_id}_{current_time_vn}"
    offer_id = hashlib.md5(combined_offer.encode()).hexdigest()[:10]
    
    price_offer_data = {
        'offer_id': offer_id,
        'product_id': product_id,
        'current_price': current_price,
        'original_price': original_price,
        'discount_percent': discount_percent,
        'coupon_available': ", ".join(coupons),
        'extra_services': ", ".join(services),
        'crawl_time': current_time_vn
    }

    reviews, reviewers = ([], [])
    if review_count > 0:
        reviews, reviewers = crawl_all_reviews(driver, product_id, review_count)
    
    return {
        'product': product_data,
        'price_offer': price_offer_data,
        'seller': seller_data,
        'reviewers': reviewers,
        'reviews': reviews
    }

def repair_and_update_sellers(cur, conn, driver):
    print("Repairing and updating sellers...")
    
    cur.execute("""
        SELECT product_id, product_url, product_name, category_id, image_url, author_brand, sold_quantity
        FROM product 
        WHERE seller_id = 'N/A' OR seller_id IS NULL;
    """)
    broken_products = cur.fetchall()
    
    if not broken_products:
        print("Data is clean, no products missing Seller.")
        return

    print(f"Found {len(broken_products)} products to repair. Starting to process...")

    for row in broken_products:
        p_id, p_url, p_name, cat_id, img_url, auth, sold = row
        
        temp_product = {
            'product_id': p_id, 'product_url': p_url, 'product_name': p_name,
            'category_id': cat_id, 'image_url': img_url, 'author_brand': auth, 'sold_quantity': sold
        }

        try:
            print(f"Getting seller for: {p_name}...")
            re_crawled_data = parse_tiki_detail_page(driver, temp_product)
            if re_crawled_data is None:
                continue
            
            new_seller = re_crawled_data['seller']
            
            if new_seller['seller_id'] == 'N/A':
                print(f"Still cannot find seller for {p_id}, possibly due to page loading error.")
                continue

            cur.execute("""
                INSERT INTO seller (seller_id, seller_name, seller_rating, total_reviews)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (seller_id) DO UPDATE SET 
                    seller_name = EXCLUDED.seller_name,
                    seller_rating = EXCLUDED.seller_rating;
            """, (new_seller['seller_id'], new_seller['seller_name'], 
                  new_seller['seller_rating'], new_seller['total_reviews']))

            cur.execute("""
                UPDATE product 
                SET seller_id = %s 
                WHERE product_id = %s;
            """, (new_seller['seller_id'], p_id))

            conn.commit()
            print(f"Successfully repaired product {p_id}. New seller: {new_seller['seller_name']}")

        except Exception as e:
            conn.rollback()
            print(f"Error repairing product {p_id}: {e}")

    try:
        cur.execute("""
            DELETE FROM seller 
            WHERE seller_id = 'N/A' 
            AND NOT EXISTS (SELECT 1 FROM product WHERE seller_id = 'N/A');
        """)
        conn.commit()
    except Exception as e:
        print(f"Cannot delete 'N/A' row because there are still products referencing it: {e}")

def is_product_exists(cur, product_id):
    cur.execute("SELECT 1 FROM product WHERE product_id = %s LIMIT 1;", (product_id,))
    return cur.fetchone() is not None

def repair_finished_categories(cur, conn, driver):
    print("Repairing finished categories...")
    
    if not os.path.exists("finished_categories.txt"):
        print("Cannot find finished_categories.txt")
        return

    with open("finished_categories.txt", "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f.readlines() if line.strip()]

    for url in urls:
        print(f"\nChecking category: {url}")
        
        cur.execute("SELECT category_id FROM category WHERE category_url = %s", (url,))
        result = cur.fetchone()
        if not result:
            print(f"Cannot find URL in category table. Skipping.")
            continue
        cat_id = result[0]

        driver.get(url)
        while click_see_more(driver):
            pass
        
        html_content = driver.page_source
        products_on_web = parse_tiki_products(html_content, cat_id)
        
        missing_count = 0
        for p in products_on_web:
            p_id = p['product_id']
            
            cur.execute("SELECT 1 FROM product WHERE product_id = %s", (p_id,))
            if not cur.fetchone():
                print(f"Missing product: {p_id}. Starting to crawl...")
                
                try:
                    product_data = parse_tiki_detail_page(driver, p)
                    if product_data:
                        save_to_db(cur, conn, product_data)
                        missing_count += 1
                except Exception as e:
                    print(f"Error crawling product {p_id}: {e}")
        
        if missing_count == 0:
            print(f"Category is fully data (Total: {len(products_on_web)} products).")
        else:
            print(f"Successfully crawled {missing_count} products for this category.")

def get_detailed_coupons(driver):
    extracted_coupons = []
    
    try:
        arrow_xpath = "//div[contains(text(), 'Ưu đãi khác')]/following-sibling::div//img[@alt='right-icon']"
        
        arrow_btn = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.XPATH, arrow_xpath))
        )
        
        driver.execute_script("arguments[0].click();", arrow_btn)
        
        WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.CLASS_NAME, "coupon-item"))
        )
    except TimeoutException:
        print("Timeout waiting for coupon popup to appear.")
        return extracted_coupons
    except Exception as e:
        print(f"Error getting detailed coupons: {e}")
        return extracted_coupons

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    coupon_items = soup.find_all('div', class_='coupon-item')
    
    for item in coupon_items:
        title_tag = item.find('h4')
        title = title_tag.text.strip() if title_tag else "N/A"
        
        p_tags = item.find_all('p', class_='gdZzDE')
        condition = p_tags[0].text.strip() if len(p_tags) > 0 else "N/A"
        expiry = p_tags[1].text.strip() if len(p_tags) > 1 else "N/A"
        
        save_btn = item.find('button', attrs={'data-view-id': 'coupon_save_button'})
        coupon_code = save_btn.get('data-view-label', 'N/A') if save_btn else "N/A"
        
        extracted_coupons.append({
            'code': coupon_code,
            'title': title,
            'condition': condition,
            'expiry': expiry
        })

    return extracted_coupons

def get_current_price_only(driver, url, product_id):        
    try:
        driver.get(url)

        wait = WebDriverWait(driver, 8)
        html_content = driver.page_source

        if "Trang bạn đang tìm kiếm không tồn tại" in html_content: 
            return None

        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "product-price__current-price")))

        html_content = driver.page_source
        soup = BeautifulSoup(html_content, 'html.parser')

        tam_tinh_tag = soup.select_one('div.sc-31ecf63b-1.fgrIVW')
        current_price = 0.0
        if tam_tinh_tag:
            price_text = re.sub(r'\D', '', tam_tinh_tag.get_text())
            current_price = float(price_text) if price_text else 0.0

        disc_tag = soup.find('div', class_='product-price__discount-rate')
        discount_percent = 0.0
        if disc_tag:
            disc_match = re.search(r'\d+', disc_tag.get_text())
            discount_percent = float(disc_match.group()) if disc_match else 0.0

        orig_tag = soup.find('div', class_='product-price__original-price')
        original_price = 0.0
        
        if orig_tag and re.sub(r'\D', '', orig_tag.get_text()):
            original_price = float(re.sub(r'\D', '', orig_tag.get_text()))
        
        if discount_percent > 0:
            main_curr_tag = soup.find('div', class_='product-price__current-price')
            main_curr_val = float(re.sub(r'\D', '', main_curr_tag.get_text())) if main_curr_tag else 0.0
            
            if original_price == 0 or original_price <= current_price:
                if main_curr_val > current_price:
                    original_price = main_curr_val
                else:
                    original_price = round(current_price / (1 - (discount_percent / 100)), -3)

        if current_price == 0:
            print(f"Debug: Using traditional method to get current price.")
            soup = BeautifulSoup(html_content, 'html.parser')
            disc_tag = soup.find('div', class_='product-price__discount-rate')

            if disc_tag:
                try:
                    wait.until(lambda d: 
                        d.find_element(By.CLASS_NAME, "product-price__current-price").text != 
                        d.find_element(By.CLASS_NAME, "product-price__original-price").text
                    )
                except:
                    print(f"Timeout waiting for price update for {product_id}, using calculation logic.")

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            curr_tag = soup.find('div', class_='product-price__current-price')
            current_price = float(re.sub(r'\D', '', curr_tag.get_text())) if curr_tag else 0.0
            
            orig_tag = soup.find('div', class_='product-price__original-price')
            original_price = float(re.sub(r'\D', '', orig_tag.get_text())) if orig_tag else current_price
            
            disc_match = re.search(r'\d+', disc_tag.get_text()) if disc_tag else None
            discount_percent = float(disc_match.group()) if disc_match else 0.0

            if discount_percent > 0 and original_price <= current_price:
                current_price = round(original_price * (1 - (discount_percent / 100)), -3)

        coupons_list = get_detailed_coupons(driver)

        service_items = soup.find_all('div', class_='sc-34e0efdc-3 jcYGog benefit-item')
        services_list = [item.find('div').text.strip() for item in service_items if item.find('div')]

        vn_tz = timezone(timedelta(hours=7))
        current_time_vn = datetime.now(vn_tz).isoformat()
        
        combined_offer = f"{product_id}_{current_time_vn}"
        offer_id = hashlib.md5(combined_offer.encode()).hexdigest()[:10]

        if original_price == 0:
            original_price = current_price

        return {
            'offer_id': offer_id,
            'product_id': product_id,
            'current_price': current_price,
            'original_price': original_price,
            'discount_percent': discount_percent,
            'coupon_available': coupons_list,
            'extra_services': services_list,
            'crawl_time': current_time_vn
        }
    except Exception as e:
        print(f"Error getting current price for {product_id}: {e}")
        return None

def update_price_offer(cur, conn, driver):
    try:
        cur.execute("SELECT product_id, product_url FROM product ORDER BY product_id ASC;")
        products = cur.fetchall()
        print(f"Starting to update price for {len(products)} products...")
        count = 0
        for p_id, p_url in products:
            print("--------------------------------")
            print(f"[{count}] Updating: {p_id}")
            price_offer = get_current_price_only(driver, p_url, p_id)
            if price_offer:
                print(price_offer)
                cur.execute(
                    """
                    INSERT INTO price_offer (offer_id, product_id, current_price, original_price, discount_percent, crawl_time)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (offer_id) DO NOTHING;
                    """,
                    (price_offer['offer_id'], price_offer['product_id'], price_offer['current_price'], 
                    price_offer['original_price'], price_offer['discount_percent'], price_offer['crawl_time'])
                )

                for cp in price_offer['coupon_available']:
                    if cp['code'] == 'N/A' or not cp['code']: continue
                    
                    cur.execute(
                        """
                        INSERT INTO coupon (coupon_code, title, condition, expiry)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (coupon_code) DO UPDATE SET title = EXCLUDED.title
                        RETURNING coupon_id;
                        """,
                        (cp['code'], cp['title'], cp['condition'], cp['expiry'])
                    )
                    coupon_id = cur.fetchone()[0]
                    
                    cur.execute(
                        "INSERT INTO offer_coupon (offer_id, coupon_id) VALUES (%s, %s) ON CONFLICT DO NOTHING;",
                        (price_offer['offer_id'], coupon_id)
                    )

                for s_name in price_offer['extra_services']:
                    if not s_name: continue
                    
                    cur.execute(
                        """
                        INSERT INTO service (service_name) VALUES (%s)
                        ON CONFLICT (service_name) DO UPDATE SET service_name = EXCLUDED.service_name
                        RETURNING service_id;
                        """,
                        (s_name,)
                    )
                    service_id = cur.fetchone()[0]
                    
                    cur.execute(
                        "INSERT INTO offer_service (offer_id, service_id) VALUES (%s, %s) ON CONFLICT DO NOTHING;",
                        (price_offer['offer_id'], service_id)
                    )
                conn.commit()
                print(f"Successfully saved new price: {price_offer['current_price']}")
            
            count += 1
    except Exception as e:
        print(f"Error updating price offer: {e}")

def crawl_base_product(cur, conn, driver):

    if os.path.exists("finished_categories.txt"):
        with open("finished_categories.txt", "r", encoding="utf-8") as f:
            finished_categories = set([line.strip() for line in f.readlines() if line.strip()])
    else:
        finished_categories = set()
        with open("finished_categories.txt", "w", encoding="utf-8") as f:
            f.write("")
    
    cur.execute(
        """
        SELECT category_id, category_url
        FROM category c
        WHERE is_scanned = TRUE
        AND (
            category_path LIKE 'Nhà Sách Tiki%'
            -- OR category_path LIKE 'Nhà Cửa - Đời Sống%' 
            -- OR category_path LIKE 'Điện Tử - Điện Lạnh%' 
            -- OR category_path LIKE 'Làm Đẹp - Sức Khỏe%' 
            -- OR category_path LIKE 'Đồ Chơi - Mẹ & Bé%' 
            -- OR category_path LIKE 'Laptop - Máy Vi Tính - Linh kiện%' 
            -- OR category_path LIKE 'Thể Thao - Dã Ngoại%' 
            -- OR category_path LIKE 'Điện Gia Dụng%'
            -- OR category_path LIKE 'Thiết Bị Số - Phụ Kiện Số%'
        )
        AND NOT EXISTS (
            SELECT 1 
            FROM category sub 
            WHERE sub.parent_category_id = c.category_id
        )
        ORDER BY level DESC;
        """,
    )
    rows = cur.fetchall()
    print(f"Found {len(rows)} categories to crawl.")
    for row in rows:
        cat_id, url = row
        if url in finished_categories:
            continue
        print("\n" + "--"*50)
        print(url)
        print("--"*50 + "\n") 
        driver.get(url)
        while click_see_more(driver):
            pass
        
        html_content = driver.page_source
        products = parse_tiki_products(html_content, cat_id)

        products_to_crawl = []
        for p in products:
            if not is_product_exists(cur, p['product_id']):
                products_to_crawl.append(p)
        
        print(f"Found {len(products_to_crawl)} products to crawl.")
        time.sleep(0.5) 
        for product in products_to_crawl:
            product_data = parse_tiki_detail_page(driver, product)
            if product_data is None:
                continue

            product_item = product_data['product']
            price_offer_item = product_data['price_offer']
            seller_item = product_data['seller']
            reviewers_item = product_data['reviewers']
            reviews_item = product_data['reviews']

            print(product_item)
            print(price_offer_item)
            print(seller_item)
            for reviewer in reviewers_item:
                print(reviewer)
            for review in reviews_item:
                print(review)
            print("--------------------------------")
            
            save_to_db(cur, conn, product_data)

        cur.execute("SELECT COUNT(*) FROM product WHERE category_id = %s", (cat_id,))
        count_in_db = cur.fetchone()[0]
        
        if count_in_db >= len(products):
            finished_categories.add(url)
            with open("finished_categories.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(list(finished_categories)) + "\n")

def save_to_db(cur, conn, data):
    product = data['product']
    price_offer = data['price_offer']
    seller = data['seller']
    reviewers = data['reviewers']
    reviews = data['reviews']

    cur.execute(
        """
        INSERT INTO seller (seller_id, seller_name, seller_rating, total_reviews)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (seller_id) DO UPDATE SET 
            seller_name = EXCLUDED.seller_name,
            seller_rating = EXCLUDED.seller_rating,
            total_reviews = EXCLUDED.total_reviews;
        """,
        (seller['seller_id'], seller['seller_name'], seller['seller_rating'], seller['total_reviews'])
    )

    cur.execute(
        """
        INSERT INTO product (product_id, product_name, short_description, category_id, seller_id, 
                           product_url, image_url, author_brand, sold_quantity, review_count, review_score)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (product_id) DO UPDATE SET 
            sold_quantity = EXCLUDED.sold_quantity,
            review_count = EXCLUDED.review_count,
            review_score = EXCLUDED.review_score,
            short_description = EXCLUDED.short_description;
        """,
        (product['product_id'], product['product_name'], product['short_description'], 
        product['category_id'], seller['seller_id'], product['product_url'], 
        product['image_url'], product['author_brand'], product['sold_quantity'], 
        product['review_count'], product['review_score'])
    )

    cur.execute(
        """
        INSERT INTO price_offer (offer_id, product_id, current_price, original_price, discount_percent, crawl_time)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (offer_id) DO NOTHING;
        """,
        (price_offer['offer_id'], price_offer['product_id'], price_offer['current_price'], 
        price_offer['original_price'], price_offer['discount_percent'], price_offer['crawl_time'])
    )

    for cp in price_offer['coupon_available']:
        if cp['code'] == 'N/A' or not cp['code']:
            continue
            
        cur.execute(
            """
            INSERT INTO coupon (coupon_code, title, condition, expiry)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (coupon_code) DO UPDATE SET 
                title = EXCLUDED.title,
                condition = EXCLUDED.condition,
                expiry = EXCLUDED.expiry
            RETURNING coupon_id;
            """,
            (cp['code'], cp['title'], cp['condition'], cp['expiry'])
        )
        coupon_id = cur.fetchone()[0]
        
        cur.execute(
            "INSERT INTO offer_coupon (offer_id, coupon_id) VALUES (%s, %s) ON CONFLICT DO NOTHING;",
            (price_offer['offer_id'], coupon_id)
        )

    for s_name in price_offer['extra_services']:
        if not s_name:
            continue
            
        cur.execute(
            """
            INSERT INTO service (service_name)
            VALUES (%s)
            ON CONFLICT (service_name) DO UPDATE SET service_name = EXCLUDED.service_name
            RETURNING service_id;
            """,
            (s_name,)
        )
        service_id = cur.fetchone()[0]
        
        cur.execute(
            "INSERT INTO offer_service (offer_id, service_id) VALUES (%s, %s) ON CONFLICT DO NOTHING;",
            (price_offer['offer_id'], service_id)
        )

    for reviewer in reviewers:
        cur.execute(
            """
            INSERT INTO reviewer (reviewer_id, reviewer_name, reviewer_seniority, reviewer_contributions, reviewer_received_thanks)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (reviewer_id) DO UPDATE SET 
                reviewer_contributions = EXCLUDED.reviewer_contributions,
                reviewer_received_thanks = EXCLUDED.reviewer_received_thanks;
            """,
            (reviewer['reviewer_id'], reviewer['reviewer_name'], reviewer['reviewer_seniority'], 
            reviewer['reviewer_contributions'], reviewer['reviewer_received_thanks'])
        )

    for review in reviews:
        cur.execute(
            """
            INSERT INTO review (review_id, product_id, reviewer_id, rating_score, review_content, thank_count, review_time, usage_duration)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (product_id, reviewer_id) 
            DO UPDATE SET 
                thank_count = EXCLUDED.thank_count,
                review_content = EXCLUDED.review_content;
            """,
            (review['review_id'], review['product_id'], review['reviewer_id'], 
            review['rating_score'], review['review_content'], review['thank_count'], 
            review['review_time'], review['usage_duration'])
        )
        
    conn.commit()

def main():
    conn = get_db_connection()
    cur = conn.cursor()
    create_all_tables(cur)

    driver = setup_chrome_driver()

    try:
        # crawl_base_product(cur, conn, driver)

        # repair_and_update_sellers(cur, conn, driver)
        
        # repair_finished_categories(cur, conn, driver)

        update_price_offer(cur, conn, driver)
    finally:
        driver.quit()
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()
    