import streamlit as st
from PIL import Image
import os
import tempfile
from google import genai
from google.genai import types

# Sayfa Yapılandırması
st.set_page_config(
    page_title="LGS Matematik Asistanı & Koçu",
    page_icon="📐",
    layout="wide"
)

# API Anahtarı Kontrolü
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")

if not api_key:
    st.error("Lütfen GEMINI_API_KEY anahtarını Streamlit Secrets alanına ekleyin.")
    st.stop()

# Gemini İstemcisi
client = genai.Client(
    api_key=api_key,
    http_options={"api_version": "v1beta"}
)

# Session State Hazırlığı
if "active_books" not in st.session_state:
    st.session_state.active_books = []

# --- MEB RESMİ 8. SINIF LGS KAZANIM LİSTESİ ---
LGS_KAZANIMLAR = [
    "M.8.1.1.1. Pozitif tam sayıların çarpanları ve asal çarpanlar",
    "M.8.1.1.2. İki doğal sayının EBOB ve EKOK'u ve ilgili problemler",
    "M.8.1.1.3. İki doğal sayının aralarında asal olması",
    "M.8.1.2.1. Tam sayıların tam sayı kuvvetleri (Negatif üs dahil)",
    "M.8.1.2.2. Üslü ifadelerle çarpma ve bölme kuralları",
    "M.8.1.2.3. Ondalık gösterimleri 10'un kuvvetleriyle çözümleme",
    "M.8.1.2.4. Çok büyük ve çok küçük sayılar ve bilimsel gösterim",
    "M.8.1.3.1. Tam kare sayılar ve karekök ilişkisi",
    "M.8.1.3.2. Tam kare olmayan sayıların yaklaşık değeri ve aralık bulma",
    "M.8.1.3.3. Kareköklü ifadeyi a√b şeklinde yazma ve katsayıyı kök içine alma",
    "M.8.1.3.4. Kareköklü ifadelerde çarpma ve bölme işlemleri",
    "M.8.1.3.5. Kareköklü ifadelerde toplama ve çıkarma işlemleri",
    "M.8.1.3.6. Doğal sayı yapan çarpanlar (Karekökten kurtarma)",
    "M.8.1.3.7. Ondalık ifadelerin karekökleri",
    "M.8.1.3.8. Gerçek sayılar (Rasyonel ve İrrasyonel ayrımı)",
    "M.8.4.1.1. Çizgi ve sütun grafiklerini yorumlama",
    "M.8.4.1.2. Sütun, daire ve çizgi grafikleri arasında dönüşüm yapma",
    "M.8.5.1.1. Bir olaya ait olası durumları belirleme",
    "M.8.5.1.5. Basit bir olayın olma olasılığını hesaplama",
    "M.8.2.1.1. Basit cebirsel ifadelerin anlamı ve yazımı",
    "M.8.2.1.2. Cebirsel ifadelerin çarpımı",
    "M.8.2.1.3. Özdeşlikler ve geometrik modeller ((a±b)², a²-b²)",
    "M.8.2.1.4. Cebirsel ifadeleri çarpanlarına ayırma",
    "M.8.2.2.1. Birinci dereceden bir bilinmeyenli denklemleri çözme",
    "M.8.2.2.2. Koordinat sistemi ve sıralı ikililer",
    "M.8.2.2.3. Doğrusal denklemlerin grafiğini çizme",
    "M.8.2.2.4. Doğrusal ilişki içeren tablo, grafik ve denklemleri yorumlama",
    "M.8.2.2.5. Doğrunun eğimi ve grafik-denklem ilişkisi",
    "M.8.2.3.1. Günlük hayat durumlarına uygun eşitsizlikler yazma",
    "M.8.2.3.2. Birinci dereceden bir bilinmeyenli eşitsizlikleri çözme ve sayı doğrusu",
    "M.8.3.1.1. Üçgende kenarortay, açıortay ve yükseklik",
    "M.8.3.1.2. Üçgen eşitsizliği (Kenar uzunlukları bağıntısı)",
    "M.8.3.1.3. Açı-kenar bağıntıları",
    "M.8.3.1.5. Pisagor bağıntısı ve yeni nesil problemler",
    "M.8.3.2.2. Benzer çokgenler, benzerlik oranı ve alan-çevre ilişkisi",
    "M.8.3.3.1. Dönüşüm geometrisi (Öteleme ve yansıma)",
    "M.8.3.4.1. Prizmalar, silindir, piramit ve koninin temel elemanları ve açınımları"
]

# --- SOL MENÜ: KİTAP VE KAYNAK YÖNETİMİ ---
with st.sidebar:
    st.header("📚 Soru Bankası & Deneme Havuzu")
    st.caption("8. sınıf PDF kitap veya denemelerinizi buradan yükleyin.")
    
    uploaded_files = st.file_uploader(
        "PDF Kitap / Deneme Seçin", 
        type=["pdf"], 
        accept_multiple_files=True
    )
    
    if uploaded_files:
        if st.button("Kitapları Sisteme Tanıt ve İndeksle", use_container_width=True):
            with st.spinner("Kitaplar taranıyor, seviyeler ve cevap anahtarları haritalanıyor..."):
                processed = []
                for f in uploaded_files:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(f.read())
                        tmp_path = tmp.name
                    
                    try:
                        doc = client.files.upload(
                            file=tmp_path,
                            config=types.UploadFileConfig(display_name=f.name)
                        )
                        processed.append((f.name, doc))
                    finally:
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)
                            
                st.session_state.active_books = processed
                st.success(f"{len(processed)} adet kitap hafızaya alındı!")

    if st.session_state.active_books:
        st.write("---")
        st.subheader("Hafızadaki Kitaplar")
        for name, _ in st.session_state.active_books:
            st.markdown(f"- 📘 `{name}`")

# --- PEDAGOJİK TALİMAT VE KOÇLUK PROTOKOLÜ ---
BASE_TEACHER_PROMPT = """
Sen LGS hazırlık sürecinde uzman, MEB müfredatına ve soru mantığına hâkim bir 8. Sınıf Matematik Öğretmeni ve Öğrenci Koçusun.
Sana referans olarak 8. sınıf soru bankaları ve deneme PDF'leri verilmektedir.

DİKKAT EDİLECEK TEMEL İLKELER:
1. TEST SEVİYELERİNİ AYIRT ET:
   - Kazanım/Kavrama: Temel formül ve işlem becerisi.
   - Pekiştirme: Orta zorlukta, kısa modellemeli sorular.
   - Yeni Nesil: Günlük hayat bağlamı, şekil/tablo içeren LGS tarzı beceri temelli sorular.
2. CEVAP ANAHTARI DOĞRULAMASI: Soruların doğruluğunu kitap sonundaki cevap anahtarlarıyla çapraz denetle.
3. HATA TÜRÜ ANALİZİ (KOÇLUK):
   - Kavram/Kural Hatası: Öğrenciye formülün mantığı ve temel kural hatırlatılmalı.
   - Okuduğunu Anlama/Modelleme Hatası: Sorunun matematik cümlesine nasıl döküleceği gösterilmeli.
   - Süre/İşlem Hatası: Turlama taktiği ve kestirme işlem yöntemleri önerilmeli.
4. Çözümlerde matematiksel gösterimleri LaTeX ($...$) formatında yaz.
"""

# --- ANA EKRAN SEKMELERİ ---
st.title("📐 8. Sınıf Akıllı Matematik Asistanı & LGS Koçu")

tab1, tab2, tab3 = st.tabs([
    "📷 Soru Çözümü & Kontrol", 
    "🎯 Kazanım & Seviyeli Soru Seçimi", 
    "📊 Deneme Analizi & Koçluk Reçetesi"
])

# ==========================================
# SEKME 1: SORU ÇÖZÜMÜ
# ==========================================
with tab1:
    col_img, col_sol = st.columns([1, 1])
    
    with col_img:
        st.subheader("1. Soru Görseli")
        q_img = st.file_uploader("Soru fotoğrafı yükleyin", type=["jpg", "png", "jpeg"], key="q_solver")
        img_obj = None
        if q_img:
            img_obj = Image.open(q_img)
            st.image(img_obj, use_container_width=True)
            
        btn_solve = st.button("Soruyu Analiz Et, Çöz ve Doğrula", type="primary", use_container_width=True)

    with col_sol:
        st.subheader("2. Öğretmen Çözüm Rehberi")
        if btn_solve:
            if not img_obj:
                st.warning("Lütfen önce bir soru fotoğrafı yükleyin.")
            else:
                with st.spinner("Soru çözülüyor, kazanım eşleştiriliyor ve cevap anahtarı taranıyor..."):
                    payload = [BASE_TEACHER_PROMPT]
                    for _, doc in st.session_state.active_books:
                        payload.append(doc)
                    payload.append(img_obj)
                    payload.append("""
                    Bu soruyu analiz et ve çöz:
                    1. Hangi MEB kazanımına ait olduğunu belirt (Örn: M.8.1.1.2).
                    2. Zorluk seviyesini belirle (Kazanım / Pekiştirme / Yeni Nesil).
                    3. Kitaplardaki cevap anahtarıyla teyit edilmiş adım adım çözümü ver.
                    4. 'Öğretmenin Püf Noktası / İşlem Tuzağı' uyarısı ekle.
                    """)
                    
                    try:
                        res = client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=payload,
                            config=types.GenerateContentConfig(temperature=0.2)
                        )
                        st.markdown(res.text)
                    except Exception as e:
                        st.error(f"Hata: {str(e)}")

# ==========================================
# SEKME 2: KAZANIM & SEVİYELİ SORU SEÇİMİ
# ==========================================
with tab2:
    st.subheader("Kazanım Ağacına Göre Soru Çekme & Üretme")
    st.caption("Resmi MEB kazanımını ve istediğiniz zorluk seviyesini seçerek kitaplardan soru getirin.")
    
    col_k1, col_k2 = st.columns([2, 1])
    with col_k1:
        selected_kazanim = st.selectbox("🎯 MEB LGS Matematik Kazanımı", LGS_KAZANIMLAR)
    with col_k2:
        selected_level = st.selectbox("İstenen Soru Seviyesi", [
            "Kazanım / Kavrama Düzeyi (Temel Kural & İşlem)",
            "Pekiştirme Düzeyi (Geçiş & Orta Zorluk)",
            "Yeni Nesil / Beceri Temelli (LGS Düzeyi)",
            "MEB Çıkmış Soru / Örnek Soru Benzeri"
        ])
        
    col_m1, col_m2 = st.columns([1, 2])
    with col_m1:
        op_mode = st.radio("İşlem Modu", ["Kitaptan Birebir Soru Bul", "Kitap Formatında Yeni Soru Üret"])
    with col_m2:
        extra_note = st.text_input("Özel Öğretmen Notu (Opsiyonel)", placeholder="Örn: EBOB-EKOK'ta ağaç dikme veya aralık bulma sorusu olsun.")
        
    if st.button("Soruyu Listele / Üret", type="primary"):
        if not st.session_state.active_books:
            st.warning("Lütfen önce sol menüden en az bir kitap PDF'i yükleyin.")
        else:
            with st.spinner("Kitaplar taranıyor, ilgili kazanım ve test seviyesinden soru getiriliyor..."):
                payload = [BASE_TEACHER_PROMPT]
                for _, doc in st.session_state.active_books:
                    payload.append(doc)
                
                payload.append(f"""
                GÖREV:
                Hedef Kazanım: {selected_kazanim}
                Hedef Seviye: {selected_level}
                İşlem Modu: {op_mode}
                Ek Not: {extra_note}

                Yüklenen kitapları tara. '{selected_kazanim}' kazanımına ait ve '{selected_level}' niteliğindeki test sayfalarından bir soru seç veya üret.
                Soruyu şıklarıyla, doğru seçeneğiyle ve cevap anahtarıyla teyit edilmiş çözümüyle birlikte göster.
                """)
                
                try:
                    res = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=payload,
                        config=types.GenerateContentConfig(temperature=0.3)
                    )
                    st.markdown(res.text)
                except Exception as e:
                    st.error(f"Hata: {str(e)}")

# ==========================================
# SEKME 3: DENEME ANALİZİ & KOÇLUK REÇETESİ
# ==========================================
with tab3:
    st.subheader("📊 LGS Deneme Analizi & Öğrenci Koçluk Reçetesi")
    st.caption("Öğrencinin denemedeki eksik kazanımlarını ve hata kök nedenini seçin; sistem kişisel telafi föyü ve çalışma planı hazırlasın.")
    
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        std_name = st.text_input("Öğrenci Adı Soyadı", placeholder="Örn: Ceren Taşkın")
    with col_s2:
        std_net = st.text_input("Deneme Neti (Doğru / Yanlış / Boş)", placeholder="Örn: 14 Doğru, 4 Yanlış, 2 Boş (12.67 Net)")

    st.write("---")
    st.markdown("#### 🎯 Eksik / Yanlış Yapılan MEB Kazanımları")
    selected_flaws = st.multiselect(
        "Denemede kaçırılan kazanımları seçin (Birden fazla seçebilirsiniz):",
        LGS_KAZANIMLAR,
        default=[LGS_KAZANIMLAR[1], LGS_KAZANIMLAR[8]]
    )
    
    st.markdown("#### 🔍 Hatanın Bilişsel Kök Nedeni (Öğretmen Gözlemi)")
    col_h1, col_h2, col_h3 = st.columns(3)
    with col_h1:
        err_kavram = st.checkbox("📌 Kavram / Kural Boşluğu (Formülü unutma, tanım bilmeme)")
    with col_h2:
        err_model = st.checkbox("📖 Okuduğunu Anlama / Modelleme (Soruyu denkleme dökememe)")
    with col_h3:
        err_sure = st.checkbox("⏱️ Süre / İşlem Hatası (Vakit yetmeme, işlemde takılma)")
        
    coach_notes = st.text_area("Öğrenci Hakkında Ek Koçluk Gözlemi (Opsiyonel)", placeholder="Örn: Yeni nesil sorularda şekli yorumlamakta zorlanıyor, hemen pes ediyor.")

    if st.button("Kişiye Özel LGS Koçluk Raporu ve Telafi Föyü Oluştur", type="primary", use_container_width=True):
        if not st.session_state.active_books:
            st.warning("Lütfen önce sol menüden en az bir kitap PDF'i yükleyin.")
        elif not selected_flaws:
            st.warning("Lütfen en az bir eksik kazanım seçin.")
        else:
            with st.spinner(f"{std_name} için deneme analizi yapılıyor ve kitaplardan telafi reçetesi derleniyor..."):
                error_types = []
                if err_kavram: error_types.append("Kavram/Kural Boşluğu")
                if err_model: error_types.append("Okuduğunu Anlama/Modelleme Hatası")
                if err_sure: error_types.append("Süre Yönetimi ve İşlem Hatası")

                payload = [BASE_TEACHER_PROMPT]
                for _, doc in st.session_state.active_books:
                    payload.append(doc)
                
                prompt_analysis = f"""
                LGS MATEMATİK ÖĞRENCİ KOÇLUK RAPORU GÖREVİ:
                Öğrenci: {std_name}
                Mevcut Net Durumu: {std_net}
                Eksik Kazanımlar: {selected_flaws}
                Tespit Edilen Hata Türleri: {error_types}
                Öğretmen Notu: {coach_notes}

                Lütfen yüklenen kitapları referans alarak öğrenci için şu bölümlerden oluşan kapsamlı bir 'LGS Koçluk & Telafi Raporu' hazırla:

                1. 📋 BİLİŞSEL KOÇLUK ANALİZİ:
                   - Öğrencinin seçilen hata türlerine göre psikolojik ve stratejik durumu nedir?
                   - LGS'de bu kazanımların soru potansiyeli nedir ve öğrenci nerelerde takılıyor?

                2. 💡 HIZLI KAZANIM HATIRLATMA REÇETESİ:
                   - Seçilen her kazanım için kitaplardaki püf noktaları, kritik formülleri ve tuzak noktaları 2'şer maddede özetle.

                3. 📚 KİTAPLARDAN KADEMELİ ÇALIŞMA SORU SETİ:
                   - Seçilen her eksik kazanım için yüklenen kitaplardaki ilgili testleri tara ve şu 3 seviyede soru listele:
                     * 🟢 Seviye 1 (Kazanım Sorusu): Temel kuralı oturtmak için.
                     * 🟡 Seviye 2 (Pekiştirme Sorusu): Muhakeme ve geçiş sorusu.
                     * 🔴 Seviye 3 (LGS Yeni Nesil Sorusu): Denemede kaçırılan sorunun birebir muadili beceri temelli soru.

                4. 🎯 HAFTALIK KOÇLUK EYLEM PLANI:
                   - Öğrencinin bu eksikleri kapatması için önümüzdeki 7 günde kaç soru çözmesi ve hangi gün neye çalışması gerektiğine dair somut bir çalışma takvimi.
                """
                payload.append(prompt_analysis)
                
                try:
                    res = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=payload,
                        config=types.GenerateContentConfig(temperature=0.25)
                    )
                    st.markdown(res.text)
                except Exception as e:
                    st.error(f"Hata: {str(e)}")
