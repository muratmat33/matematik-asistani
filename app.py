import streamlit as st
from PIL import Image
import os
import tempfile
import json
import pypdfium2 as pdfium
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

# Oturum Durumları
if "active_books" not in st.session_state:
    st.session_state.active_books = []  # [(name, doc_ref, temp_pdf_path)]

# --- YARDIMCI FONKSİYON: PDF SAYFASINI RESME DÖNÜŞTÜRME ---
def render_pdf_page_as_image(pdf_path, page_number):
    try:
        pdf = pdfium.PdfDocument(pdf_path)
        if 1 <= page_number <= len(pdf):
            page = pdf[page_number - 1]
            image = page.render(scale=2.0).to_pil() # 2x ölçek ile net görüntü
            return image
    except Exception as e:
        st.error(f"Sayfa görselleştirilemedi: {str(e)}")
    return None

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

# --- SOL MENÜ: KİTAP YÜKLEME ---
with st.sidebar:
    st.header("📚 Soru Bankası & Deneme Havuzu")
    st.caption("8. sınıf PDF kitap veya denemenizi buradan yükleyin.")
    
    uploaded_files = st.file_uploader(
        "PDF Kitap / Deneme Seçin", 
        type=["pdf"], 
        accept_multiple_files=True
    )
    
    if uploaded_files:
        if st.button("Kitapları Sisteme Tanıt ve İndeksle", use_container_width=True):
            with st.spinner("Kitaplar işleniyor, sayfalar ve cevap anahtarları haritalanıyor..."):
                processed = []
                for f in uploaded_files:
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                    tmp.write(f.read())
                    tmp_path = tmp.name
                    
                    try:
                        doc = client.files.upload(
                            file=tmp_path,
                            config=types.UploadFileConfig(display_name=f.name)
                        )
                        processed.append((f.name, doc, tmp_path))
                    except Exception as e:
                        st.error(f"Hata ({f.name}): {str(e)}")
                            
                st.session_state.active_books = processed
                st.success(f"{len(processed)} adet kitap hafızaya alındı!")

    if st.session_state.active_books:
        st.write("---")
        st.subheader("Hafızadaki Kitaplar")
        for name, _, _ in st.session_state.active_books:
            st.markdown(f"- 📘 `{name}`")

# --- PEDAGOJİK TALİMAT VE KOÇLUK PROTOKOLÜ ---
BASE_TEACHER_PROMPT = """
Sen LGS hazırlık sürecinde uzman, MEB müfredatına ve soru mantığına hâkim bir 8. Sınıf Matematik Öğretmeni ve Bilişsel Öğrenci Koçusun.
Sana referans olarak 8. sınıf soru bankaları ve deneme PDF'leri verilmektedir.

DİKKAT EDİLECEK TEMEL İLKELER:
1. FORMÜLLER VE İŞLEMLER: Matematiksel tüm gösterimleri, köklü ifadeleri, üslü sayıları ve denklemleri kesinlikle LaTeX formatında yaz ($...$ veya $$...$$). Asla düz metin halinde geçiştirme.
2. CEVAP ANAHTARI DOĞRULAMASI: Soruların doğruluğunu kitap sonundaki cevap anahtarlarıyla çapraz denetle.
3. KADEMELİ ANALİZ: Sorunun kazanım düzeyini (Kazanım / Pekiştirme / Yeni Nesil) belirt.
"""

# --- ANA EKRAN SEKMELERİ ---
st.title("📐 8. Sınıf Akıllı Matematik Asistanı & LGS Koçu")

tab1, tab2, tab3 = st.tabs([
    "📷 Soru Çözümü & Kontrol", 
    "🎯 Kitaptan Soru Getir (Görsel + LaTeX)", 
    "📊 Deneme Analizi & Koçluk Reçetesi"
])

# ==========================================
# SEKME 1: FOTOĞRAFTAN SORU ÇÖZÜMÜ
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
            
        teacher_feedback = st.text_input(
            "Öğretmen İpucu / Düzeltme Notu (Opsiyonel):",
            placeholder="Örn: Doğru cevap D şıkkı / Havuzun kenarını kök 72 olarak al."
        )
        
        btn_solve = st.button("Soruyu Analiz Et, Çöz ve Doğrula", type="primary", use_container_width=True)

    with col_sol:
        st.subheader("2. Öğretmen Çözüm Rehberi")
        if btn_solve:
            if not img_obj:
                st.warning("Lütfen önce bir soru fotoğrafı yükleyin.")
            else:
                with st.spinner("Soru çözülüyor, kazanım eşleştiriliyor ve cevap anahtarı taranıyor..."):
                    payload = [BASE_TEACHER_PROMPT]
                    for _, doc, _ in st.session_state.active_books:
                        payload.append(doc)
                    payload.append(img_obj)
                    
                    prompt_instruction = """
                    Bu soruyu pedagojik olarak analiz et ve çöz:
                    1. Hangi MEB kazanımına ait olduğunu belirt (Örn: M.8.1.1.2).
                    2. Zorluk seviyesini belirle (Kazanım / Pekiştirme / Yeni Nesil).
                    3. Kitaplardaki cevap anahtarıyla teyit edilmiş adım adım çözümü ver. Tüm formülleri LaTeX ($...$) olarak yaz.
                    4. 'Öğretmenin Püf Noktası / İşlem Tuzağı' uyarısı ekle.
                    """
                    
                    if teacher_feedback:
                        prompt_instruction += f"\n\nÖNEMLİ ÖĞRETMEN DÜZELTMESİ / İPUCU: '{teacher_feedback}'. Bu notu doğrudan referans alarak çözümü ve sonucu bu doğrultuda kesinleştir."
                        
                    payload.append(prompt_instruction)
                    
                    try:
                        res = client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=payload,
                            config=types.GenerateContentConfig(temperature=0.1)
                        )
                        st.markdown(res.text)
                    except Exception as e:
                        st.error(f"Hata: {str(e)}")

# ==========================================
# SEKME 2: KİTAPTAN GÖRSEL SORU ÇEKME & LATEX ÇÖZÜM
# ==========================================
with tab2:
    st.subheader("Kitaptan Orijinal Görsel Soru Getirme")
    st.caption("Kazanım ve seviye seçin; sistem kitaptaki ilgili sayfanın görselini kesip getirsin ve altına LaTeX çözümü eklesin.")
    
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
        
    extra_filter_note = st.text_input("Özel Filtre (Opsiyonel)", placeholder="Örn: Soruda cetvel veya daire grafiği olsun.")
    
    if st.button("Soruyu Kitaptan Görsel Olarak Getir", type="primary"):
        if not st.session_state.active_books:
            st.warning("Lütfen önce sol menüden bir kitap PDF'i yükleyin.")
        else:
            with st.spinner("Kitap taranıyor, ilgili soru sayfası tespit ediliyor..."):
                active_book_name, active_doc, active_path = st.session_state.active_books[0]
                
                payload = [
                    BASE_TEACHER_PROMPT,
                    active_doc,
                    f"""
                    GÖREV:
                    Bu PDF kitabın içini tara.
                    Hedef Kazanım: '{selected_kazanim}'
                    Hedef Seviye: '{selected_level}'
                    Ek Kriter: '{extra_filter_note}'

                    Bu kriterlere tam uyan sorunun yer aldığı PDF SAYFA NUMARASINI tespit et.
                    Ardından bu sorunun detaylı çözümünü hazırla.
                    
                    YANITINI ŞU JSON FORMATINDA VER:
                    ```json
                    {{
                        "page_number": 15,
                        "question_title": "Test 3 - Soru 4",
                        "answer_key": "C",
                        "solution_latex": "Adım adım LaTeX destekli çözüm metni...",
                        "teacher_tip": "Öğretmenin dikkat tuzağı uyarısı..."
                    }}
                    ```
                    Not: Sadece saf JSON formatında yanıt ver. Sayfa numarası PDF'in gerçek fiziksel sayfa indeksi (1'den başlayan) olmalıdır.
                    """
                ]
                
                try:
                    res = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=payload,
                        config=types.GenerateContentConfig(
                            temperature=0.1,
                            response_mime_type="application/json"
                        )
                    )
                    
                    data = json.loads(res.text)
                    page_num = data.get("page_number", 1)
                    q_title = data.get("question_title", "Tespit Edilen Soru")
                    ans_key = data.get("answer_key", "-")
                    sol_latex = data.get("solution_latex", "")
                    tip = data.get("teacher_tip", "")
                    
                    st.markdown(f"### 📖 {active_book_name} - {q_title} (Sayfa {page_num})")
                    
                    # Sayfayı resim olarak getir ve göster
                    col_page_img, col_page_sol = st.columns([1, 1])
                    
                    with col_page_img:
                        st.subheader("🖼️ Kitaptaki Orijinal Soru Sayfası")
                        rendered_img = render_pdf_page_as_image(active_path, page_num)
                        if rendered_img:
                            st.image(rendered_img, caption=f"PDF Sayfa {page_num}", use_container_width=True)
                        else:
                            st.warning("Sayfa görseli oluşturulamadı.")
                            
                    with col_page_sol:
                        st.subheader("📝 LaTeX Destekli Pedagojik Çözüm")
                        st.info(f"**Doğrulanmış Cevap Şıkkı:** {ans_key}")
                        st.markdown(sol_latex)
                        if tip:
                            st.warning(f"**💡 Öğretmenin Püf Noktası:**\n\n{tip}")
                            
                except Exception as e:
                    st.error(f"Soru getirilirken bir hata oluştu: {str(e)}")

# ==========================================
# SEKME 3: DENEME ANALİZİ & KOÇLUK REÇETESİ
# ==========================================
with tab3:
    st.subheader("📊 LGS Deneme Analizi & Öğrenci Koçluk Reçetesi")
    st.caption("Öğrencinin eksik kazanımlarını ve hata kök nedenini seçin; sistem kitaplardan aşamalı telafi föyü ve çalışma planı hazırlasın.")
    
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        std_name = st.text_input("Öğrenci Adı Soyadı", placeholder="Örn: Ceren Taşkın")
    with col_s2:
        std_net = st.text_input("Deneme Neti (Doğru / Yanlış / Boş)", placeholder="Örn: 14 Doğru, 4 Yanlış, 2 Boş (12.67 Net)")

    st.write("---")
    st.markdown("#### 🎯 Eksik / Yanlış Yapılan MEB Kazanımları")
    selected_flaws = st.multiselect(
        "Denemede kaçırılan kazanımları seçin:",
        LGS_KAZANIMLAR,
        default=[LGS_KAZANIMLAR[1], LGS_KAZANIMLAR[8]]
    )
    
    st.markdown("#### 🔍 Hatanın Bilişsel Kök Nedeni (Öğretmen Gözlemi)")
    col_h1, col_h2, col_h3 = st.columns(3)
    with col_h1:
        err_kavram = st.checkbox("📌 Kavram / Kural Boşluğu (Formülü unutma, tanım bilmeme)")
    with col_h2:
        err_model = st.checkbox("📖 Yeni Nesil / Modelleme Tıkanması (Soruyu denkleme dökememe)")
    with col_h3:
        err_sure = st.checkbox("⏱️ Dikkat / Süre / İşlem Hatası (Acelecilik, işlemde takılma)")
        
    coach_notes = st.text_area("Öğrenci Hakkında Ek Koçluk Gözlemi (Opsiyonel)", placeholder="Örn: Cetvelli sorularda yaklaşık değer aralığını bulurken süre kaybediyor.")

    if st.button("Kişiye Özel LGS Koçluk Raporu ve Telafi Föyü Oluştur", type="primary", use_container_width=True):
        if not st.session_state.active_books:
            st.warning("Lütfen önce sol menüden sisteme bir kitap PDF'i ekleyin.")
        elif not selected_flaws:
            st.warning("Lütfen en az bir eksik kazanım seçin.")
        else:
            with st.spinner(f"{std_name} için deneme analizi yapılıyor ve telafi föyü hazırlanıyor..."):
                error_types = []
                if err_kavram: error_types.append("Kavram/Kural Boşluğu")
                if err_model: error_types.append("Yeni Nesil / Modelleme Tıkanması")
                if err_sure: error_types.append("Dikkat / Süre / İşlem Hatası")

                payload = [BASE_TEACHER_PROMPT]
                for _, doc, _ in st.session_state.active_books:
                    payload.append(doc)
                
                prompt_analysis = f"""
                LGS MATEMATİK ÖĞRENCİ KOÇLUK RAPORU:
                Öğrenci: {std_name}
                Mevcut Net Durumu: {std_net}
                Eksik Kazanımlar: {selected_flaws}
                Tespit Edilen Hata Türleri: {error_types}
                Öğretmen Notu: {coach_notes}

                TÜM MATEMATİKSEL İFADELERİ KESİNLİKLE OKUNAKLI LATEX ($...$) İLE YAZ.
                
                Şu formatta rapor hazırla:
                1. 📋 BİLİŞSEL KOÇLUK TEŞHİSİ: Hata türlerine göre öğrencinin bilişsel analizi.
                2. 💡 HIZLI KAZANIM VE TUZAK HATIRLATMA: Her kazanım için formül ve düşülen işlem tuzakları ($...$ formatında).
                3. 📚 KİTAPTAN KADEMELİ ÇALIŞMA SORULARI:
                   Kitaptaki ilgili sayfaları belirt (Örn: 'Sayfa 42, Test 5, Soru 3').
                   - Seviye 1 (Kazanım)
                   - Seviye 2 (Pekiştirme)
                   - Seviye 3 (Yeni Nesil)
                4. 🎯 7 GÜNLÜK ÇALIŞMA REÇETESİ: Gün gün soru hedefi.
                """
                payload.append(prompt_analysis)
                
                try:
                    res = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=payload,
                        config=types.GenerateContentConfig(temperature=0.2)
                    )
                    st.markdown(res.text)
                except Exception as e:
                    st.error(f"Hata: {str(e)}")
