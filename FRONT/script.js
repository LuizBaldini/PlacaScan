const fileInput = document.getElementById("fileInput");
const dropzone = document.getElementById("dropzone");
const previewWrap = document.getElementById("previewWrap");
const previewImg = document.getElementById("previewImg");
const removeBtn = document.getElementById("removeBtn");
const scanBtn = document.getElementById("scanBtn");
const resultBox = document.getElementById("resultBox");
const plateText = document.getElementById("plateText");
const errorBox = document.getElementById("errorBox");
const copyBtn = document.getElementById("copyBtn");
const stepsArea = document.getElementById("stepsArea");
const stepsGallery = document.getElementById("stepsGallery");

let selectedFile = null;

function showPreview(file) {
  selectedFile = file;
  const url = URL.createObjectURL(file);
  previewImg.src = url;
  previewWrap.style.display = "block";
  dropzone.style.display = "none";
  scanBtn.disabled = false;
  hideMessages();
}

function resetUI() {
  selectedFile = null;
  previewWrap.style.display = "none";
  dropzone.style.display = "block";
  scanBtn.disabled = true;
  fileInput.value = "";
  hideMessages();
}

function hideMessages() {
  resultBox.style.display = "none";
  errorBox.style.display = "none";
  stepsArea.style.display = "none";
  stepsGallery.innerHTML = "";
}

fileInput.addEventListener("change", (e) => {
  if (e.target.files[0]) showPreview(e.target.files[0]);
});

removeBtn.addEventListener("click", resetUI);

// Drag & drop originais
dropzone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropzone.classList.add("drag-over");
});
dropzone.addEventListener("dragleave", () =>
  dropzone.classList.remove("drag-over"),
);
dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropzone.classList.remove("drag-over");
  const file = e.dataTransfer.files[0];
  if (file && file.type.startsWith("image/")) showPreview(file);
});

// Scan com integração dos passos
scanBtn.addEventListener("click", async () => {
  if (!selectedFile) return;
  scanBtn.classList.add("loading");
  scanBtn.disabled = true;
  hideMessages();

  const formData = new FormData();
  formData.append("imagem", selectedFile);

  try {
    const res = await fetch("http://127.0.0.1:5000/detectar-placa", {
      method: "POST",
      body: formData,
    });
    const data = await res.json();

    if (data.passos) {
      stepsArea.style.display = "block";
      const labels = {
        "1_gauss": "Filtro",
        "2_sobel": "Bordas",
        "3_morf": "Morph",
        "4_corte": "Placa",
        "5_final": "OCR",
      };
      Object.keys(data.passos).forEach((key) => {
        const div = document.createElement("div");
        div.innerHTML = `<p style="font-size:15px; color:var(--muted); margin-bottom:5px;">${labels[key] || key}</p>
                                 <img src="data:image/jpeg;base64,${data.passos[key]}" style="width:100%; border-radius:8px; border:1px solid var(--border);">`;
        stepsGallery.appendChild(div);
      });
    }

    if (data.placa) {
      plateText.textContent = data.placa;
      resultBox.style.display = "block";
    } else {
      errorBox.textContent = "⚠ " + (data.erro || "Erro desconhecido.");
      errorBox.style.display = "block";
    }
  } catch (err) {
    errorBox.textContent = "⚠ Erro ao conectar com o servidor.";
    errorBox.style.display = "block";
  } finally {
    scanBtn.classList.remove("loading");
    scanBtn.disabled = false;
  }
});

copyBtn.addEventListener("click", () => {
  navigator.clipboard.writeText(plateText.textContent).then(() => {
    const originalHTML = copyBtn.innerHTML;
    copyBtn.innerHTML = `Copiado!`;
    setTimeout(() => {
      copyBtn.innerHTML = originalHTML;
    }, 2000);
  });
});
