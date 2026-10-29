# Noctemsol MAL Classic otomatik künye

Bu depo `noctemsol` hesabının **herkese açık** anime/manga listelerini günlük tarar.
Jikan Edge üzerinden eserlerin alternatif isimlerini, türlerini, stüdyo/yazar,
format, bölüm sayısı ve genel puan bilgilerini alır. Sonra MAL Classic
listesinde native **More** düğmesi ile açılabilen CSS künye panellerini üretir.

## GitHub kurulumu

1. GitHub'da `noctemsol-mal-kunye` adında **public** bir depo aç.
2. Bu klasörün **içindekileri**, `.github` klasörü dahil, deponun köküne yükle.
3. `Settings → Pages → Build and deployment → Source` ayarını **GitHub Actions** yap.
4. `Actions → Update MAL künye → Run workflow` ile ilk çalışmayı başlat.
5. Yeşil tikli `deploy` işi tamamlanınca `https://GITHUB_KULLANICI_ADIN.github.io/noctemsol-mal-kunye/kunye.css` adresinin açıldığını kontrol et.
6. MAL Classic özel CSS'inin **başına** şunu ekle:

   ```css
   @\import "https://GITHUB_KULLANICI_ADIN.github.io/noctemsol-mal-kunye/kunye.css";
   ```

   MAL'ın CSS URL kontrolü nedeniyle `@\import` biçimindeki ters eğik çizgi önemlidir.

7. MAL CSS içindeki eski FMAB'a özel More/künye denemesini kaldır. Genel
   **Edit / More** düğmesi düzenini koru. İçerik kodu artık depodan gelir.

## Sınırlar

- Künye CSS ile `::before` ve `::after` metinleri olarak oluşturulur. Bu metinler
  bazı tarayıcılarda güvenilir biçimde seçilip **kopyalanamaz**. Kopyalanabilir
  gerçek metin, MAL Classic sayfasına JavaScript enjekte edilmeden mümkün değildir.
- Veri kaynağı geçici olarak yanıt vermezse kayıt önbellekten korunur; yeni eser
  ertesi çalışmada tekrar denenir. **Public listede görünmeyen** eserler eklenmez.
- Genel puan günlük işin çalışmasına göre yenilenir; gerçek zamanlı değildir.
- GitHub, uzun süre etkin olmayan public depoların zamanlanmış işlerini
  durdurabilir. `Actions` sekmesinden yeniden etkinleştirmek gerekebilir.
- İleride CSS boyutu çok büyürse MAL'ın özel CSS boyut/perf sınırlarını kontrol et.

## Yerel üretim

Python 3.12+ ile:

```bash
python scripts/generate.py
```

İlk çalıştırma tüm eserler için Jikan sorguları nedeniyle birkaç dakika sürebilir.
Sonraki çalışmalarda 28 gün içinde alınan ayrıntılar önbellekten kullanılır.
