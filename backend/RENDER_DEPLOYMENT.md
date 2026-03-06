# 🚀 Deploy BusHappy Backend lên Render

## Phương pháp 1: Sử dụng Render.yaml (Khuyến nghị)

### Bước 1: Chuẩn bị Repository
```bash
# Đảm bảo tất cả file cần thiết đã được commit
git add .
git commit -m "Add Render deployment config"
git push origin main
```

### Bước 2: Tạo Web Service trên Render
1. Truy cập https://render.com và đăng ký/đăng nhập
2. Click **"New +"** → **"Web Service"**
3. Kết nối GitHub repository của bạn
4. Render sẽ tự động phát hiện file `render.yaml`
5. Click **"Apply"** để tạo service

---

## Phương pháp 2: Cấu hình thủ công trên Dashboard

### Bước 1: Tạo New Web Service
1. Truy cập https://dashboard.render.com
2. Click **"New +"** → **"Web Service"**
3. Kết nối repository GitHub/GitLab

### Bước 2: Cấu hình Build Settings
**Thiết lập cơ bản:**
- **Name:** `bushappy-api`
- **Region:** Singapore (gần Việt Nam nhất)
- **Branch:** `main`
- **Root Directory:** `backend` (nếu backend ở subfolder)
- **Environment:** `Python 3`
- **Build Command:**
  ```bash
  pip install -r requirements.txt && cd data_preprocessing && python generate_gtfs.py && cd ..
  ```
- **Start Command:**
  ```bash
  gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
  ```

### Bước 3: Cấu hình Environment Variables
Thêm các biến môi trường:
- `BUSHAPPY_ENV` = `production` (hoặc `sandbox` để test)
- `PYTHON_VERSION` = `3.11.0`

### Bước 4: Chọn Plan
- **Free Plan:** 750 giờ/tháng, auto-sleep sau 15 phút không dùng
- **Starter Plan ($7/month):** Không sleep, tốc độ tốt hơn

### Bước 5: Deploy
Click **"Create Web Service"** và chờ deploy (5-10 phút)

---

## Sau khi Deploy thành công

### URL của bạn sẽ có dạng:
```
https://bushappy-api.onrender.com
```

### Test API endpoints:
```bash
# Test health check
curl https://bushappy-api.onrender.com/api/environment/info

# Test nearby stops
curl "https://bushappy-api.onrender.com/api/nearby_stops?lat=10.762622&lon=106.660172&radius=1"

# Test routes list
curl https://bushappy-api.onrender.com/api/routes
```

### Cập nhật Frontend config:
Sửa file `frontend/.env`:
```env
VITE_API_URL=https://bushappy-api.onrender.com/api
```

---

## ⚠️ Lưu ý quan trọng

### 1. Free Plan Limitations:
- Service sẽ **sleep** sau 15 phút không có request
- Request đầu tiên sau khi sleep sẽ mất 30-50 giây để wake up
- 750 giờ/tháng (khoảng 31 ngày nếu chạy liên tục)

### 2. Dữ liệu GTFS:
- Dữ liệu sẽ được generate trong build command
- File system trên Render là **ephemeral** (tạm thời)
- Mỗi lần deploy lại, data sẽ được tạo mới

### 3. Persistent Storage (Tùy chọn):
Nếu cần lưu data lâu dài, sử dụng Render Disks:
```yaml
disk:
  name: gtfs-data
  mountPath: /opt/render/project/src/backend/gtfs
  sizeGB: 1
```

### 4. Production vs Sandbox:
- **Production mode:** Dùng dữ liệu `gtfs/` (real data)
- **Sandbox mode:** Dùng dữ liệu `gtfs_sandbox/` (test data)
- Đặt `BUSHAPPY_ENV=production` trong Environment Variables

### 5. CORS Configuration:
Backend đã có `flask-cors` nên frontend từ domain khác có thể gọi API

---

## 🔧 Troubleshooting

### Build failed?
- Check logs trong Render dashboard
- Đảm bảo `requirements.txt` có đủ dependencies
- Xem có file `generate_gtfs.py` không

### Service crash sau khi start?
- Check logs: `gunicorn` có start được không?
- Đảm bảo có file `wsgi.py`
- Test local: `gunicorn wsgi:app`

### API trả về 404?
- Kiểm tra routes trong `api_server.py`
- Đảm bảo prefix `/api` đúng
- Test: `curl https://your-app.onrender.com/api/routes`

### Slow performance?
- Upgrade lên Starter plan ($7/month)
- Tăng số workers trong start command: `--workers 4`
- Optimize pandas queries trong code

---

## 📊 Monitoring

Render cung cấp:
- **Logs:** Real-time logs trong dashboard
- **Metrics:** CPU, Memory usage
- **Alerts:** Email khi service down

---

## 🔄 Auto-deploy

Mỗi khi push code lên GitHub:
1. Render tự động detect thay đổi
2. Chạy build command
3. Deploy version mới
4. Zero-downtime deployment

Để tắt auto-deploy: Vào Settings → **Disable "Auto-Deploy"**

---

## 💰 Chi phí ước tính

### Free Plan:
- **Chi phí:** $0
- **Giới hạn:** 750 giờ/tháng, auto-sleep

### Starter Plan:
- **Chi phí:** $7/tháng
- **Ưu điểm:** Không sleep, 1GB RAM, fast startup

### Standard Plan:
- **Chi phí:** $25/tháng
- **Ưu điểm:** 4GB RAM, better performance

---

## 🌐 Deploy cùng với Frontend

Nếu deploy frontend lên Vercel/Netlify:
1. Set `VITE_API_URL` = Render backend URL
2. Deploy frontend
3. Cả hai sẽ hoạt động độc lập

**Ví dụ:**
- Backend: `https://bushappy-api.onrender.com`
- Frontend: `https://bushappy.vercel.app`
