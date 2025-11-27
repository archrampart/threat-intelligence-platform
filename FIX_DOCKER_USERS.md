# Docker'da Kullanıcı Sorunu Çözümü

## Sorun
Docker'da kurulum yapıldıktan sonra default kullanıcılar "notfound" hatası veriyor.

## Neden
Backend startup event'inde database initialization ve user seeding sadece `development` modunda çalışıyordu. 
Docker'da ise `ENVIRONMENT=production` olduğu için kullanıcılar oluşturulmuyordu.

## Çözüm
✅ `backend/app/main.py` dosyası güncellendi:
- Database initialization artık tüm environment'larda çalışıyor
- Default kullanıcı seed işlemi her zaman çalışıyor (zaten varsa skip ediyor)

## Uygulama Adımları

1. Docker container'ları yeniden başlat:
   ```bash
   docker-compose restart backend
   ```

2. Veya tamamen yeniden başlat:
   ```bash
   docker-compose down
   docker-compose up -d --build
   ```

3. Backend loglarını kontrol et:
   ```bash
   docker-compose logs backend | grep -i "seed\|user\|database"
   ```

4. Default kullanıcılar artık oluşturulmuş olmalı:
   - admin / admin123
   - analyst / analyst123
   - viewer / viewer123

## Doğrulama

Backend loglarında şunu görmelisiniz:
```
INFO: Default users seeded
Successfully seeded default users:
  - admin / admin123 (ADMIN)
  - analyst / analyst123 (ANALYST)
  - viewer / viewer123 (VIEWER)
```
