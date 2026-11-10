import streamlit as st
import streamlit.components.v1 as components
from PIL import Image
import os
import tempfile
import json
import pypdfium2 as pdfium
from google import genai
from google.genai import types

# Sayfa Yapılandırması
st.set_page_config(
    page_title="LGS Matematik Asistanı & Animasyonlu Tahta",
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
            image = page.render(scale=2.0).to_pil()
            return image
    except Exception as e:
        st.error(f"Sayfa görselleştirilemedi: {str(e)}")
    return None

# --- İNTERAKTİF DİJİTAL TAHTA & ANİMASYONLU ÖĞRETMEN BİLEŞENİ ---
def render_chalkboard_ui(steps_json_str, teacher_tip, final_answer):
    html_code = f"""
    <!DOCTYPE html>
    <html lang="tr">
    <head>
      <meta charset="UTF-8">
      <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.css">
      <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.js"></script>
      <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/contrib/auto-render.min.js"></script>
      <style>
        body {{
          margin: 0;
          padding: 10px;
          font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
          background-color: transparent;
        }}
        .board-container {{
          display: flex;
          gap: 15px;
          background: #1c3b2b; /* Klasik Okul Yeşil Tahtası */
          border: 12px solid #8B5A2B; /* Ahşap Çerçeve */
          border-radius: 12px;
          box-shadow: 0 10px 25px rgba(0,0,0,0.4);
          padding: 20px;
          min-height: 480px;
          box-sizing: border-box;
          color: #f1f8e9;
        }}
        .character-zone {{
          width: 140px;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: flex-start;
          border-right: 2px dashed rgba(255,255,255,0.2);
          padding-right: 15px;
        }}
        .teacher-avatar {{
          width: 90px;
          height: 90px;
          border-radius: 50%;
          background: #2e7d32;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 45px;
          border: 3px solid #a5d6a7;
          box-shadow: 0 4px 10px rgba(0,0,0,0.3);
          animation: floatTeacher 3s ease-in-out infinite;
        }}
        @keyframes floatTeacher {{
          0%, 100% {{ transform: translateY(0px); }}
          50% {{ transform: translateY(-8px); }}
        }}
        .teacher-speech {{
          background: #ffffff;
          color: #212121;
          border-radius: 10px;
          padding: 8px 10px;
          font-size: 12px;
          font-weight: bold;
          margin-top: 15px;
          text-align: center;
          position: relative;
          box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }}
        .teacher-speech:after {{
          content: '';
          position: absolute;
          top: -8px;
          left: 50%;
          transform: translateX(-50%);
          border-width: 0 8px 8px;
          border-style: solid;
          border-color: #ffffff transparent;
          display: block;
          width: 0;
        }}
        .board-zone {{
          flex: 1;
          display: flex;
          flex-direction: column;
          justify-content: space-between;
        }}
        .board-header {{
          border-bottom: 2px solid rgba(255,255,255,0.2);
          padding-bottom: 8px;
          margin-bottom: 12px;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }}
        .board-header h3 {{
          margin: 0;
          font-size: 18px;
          color: #e8f5e9;
          letter-spacing: 1px;
        }}
        .chalk-steps {{
          flex: 1;
          overflow-y: auto;
          padding-right: 5px;
          max-height: 320px;
        }}
        .step-item {{
          background: rgba(255,255,255,0.06);
          border-left: 4px solid #81c784;
          padding: 10px 14px;
          margin-bottom: 10px;
          border-radius: 4px;
          animation: fadeIn 0.4s ease-in;
          font-size: 15px;
          line-height: 1.5;
        }}
        .step-title {{
          font-weight: bold;
          color: #aed581;
          margin-bottom: 4px;
          font-size: 13px;
        }}
        .tip-box {{
          background: rgba(255, 235, 59, 0.15);
          border: 2px dashed #fbc02d;
          border-radius: 8px;
          padding: 10px;
          margin-top: 10px;
          color: #fff9c4;
          font-size: 13px;
        }}
        .ans-badge {{
          background: #388e3c;
          color: #ffffff;
          padding: 4px 10px;
          border-radius: 6px;
          font-size: 13px;
          font-weight: bold;
        }}
        .board-controls {{
          display: flex;
          gap: 10px;
          margin-top: 15px;
          padding-top: 10px;
          border-top: 1px solid rgba(255,255,255,0.2);
        }}
        button {{
          background: #4caf50;
          color: white;
          border: none;
          padding: 8px 16px;
          font-size: 14px;
          font-weight: bold;
          border-radius: 6px;
          cursor: pointer;
          transition: 0.2s;
        }}
        button:hover {{
          background: #43a047;
          transform: scale(1.02);
        }}
        button.secondary {{
          background: rgba(255,255,255,0.2);
        }}
        button.secondary:hover {{
          background: rgba(255,255,255,0.3);
        }}
        @keyframes fadeIn {{
          from {{ opacity: 0; transform: translateY(6px); }}
          to {{ opacity: 1; transform: translateY(0); }}
        }}
      </style>
    </head>
    <body>
      <div class="board-container">
        <!-- Öğretmen Karakter Alanı -->
        <div class="character-zone">
          <div class="teacher-avatar" id="avatarIcon">👨‍🏫</div>
          <div class="teacher-speech" id="teacherMsg">Hazırsan ilk adımla başlayalım!</div>
        </div>

        <!-- Dijital Yeşil Tahta Alanı -->
        <div class="board-zone">
          <div class="board-header">
            <h3>📐 DİJİTAL MATEMATİK TAHTASI</h3>
            <span class="ans-badge">Doğru Cevap: {final_answer}</span>
          </div>

          <div class="chalk-steps" id="stepsContainer">
            <!-- Adımlar JS ile dinamik gelecek -->
          </div>

          <div id="tipContainer" style="display: none;" class="tip-box">
            <strong>💡 Öğretmenin Püf Noktası:</strong> {teacher_tip}
          </div>

          <div class="board-controls">
            <button onclick="nextStep()" id="btnNext">👉 Sonraki Adımı Yaz</button>
            <button onclick="showAllSteps()" class="secondary">Tamamını Tahtaya Yaz</button>
            <button onclick="resetBoard()" class="secondary">Tahtayı Temizle</button>
          </div>
        </div>
      </div>

      <script>
        const steps = {steps_json_str};
        let currentStep = 0;

        const msgs = [
          "Verileri dikkatle ayıralım!",
          "Şimdi kuralı tahtaya uyguluyorum...",
          "İşlem basamağına dikkat et!",
          "İşte kritik noktaya geldik!",
          "Tebrikler! Çözümü tamamladık."
        ];

        function renderMath() {{
          if (window.renderMathInElement) {{
            renderMathInElement(document.getElementById("stepsContainer"), {{
              delimiters: [
                {{left: "$$", right: "$$", display: true}},
                {{left: "$", right: "$", display: false}}
              ]
            }});
          }}
        }}

        function nextStep() {{
          if (currentStep < steps.length) {{
            const step = steps[currentStep];
            const container = document.getElementById("stepsContainer");
            
            const stepDiv = document.createElement("div");
            stepDiv.className = "step-item";
            stepDiv.innerHTML = `<div class="step-title">Adım ${{currentStep + 1}}: ${{step.title}}</div><div>${{step.content}}</div>`;
            container.appendChild(stepDiv);
            
            // Öğretmen mesajını güncelle
            const msgIdx = Math.min(currentStep, msgs.length - 1);
            document.getElementById("teacherMsg").innerText = msgs[msgIdx];
            
            currentStep++;
            renderMath();
            container.scrollTop = container.scrollHeight;

            if (currentStep >= steps.length) {{
              document.getElementById("tipContainer").style.display = "block";
              document.getElementById("btnNext").disabled = true;
              document.getElementById("btnNext").innerText = "✅ Çözüm Bitti";
              document.getElementById("teacherMsg").innerText = "Harika iş çıkardın!";
            }}
          }}
        }}

        function showAllSteps() {{
          while (currentStep < steps.length) {{
            nextStep();
          }}
        }}

        function resetBoard() {{
          document.getElementById("stepsContainer").innerHTML = "";
          document.getElementById("tipContainer").style.display = "none";
          document.getElementById("btnNext").disabled = false;
          document.getElementById("btnNext").innerText = "👉 Sonraki Adımı Yaz";
          document.getElementById("teacherMsg").innerText = "Tahta temizlendi. Baştan alalım!";
          currentStep = 0;
        }}

        window.onload = function() {{
          // İlk adımı otomatik yazdır
          nextStep();
        }};
      </script>
    </body>
    </html>
    """
    components.html(html_code, height=520, scrolling=False)

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
            with st.spinner("Kitaplar işleniyor, sayfalar haritalanıyor..."):
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
Sen LGS hazırlık sürecinde uzman, MEB müfredatına ve soru mantığına hâkim bir 8. Sınıf Matematik Öğretmenisin.
Sana referans olarak 8. sınıf soru bankaları ve deneme PDF'leri verilmektedir.

DİKKAT EDİLECEK TEMEL İLKELER:
1. FORMÜLLER VE İŞLEMLER: Matematiksel tüm gösterimleri, köklü ifadeleri, üslü sayıları ve denklemleri kesinlikle KaTeX/LaTeX formatında yaz ($...$).
2. ADIM ADIM ANLATIM: Çözümü kütle halinde değil, tahtaya yazılacak mantıksal 3-5 adıma böl.
3. CEVAP ANAHTARI DOĞRULAMASI: Soruların doğruluğunu kitap sonundaki cevap anahtarlarıyla çapraz denetle.
"""

# --- ANA EKRAN SEKMELERİ ---
st.title("📐 8. Sınıf Akıllı Matematik Asistanı & Animasyonlu Tahta")

tab1, tab2, tab3 = st.tabs([
    "📷 Soru Çözümü & Tahtada Canlandırma", 
    "🎯 Kitaptan Soru Getir (Görsel + Tahta)", 
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
        
        btn_solve = st.button("Soruyu Analiz Et ve Tahtada Çöz", type="primary", use_container_width=True)

    with col_sol:
        st.subheader("2. Animasyonlu Öğretmen & Tahta")
        if btn_solve:
            if not img_obj:
                st.warning("Lütfen önce bir soru fotoğrafı yükleyin.")
            else:
                with st.spinner("Öğretmen soruyu inceliyor ve tahta adımlarını hazırlıyor..."):
                    payload = [BASE_TEACHER_PROMPT]
                    for _, doc, _ in st.session_state.active_books:
                        payload.append(doc)
                    payload.append(img_obj)
                    
                    prompt_instruction = """
                    Bu soruyu pedagojik olarak analiz et ve dijital tahtaya adım adım yazılacak şekilde JSON formatında hazırla.
                    Tüm matematiksel formülleri $...$ içinde KaTeX/LaTeX olarak yaz.

                    YANITINI ŞU KESİN JSON FORMATINDA VER:
                    ```json
                    {
                        "answer_key": "B",
                        "steps": [
                            {"title": "Verileri Belirleme", "content": "Soruda verilen kenar uzunluğu $a = \\sqrt{72} = 6\\sqrt{2}$ cm'dir."},
                            {"title": "Modeli Kurma", "content": "Alanı bulmak için $A = a^2$ bağıntısını kullanacağız."},
                            {"title": "Sonuç Adımı", "content": "$A = (6\\sqrt{2})^2 = 36 \\cdot 2 = 72\\text{ cm}^2$ bulunur."}
                        ],
                        "teacher_tip": "Öğrenciler genellikle karekökten çıkarırken katsayının karesini almayı unutur. $6\\sqrt{2}$'nin karesi $36 \\cdot 2 = 72$'dir."
                    }
                    ```
                    """
                    
                    if teacher_feedback:
                        prompt_instruction += f"\n\nÖĞRETMEN DÜZELTMESİ: '{teacher_feedback}'. Çözüm adımlarını buna göre kesinleştir."
                        
                    payload.append(prompt_instruction)
                    
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
                        render_chalkboard_ui(
                            json.dumps(data.get("steps", [])),
                            data.get("teacher_tip", ""),
                            data.get("answer_key", "-")
                        )
                    except Exception as e:
                        st.error(f"Hata: {str(e)}")

# ==========================================
# SEKME 2: KİTAPTAN GÖRSEL SORU & TAHTA ÇÖZÜM
# ==========================================
with tab2:
    st.subheader("Kitaptan Orijinal Soru ve Canlı Tahta Çözümü")
    st.caption("Kazanım ve seviye seçin; sistem kitaptaki sayfayı sol tarafa getirsin, sağ tarafta öğretmen animasyonla tahtaya çözsün.")
    
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
    
    if st.button("Soruyu ve Tahta Çözümünü Getir", type="primary"):
        if not st.session_state.active_books:
            st.warning("Lütfen önce sol menüden bir kitap PDF'i yükleyin.")
        else:
            with st.spinner("Kitap taranıyor ve tahta sunumu hazırlanıyor..."):
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
                    Ardından bu sorunun dijital yeşil tahtaya yazılacak adım adım KaTeX ($...$) çözümünü hazırla.
                    
                    YANITINI ŞU KESİN JSON FORMATINDA VER:
                    ```json
                    {{
                        "page_number": 15,
                        "question_title": "Test 3 - Soru 4",
                        "answer_key": "C",
                        "steps": [
                            {{"title": "Kuralı Hatırlayalım", "content": "EBOB problemlerinde bütünden parçaya gidilir."}},
                            {{"title": "Ortak Bölen Hesabı", "content": "$\\text{EBOB}(48, 60) = 12$ bulunur."}},
                            {{"title": "Sonuç ve Kontrol", "content": "Aralık sayısı $48/12 + 60/12 = 4 + 5 = 9$ olur."}}
                        ],
                        "teacher_tip": "Öğrenciler genellikle köşelere dikilen ağaçları mükerrer sayabilir, formülü dikkatli uygulayın."
                    }}
                    ```
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
                    steps_list = data.get("steps", [])
                    tip = data.get("teacher_tip", "")
                    
                    st.markdown(f"### 📖 {active_book_name} - {q_title} (Sayfa {page_num})")
                    
                    col_page_img, col_page_board = st.columns([1, 1])
                    
                    with col_page_img:
                        st.subheader("🖼️ Kitaptaki Soru Sayfası")
                        rendered_img = render_pdf_page_as_image(active_path, page_num)
                        if rendered_img:
                            st.image(rendered_img, caption=f"PDF Sayfa {page_num}", use_container_width=True)
                        else:
                            st.warning("Sayfa görseli oluşturulamadı.")
                            
                    with col_page_board:
                        st.subheader("👨‍🏫 Dijital Tahtada Canlı Anlatım")
                        render_chalkboard_ui(json.dumps(steps_list), tip, ans_key)
                            
                except Exception as e:
                    st.error(f"Soru getirilirken bir hata oluştu: {str(e)}")

# ==========================================
# SEKME 3: DENEME ANALİZİ & KOÇLUK REÇETESİ
# ==========================================
with tab3:
    st.subheader("📊 LGS Deneme Analizi & Öğrenci Koçluk Reçetesi")
    st.caption("Öğrencinin eksik kazanımlarını ve hata kök nedenini seçin; sistem kişisel telafi föyü ve çalışma planı hazırlasın.")
    
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

                TÜM MATEMATİKSEL İFADELERİ OKUNAKLI LATEX ($...$) İLE YAZ.
                
                Şu formatta rapor hazırla:
                1. 📋 BİLİŞSEL KOÇLUK TEŞHİSİ: Hata türlerine göre öğrencinin analizi.
                2. 💡 HIZLI KAZANIM VE TUZAK HATIRLATMA: Her kazanım için formül ve düşülen işlem tuzakları.
                3. 📚 KİTAPTAN KADEMELİ ÇALIŞMA SORULARI:
                   Kitaptaki sayfaları belirt (Sayfa, Test, Soru).
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
