import streamlit as st
from PIL import Image
import os
import tempfile
from google import genai
from google.genai import types

# Sayfa yapılandırması
st.set_page_config(
    page_title="8. Sınıf Matematik Asistanı",
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

# Session State Hazırlığı (Yüklenen PDF referanslarını saklamak için)
if "uploaded_pdf_files" not in st.session_state:
    st.session_state.uploaded_pdf_files = []

# --- YAN MENÜ: ÖĞRETMEN PDF & KAYNAK YÖNETİMİ ---
with st.sidebar:
    st.header("📚 Ders Kaynakları & PDF Havuzu")
    st.caption("8. sınıf deneme, soru bankası veya konu föyü PDF'lerini buradan sisteme yükleyin.")
    
    uploaded_pdfs = st.file_uploader(
        "Kitap veya Deneme PDF'i Seçin", 
        type=["pdf"], 
        accept_multiple_files=True
    )
    
    if uploaded_pdfs:
        if st.button("Seçilen PDF'leri Asistana Tanıt", use_container_width=True):
            with st.spinner("Kitap ve denemeler analiz ediliyor..."):
                processed_files = []
                for pdf_file in uploaded_pdfs:
                    # Geçici olarak diske kaydet ve Gemini Files API'ye aktar
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(pdf_file.read())
                        tmp_path = tmp.name
                    
                    try:
                        uploaded_doc = client.files.upload(
                            file=tmp_path,
                            config=types.UploadFileConfig(display_name=pdf_file.name)
                        )
                        processed_files.append((pdf_file.name, uploaded_doc))
                    finally:
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)
                            
                st.session_state.uploaded_pdf_files = processed_files
                st.success(f"{len(processed_files)} adet kaynak başarıyla hafızaya alındı!")

    if st.session_state.uploaded_pdf_files:
        st.write("---")
        st.subheader("Aktif Kaynaklar")
        for name, _ in st.session_state.uploaded_pdf_files:
            st.markdown(f"- 📄 `{name}`")

# --- KLASÖR NOTLARINI YÜKLEME ---
@st.cache_data
def load_curriculum_notes(folder_path="notlar"):
    combined_notes = ""
    if os.path.exists(folder_path):
        for file_name in os.listdir(folder_path):
            if file_name.endswith((".txt", ".md")):
                with open(os.path.join(folder_path, file_name), "r", encoding="utf-8") as f:
                    combined_notes += f"\n--- {file_name} ---\n" + f.read()
    return combined_notes

curriculum_context = load_curriculum_notes()

# --- ANA EKRAN ---
st.title("📐 8. Sınıf Akıllı Matematik Çözüm & Öğretmen Asistanı")
st.caption("Öğrenci soru fotoğrafını yükler; asistan yüklediğiniz kitap ve deneme mantığıyla pedagojik çözüm sunar.")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. Soru Fotoğrafı")
    uploaded_file = st.file_uploader(
        "Kamera veya galeriden soru yükleyin", 
        type=["jpg", "jpeg", "png", "webp"]
    )
    
    image = None
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Yüklenen Soru", use_container_width=True)
        
    solve_button = st.button("Soruyu Analiz Et ve Çöz", type="primary", use_container_width=True)

with col2:
    st.subheader("2. Pedagojik Çözüm Rehberi")
    
    if solve_button:
        if uploaded_file is None:
            st.warning("Lütfen önce sol taraftan bir soru fotoğrafı yükleyin.")
        else:
            with st.spinner("Soru inceleniyor, kaynak kitaplar taranıyor ve çözüm hazırlanıyor..."):
                try:
                    # Sistem Promptu
                    system_prompt = f"""
Sen sabırlı, motive edici, kavramsal anlamayı merkeze alan uzman bir 8. Sınıf İlköğretim Matematik Öğretmenisin.
Sana bir öğrencinin takıldığı sorunun görseli ve referans alabileceğin deneme/kitap PDF'leri ile öğretmen ders notları sunulmaktadır.

[DERS VE KAZANIM NOTLARI]
{curriculum_context}

GÖREVLERİN:
1. Görseldeki soruyu, verileri ve şekilleri titizlikle analiz et.
2. Çözümü yaparken varsa hafızandaki PDF kitaplarındaki yaklaşım tarzını ve yukarıdaki ders notlarını temel al.
3. Asla sadece cevabı verme. Adım adım, neden-sonuç bağı kurarak LGS düzeyinde rehberlik et.
4. "Öğretmenin Püf Noktası / Dikkat Tuzağı" başlığı altında öğrencilerin sıkça yaptığı işlem veya okuma hatalarını belirt.
5. Çözümün en sonuna, öğrencinin konuyu pekiştirmesi için yüklenen denemelerdeki soru formatına uygun YENİ BİR BENZER PEKİŞTİRME SORUSU ve kısa cevabını ekle.
6. Matematiksel formülleri LaTeX ($...$) olarak biçimlendir.
"""
                    # Gönderilecek içerikler listesi
                    contents_payload = [system_prompt]
                    
                    # Varsa yüklenen PDF dökümanlarını ekle
                    for _, doc_ref in st.session_state.uploaded_pdf_files:
                        contents_payload.append(doc_ref)
                        
                    # Soru görseli ve son talimat
                    contents_payload.append(image)
                    contents_payload.append("Lütfen bu soruyu ders notlarımız ve ekteki kitaplar doğrultusunda pedagojik olarak açıkla ve çöz.")

                    # Gemini çağrısı
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=contents_payload,
                        config=types.GenerateContentConfig(
                            temperature=0.2,
                        )
                    )
                    st.markdown(response.text)
                except Exception as e:
                    st.error(f"Çözüm oluşturulurken bir hata oluştu: {str(e)}")
    else:
        st.info("Sol taraftan bir soru görseli yükleyip 'Soruyu Analiz Et ve Çöz' butonuna basınız.")
