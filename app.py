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

# --- SOL MENÜ: KİTAP YÜKLEME ---
with st.sidebar:
    st.header("📚 Soru Bankası & Deneme Havuzu")
    st.caption("8. sınıf kitap veya deneme PDF'lerinizi buradan sisteme yükleyin.")
    
    uploaded_files = st.file_uploader(
        "PDF Kitap / Deneme Seçin", 
        type=["pdf"], 
        accept_multiple_files=True
    )
    
    if uploaded_files:
        if st.button("Kitapları Sisteme Tanıt ve İndeksle", use_container_width=True):
            with st.spinner("Kitaplar taranıyor, test tipleri ve cevap anahtarları haritalanıyor..."):
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

# --- PEDAGOJİK TALİMAT ŞABLONU ---
BASE_TEACHER_PROMPT = """
Sen LGS hazırlık sürecinde uzman, kavramsal öğretimi merkeze alan tecrübeli bir 8. Sınıf Matematik Öğretmenisin.
Sana referans olarak 8. sınıf soru bankaları ve deneme PDF'leri verilmektedir.

KİTAPLARI ANALİZ EDERKEN ŞU KURALLARA DİKKAT ET:
1. TEST KADEMELERİNİ AYIRT ET: Bir kitabın içinde testler sırayla gider.
   - Kazanım/Kavrama: Temel kuralı doğrudan sorgulayan kısa sorular.
   - Pekiştirme: Orta zorlukta, kısa kurgulu sorular.
   - Yeni Nesil: Günlük hayat bağlamı, şekil/tablo içeren LGS tarzı beceri temelli sorular.
   - Çıkmış/Örnek: MEB sınav soruları formatı.
2. CEVAP ANAHTARI KONTROLÜ: Kitapların sonunda yer alan cevap anahtarlarını kontrol et. Kendi çözümünle cevap anahtarındaki seçeneği karşılaştır. Eğer bir çelişki varsa işlem adımlarını tekrar teyit ederek doğrulanmış sonuca ulaş.
3. PEDAGOJİK ANLATIM: Sadece sonucu söyleme. Öğrenciye formülü neden kullandığını, kritik işlem tuzaklarını ("Burada şuna dikkat et...") açıkla. Matematiksel gösterimleri LaTeX ($...$) formatında yaz.
"""

# --- ANA EKRAN SEKMELERİ ---
st.title("📐 8. Sınıf Akıllı Matematik Asistanı & LGS Koçu")

tab1, tab2, tab3 = st.tabs([
    "📷 Soru Çözümü & Kontrol", 
    "🎯 Kitaptan Soru Seç & Üret", 
    "📊 Deneme Analizi & Telafi Reçetesi"
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
                with st.spinner("Soru çözülüyor, kitap seviyesi belirleniyor ve cevap anahtarı taranıyor..."):
                    payload = [BASE_TEACHER_PROMPT]
                    for _, doc in st.session_state.active_books:
                        payload.append(doc)
                    payload.append(img_obj)
                    payload.append("""
                    Bu soruyu çöz:
                    1. Sorunun seviyesini belirle (Kazanım mı, Pekiştirme mi, Yeni Nesil mi?).
                    2. Eğer bu soru ekteki kitaplardan birindeyse, arka cevap anahtarından kontrol et ve belirt.
                    3. Adım adım pedagojik çözümünü yap.
                    4. 'Öğretmenin Püf Noktası / Dikkat Tuzağı' uyarısı ekle.
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
# SEKME 2: KİTAPTAN SORU SEÇ & ÜRET
# ==========================================
with tab2:
    st.subheader("Kitap Havuzundan Filtreli Soru Seçimi / Üretimi")
    st.caption("Yüklediğiniz kitapların içindeki ilgili seviyedeki testlerden soru seçin veya o kalıpta yeni soru türetin.")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        topic = st.selectbox("Ünite / Konu", [
            "Çarpanlar ve Katlar (EBOB-EKOK)",
            "Üslü İfadeler",
            "Kareköklü İfadeler",
            "Veri Analizi",
            "Basit Olayların Olma Olasılığı",
            "Cebirsel İfadeler ve Özdeşlikler",
            "Doğrusal Denklemler",
            "Eşitsizlikler",
            "Üçgenler",
            "Eşlik ve Benzerlik",
            "Dönüşüm Geometrisi",
            "Geometrik Cisimler"
        ])
    with c2:
        difficulty = st.selectbox("İstenen Soru Seviyesi", [
            "Kazanım / Kavrama Düzeyi (Temel İşlem & Kural)",
            "Pekiştirme Düzeyi (Geçiş & Orta Düzey Problem)",
            "Yeni Nesil / Beceri Temelli (LGS Sınav Düzeyi)",
            "MEB Çıkmış Soru / Örnek Soru Benzeri"
        ])
    with c3:
        mode = st.radio("İşlem Türü", ["Kitaptan Birebir Soru Bul/Getir", "Kitap Formatında Yeni Soru Üret"])
        
    custom_note = st.text_input("Özel Öğretmen Notu (Opsiyonel)", placeholder="Örn: Soruda karekök yaklaşık değer ve cetvel kullanımı olsun.")
    
    if st.button("Soruyu Getir / Üret", type="primary"):
        if not st.session_state.active_books:
            st.warning("Lütfen önce sol menüden en az bir kitap PDF'i yükleyin.")
        else:
            with st.spinner("Kitaplar taranıyor, belirtilen seviyedeki testten soru seçiliyor..."):
                payload = [BASE_TEACHER_PROMPT]
                for _, doc in st.session_state.active_books:
                    payload.append(doc)
                
                payload.append(f"""
                GÖREV:
                Konu: {topic}
                Hedef Seviye: {difficulty}
                İşlem Modu: {mode}
                Ek Öğretmen Notu: {custom_note}

                Yüklenen kitapların içinden '{difficulty}' niteliğindeki test sayfalarını bul.
                Eğer 'Kitaptan Birebir Soru Getir' seçildiyse: O testten tam bu nitelikte bir soruyu, şıklarıyla ve kitabın sonundaki cevap anahtarıyla doğrulanmış çözümüyle aktar.
                Eğer 'Yeni Soru Üret' seçildiyse: Kitaptaki o test seviyesinin dili ve kurgusuyla birebir eşdeğer yeni bir soru yaz ve adım adım çözümünü ekle.
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
# SEKME 3: DENEME KARNESİ & TELAFİ REÇETESİ
# ==========================================
with tab3:
    st.subheader("Öğrenci Deneme Karnesi & Kişisel Telafi Reçetesi")
    st.caption("Öğrencinin LGS denemesinde boş bıraktığı veya yanlış yaptığı kazanımları girin; sistem kitaplardan aşamalı telafi föyü oluştursun.")
    
    student_name = st.text_input("Öğrenci Adı Soyadı", placeholder="Örn: Ahmet Yılmaz")
    incorrect_topics = st.text_area(
        "Yanlış / Boş Bırakılan Konular ve Kazanımlar",
        placeholder="Örn:\n1. EBOB-EKOK problemleri (özellikle aralık bulma)\n2. Kareköklü sayılarda toplama ve yaklaşık değer"
    )
    
    if st.button("Kişiye Özel Telafi Reçetesi Oluştur", type="primary"):
        if not st.session_state.active_books:
            st.warning("Lütfen önce sol menüden en az bir kitap PDF'i yükleyin.")
        elif not incorrect_topics:
            st.warning("Lütfen eksik kazanımları yazın.")
        else:
            with st.spinner(f"{student_name} için kitaplardan özel telafi fasikülü derleniyor..."):
                payload = [BASE_TEACHER_PROMPT]
                for _, doc in st.session_state.active_books:
                    payload.append(doc)
                
                payload.append(f"""
                ÖĞRENCİ TELAFİ PLANI GÖREVİ:
                Öğrenci: {student_name}
                Eksik / Yanlış Yapılan Konular:
                {incorrect_topics}

                Yüklenen kitaplardaki ilgili üniteleri tara ve öğrenci için şu formatta eksiksiz bir 'Kişisel LGS Telafi Föyü' hazırla:
                1. KRİTİK HATIRLATMA (Özet): Her eksik konu için kitaplardaki püf noktaları ve sık yapılan kavram yanılgılarını 3-4 maddede özetle.
                2. AŞAMALI SORU REÇETESİ (Her eksik konu için mutlaka 3 seviye sun):
                   - 🟢 Seviye 1 (Kazanım Sorusu): Temel kavramı oturtmak için.
                   - 🟡 Seviye 2 (Pekiştirme Sorusu): İşlem ve mantığı güçlendirmek için.
                   - 🔴 Seviye 3 (LGS Yeni Nesil Sorusu): Denemede kaçırılan soru tarzının birebir muadili.
                3. CEVAP ANAHTARI VE PEDAGOJİK ÇÖZÜMLER: Soruların sonunda, kitapların arkasındaki cevap anahtarı formatına uygun olarak doğrulanmış detaylı çözümleri sun.
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
