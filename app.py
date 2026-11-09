import streamlit as st
from PIL import Image
import os
from google import genai
from google.genai import types

# Sayfa yapılandırması
st.set_page_config(
    page_title="Matematik Öğretmen Asistanı",
    page_icon="📐",
    layout="wide"
)

# API Anahtarı Kontrolü (Streamlit Cloud Secrets veya Ortam Değişkeni)
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")

if not api_key:
    st.error("Lütfen GEMINI_API_KEY anahtarını Streamlit Secrets alanına ekleyin.")
    st.stop()

# Gemini İstemcisi
client = genai.Client(api_key=api_key)

# Ders Notlarını Yükleme Fonksiyonu
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

# Sistem Rolü / Pedagojik Yönerge
SYSTEM_INSTRUCTION = f"""
Sen sabırlı, motive edici ve kavramsal anlamayı merkeze alan uzman bir İlköğretim Matematik Öğretmenisin.
Öğrenci sana bir matematik sorusunun fotoğrafını yüklüyor.

Aşağıda senin kendi ders/kazanım notların ve öğretim referansların bulunmaktadır:
[DERS VE KAZANIM NOTLARIN]
{curriculum_context}

Görevin:
1. Görseldeki soruyu, tüm matematiksel sembolleri ve verileri dikkatle analiz et.
2. Soruyu çözerken yukarıdaki ders notlarında yer alan anlatım dilini, kazanım sırasını ve kuralları esas al.
3. Asla sadece doğrudan sonucu söyleyip geçme. Adım adım, neden-sonuç ilişkisi kurarak öğrenciye rehberlik et.
4. Varsa öğrencilerin sıklıkla düştüğü kavram yanılgılarını veya dikkat edilmesi gereken işlem tuzaklarını ("Burada şuna çok dikkat etmelisin...") şeklinde vurgula.
5. Matematiksel gösterimleri okunaklı LaTeX formatında ($...$) yaz.
6. Samimi, teşvik edici ve anlaşılır bir öğretmen üslubu kullan.
"""

# Kullanıcı Arayüzü
st.title("📐 Akıllı Matematik Çözüm & Öğretmen Asistanı")
st.caption("Sorunun fotoğrafını yükleyin; öğretmen anlatımıyla adım adım çözümü inceleyin.")

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
        
    # Buton artık her zaman sayfada sabit durur
    solve_button = st.button("Soruyu Analiz Et ve Çöz", type="primary", use_container_width=True)

with col2:
    st.subheader("2. Pedagojik Çözüm Rehberi")
    
    if solve_button:
        if uploaded_file is None:
            st.warning("Lütfen önce sol taraftan bir soru fotoğrafı yükleyin.")
        else:
            with st.spinner("Soru inceleniyor ve öğretmen anlatımı hazırlanıyor..."):
                try:
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=[image, "Lütfen bu soruyu ders notlarımız doğrultusunda adım adım açıkla ve çöz."],
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_INSTRUCTION,
                            temperature=0.2,
                        )
                    )
                    st.markdown(response.text)
                except Exception as e:
                    st.error(f"Çözüm oluşturulurken bir hata oluştu: {str(e)}")
    else:
        st.info("Sol taraftan bir soru görseli yükleyip 'Soruyu Analiz Et ve Çöz' butonuna basınız.")
