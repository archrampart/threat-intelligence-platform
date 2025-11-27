# IOC Client Entegrasyon Planı

Bu doküman, gerçek IOC kaynaklarına (VirusTotal, AbuseIPDB, OTX, vs.) bağlanacak client modülleri için izlenecek yaklaşımı özetler.

## 1. Ortak Tasarım İlkeleri
- Her kaynak için `BaseThreatClient` sınıfından türeyen ayrı bir client yazılacak.
- Client'lar async olacak ve `query(ioc_type, ioc_value)` metodunu implemente edecek.
- Her client isteği sonucunda standart alanlar döndürecek:
  - `status`: success | error | not_supported
  - `risk_score`: 0-1 aralığında normalize skor
  - `message`: açıklama
  - `raw`: servis tarafından dönen ham veri (debug/inceleme için)
- İstek süreleri için timeout (örn. 10 sn) ve retry (örn. 2 deneme) politikası uygulanacak.
- Rate limitler için basit throttle (örn. asyncio.Semaphore veya internal counter) eklenecek.

## 2. Yapılandırma
- Ortak ayarlar `.env` üzerinden yönetilecek (örn. `VIRUSTOTAL_API_KEY`).
- Client özelinde endpoint URL, timeout gibi değerler `Settings` içine eklenecek.
- Gerektiğinde client bazlı enable/disable flag'i kullanılacak (örn. `ENABLE_VIRUSTOTAL=1`).

## 3. Modüler Dizayn
```
app/services/
  base_client.py
  client_registry.py
  clients/
    __init__.py
    virustotal.py
    abuseipdb.py
    otx.py
```
- `clients` klasörü gerçek entegrasyonları barındıracak.
- Registry, `.register("virustotal", VirusTotalClient(...))` şeklinde yükleme yapacak.
- İleride otomatik discovery için entry point mekanizması eklenebilir.

## 4. VirusTotal Entegrasyon Planı
- Endpoint: `https://www.virustotal.com/api/v3/{ioc_type}` (IP: `/ip_addresses/{ip}` vb.)
- Auth: Header `x-apikey`
- Rate Limit: Ücretsiz 4 istek/dk (approx). Basit sleep/semaphore ile sınırlanacak.
- Response'tan alınacak alanlar:
  - `data.attributes.last_analysis_stats` (malicious, suspicious, harmless)
  - `reputation`, `last_modification_date`
- Risk skor hesaplama:
  - `malicious` oranı yüksekse 0.8+, `suspicious` varsa 0.6, aksi 0.2

## 5. AbuseIPDB Entegrasyon Planı
- Endpoint: `https://api.abuseipdb.com/api/v2/check`
- Auth: Header `Key`
- Limit: 1,000 sorgu/gün (ücretsiz). Rate limit kontrolü eklenecek.
- Önemli alanlar: `data.abuseConfidenceScore`, `data.totalReports`, `data.lastReportedAt`
- Risk skor: `abuseConfidenceScore / 100`

## 6. OTX (AlienVault) Entegrasyon Planı
- Endpoint: `https://otx.alienvault.com/api/v1/indicators/{type}/{value}/general`
- Auth: Header `X-OTX-API-KEY`
- Veri: Pulse sayısı, tags, reputation gibi bilgiler
- Risk skor: pulse sayısı + `threat_score` alanından türetilir (ör: min(pulse_count/10, 1.0))

## 7. Error Handling & Logging
- Tüm client hataları `logger.warning` ile kayıt altına alınacak.
- Hata durumunda `status="error"`, `message=str(exc)` döndürülür.
- Ağ hatalarında exponential backoff (örn. 0.5s, 1s) opsiyonel.

## 8. Test Stratejisi
- Client başına unit test (API yanıtlarını fixture ile taklit etme).
- Integration test: gerçek servislerle (opsiyonel) veya mock server ile.
- Rate limit ve timeout senaryoları için testler.

## 9. Sonraki Adımlar
1. `app/services/clients/virustotal.py` oluşturup registry'ye kaydet.
2. AbuseIPDB ve OTX client'larını ekle.
3. Rate limit ve cache mekanizmalarını devreye al.
4. Watchlist ve CVE modülleri bu client sonuçlarını kullanacak.
