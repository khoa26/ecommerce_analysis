print("--- ĐANG CHẠY PHẦN 1 ---")

# 1. Phân bố giá hiện tại (current_price)
# Sử dụng log_x nếu dải giá quá rộng (từ vài nghìn đến chục triệu)
fig1_1 = px.histogram(
    df_price, 
    x="current_price", 
    nbins=100, 
    title="1.1 Phân bố giá hiện tại (Current Price)",
    color_discrete_sequence=["#1A94FF"]
)
# fig1_1.show()

# 2. Phân bố tỷ lệ giảm giá (discount_percent)
fig1_2 = px.histogram(
    df_price, 
    x="discount_percent", 
    nbins=50, 
    title="1.2 Phân bố tỷ lệ giảm giá (Discount Percent)",
    color_discrete_sequence=["#FFB020"]
)
# fig1_2.show()

# 3. So sánh current_price vs original_price
# Thêm một đường chéo (y=x) để thấy rõ phần giảm giá nằm dưới đường chéo
fig1_3 = px.scatter(
    df_price.sample(n=min(20000, len(df_price)), random_state=42), # Sample để tránh nặng máy
    x="original_price", 
    y="current_price", 
    opacity=0.5,
    title="1.3 So sánh giá gốc và giá hiện tại",
    labels={"original_price": "Giá gốc", "current_price": "Giá sau giảm"}
)
# Vẽ đường tham chiếu y = x (không giảm giá)
max_val = max(df_price["original_price"].max(), df_price["current_price"].max())
fig1_3.add_shape(type="line", x0=0, y0=0, x1=max_val, y1=max_val, line=dict(color="red", dash="dash"))
# fig1_3.show()

# 4. Boxplot giá theo nhóm discount_percent
# Chia bins cho discount_percent
df_price["discount_group"] = pd.cut(
    df_price["discount_percent"], 
    bins=[-1, 5, 15, 30, 50, 100], 
    labels=["0-5%", "5-15%", "15-30%", "30-50%", ">50%"]
)
fig1_4 = px.box(
    df_price, 
    x="discount_group", 
    y="current_price", 
    title="1.4 Phân bố giá theo các mức giảm giá",
    color="discount_group"
)
# fig1_4.show()

print("--- ĐANG CHẠY PHẦN 2 ---")

# Join dữ liệu: price_offer + product + category + seller
df_p2 = df_price.merge(df_product[['product_id', 'category_id', 'seller_id']], on='product_id', how='inner')
df_p2 = df_p2.merge(df_category[['category_id', 'category_name']], on='category_id', how='left')
df_p2 = df_p2.merge(df_seller[['seller_id', 'seller_name']], on='seller_id', how='left')

# Tính toán bảng tóm tắt theo category
cat_summary = df_p2.groupby('category_name').agg(
    avg_current_price=('current_price', 'mean'),
    avg_discount=('discount_percent', 'mean'),
    product_count=('product_id', 'count')
).reset_index()

# Lọc các danh mục có đủ số lượng sản phẩm để mang tính đại diện
cat_summary = cat_summary[cat_summary['product_count'] >= 50]

# 1. Giá trung bình theo category (Top 15 đắt nhất)
fig2_1 = px.bar(
    cat_summary.sort_values('avg_current_price', ascending=False).head(15),
    x='avg_current_price',
    y='category_name',
    orientation='h',
    title="2.1 Giá trung bình theo Ngành hàng (Top 15)",
    color='avg_current_price',
    color_continuous_scale="Blues"
)
fig2_1.update_layout(yaxis={'categoryorder':'total ascending'})

# 2. Discount theo category (Top 15 giảm sâu nhất)
fig2_2 = px.bar(
    cat_summary.sort_values('avg_discount', ascending=False).head(15),
    x='avg_discount',
    y='category_name',
    orientation='h',
    title="2.2 Tỷ lệ giảm giá trung bình theo Ngành hàng (Top 15)",
    color='avg_discount',
    color_continuous_scale="Reds"
)
fig2_2.update_layout(yaxis={'categoryorder':'total ascending'})

# 3. Giá trung bình theo Top 15 Seller (Seller có nhiều sản phẩm nhất)
top_sellers = df_p2['seller_name'].value_counts().head(15).index
df_top_sellers = df_p2[df_p2['seller_name'].isin(top_sellers)]
seller_summary = df_top_sellers.groupby('seller_name')['current_price'].mean().reset_index()

fig2_3 = px.bar(
    seller_summary.sort_values('current_price', ascending=False),
    x='current_price',
    y='seller_name',
    orientation='h',
    title="2.3 Giá trung bình của Top 15 Người bán lớn nhất",
    color='current_price',
    color_continuous_scale="Teal"
)
fig2_3.update_layout(yaxis={'categoryorder':'total ascending'})

# 4. Scatter: discount_percent vs current_price (NO LOWESS, dùng OLS)
# Lưu ý: Cần cài đặt thư viện 'statsmodels' để dùng trendline="ols"
fig2_4 = px.scatter(
    df_p2.sample(n=min(20000, len(df_p2)), random_state=7), 
    x="discount_percent", 
    y="current_price", 
    trendline="ols",
    opacity=0.3,
    title="2.4 Quan hệ giữa Tỷ lệ giảm giá và Giá hiện tại (OLS Trendline)",
    color_discrete_sequence=["#8B5CF6"]
)

print("--- ĐANG CHẠY PHẦN 3 ---")

# 1. Nối bảng price_offer với offer_coupon và coupon
# Giả sử bảng price_offer có cột 'offer_id' để link với 'offer_coupon'
df_p3 = df_p2.copy() # Đã chứa price, product, category, seller
df_coupon_link = df_offer_coupon.merge(df_coupon, on='coupon_id', how='left')

# Lọc lấy coupon tốt nhất cho mỗi offer (nếu 1 offer có nhiều coupon)
# Giả định cột 'discount_amount' là giá trị VND được giảm
if 'discount_amount' in df_coupon_link.columns:
    best_coupons = df_coupon_link.groupby('offer_id')['discount_amount'].max().reset_index()
else:
    # Nếu không có discount_amount, tạo một biến giả định để demo logic
    df_coupon_link['discount_amount'] = 10000 # Mock data
    best_coupons = df_coupon_link.groupby('offer_id')['discount_amount'].max().reset_index()

# Merge coupon vào mart tổng
df_full = df_p3.merge(best_coupons, on='offer_id', how='left')

# Điền 0 cho những sản phẩm không có coupon
df_full['coupon_discount_amount'] = df_full['discount_amount'].fillna(0)
df_full['has_coupon'] = df_full['coupon_discount_amount'] > 0

# Tính toán giá cuối cùng và discount thực tế
df_full['final_price'] = df_full['current_price'] - df_full['coupon_discount_amount']
# Đảm bảo giá không bị âm
df_full['final_price'] = df_full['final_price'].apply(lambda x: max(x, 0))

df_full['real_discount_percent'] = round((df_full['original_price'] - df_full['final_price']) / df_full['original_price'] * 100, 2)
# Xử lý các trường hợp lỗi chia cho 0
df_full['real_discount_percent'] = df_full['real_discount_percent'].replace([np.inf, -np.inf], 0).fillna(0)


# --- TRỰC QUAN HÓA INSIGHTS ---

# 3.1 Ảnh hưởng của coupon tới giá (So sánh giá có coupon vs không có)
fig3_1 = px.box(
    df_full, 
    x="has_coupon", 
    y="current_price", 
    color="has_coupon",
    title="3.1 So sánh mức giá trung bình: Có mã giảm giá vs Không có mã",
    labels={"has_coupon": "Được áp mã Coupon", "current_price": "Giá niêm yết (VND)"}
)
fig3_1.update_yaxes(type="log") # Dùng log scale vì giá chênh lệch lớn

# 3.2 Discount thực tế vs Discount hiển thị (Scatter)
fig3_2 = px.scatter(
    df_full[df_full['has_coupon'] == True].sample(n=min(10000, len(df_full))),
    x="discount_percent",
    y="real_discount_percent",
    title="3.2 Độ lệch giữa Giảm giá hiển thị và Giảm giá thực tế (Có Coupon)",
    labels={"discount_percent": "Giảm giá hiển thị (%)", "real_discount_percent": "Giảm giá thực tế (%)"},
    opacity=0.5
)
fig3_2.add_shape(type="line", x0=0, y0=0, x1=100, y1=100, line=dict(color="red", dash="dash"))

# 3.3 Top 10 Ngành hàng có mức GIẢM THÊM (từ coupon) cao nhất
category_coupon = df_full[df_full['has_coupon'] == True].groupby('category_name').agg(
    avg_coupon_value=('coupon_discount_amount', 'mean')
).reset_index().sort_values('avg_coupon_value', ascending=False).head(10)

fig3_3 = px.bar(
    category_coupon,
    x='avg_coupon_value',
    y='category_name',
    orientation='h',
    title="3.3 Top 10 Ngành hàng có giá trị Coupon giảm thêm cao nhất",
    color='avg_coupon_value'
)
fig3_3.update_layout(yaxis={'categoryorder':'total ascending'})

# 3.4 Seller nào xả hàng (giảm giá tổng lực thực tế) mạnh nhất?
seller_discount = df_full.groupby('seller_name').agg(
    avg_real_discount=('real_discount_percent', 'mean'),
    product_count=('product_id', 'count')
).reset_index()
# Lọc các seller có trên 20 sản phẩm
seller_discount = seller_discount[seller_discount['product_count'] >= 20].sort_values('avg_real_discount', ascending=False).head(15)

fig3_4 = px.bar(
    seller_discount,
    x='avg_real_discount',
    y='seller_name',
    orientation='h',
    title="3.4 Top 15 Người bán 'Xả hàng' mạnh nhất (Theo % giảm thực tế)",
    color='avg_real_discount',
    color_continuous_scale="Inferno"
)
fig3_4.update_layout(yaxis={'categoryorder':'total ascending'})