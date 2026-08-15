// CATNIME AI STUDIO
// Em produção, configure para a URL do backend publicado.
// Ex.: window.CATNIME_AI_API_BASE = "https://seu-backend.vercel.app/api"
const API_BASE = window.CATNIME_AI_API_BASE || "http://127.0.0.1:8000/api";

const views = {
  home: document.getElementById("homeView"),
  upscale: document.getElementById("upscaleView"),
};

const fileInput = document.getElementById("fileInput");
const dropzone = document.getElementById("dropzone");
const preview = document.getElementById("preview");
const placeholder = document.getElementById("dropPlaceholder");
const processBtn = document.getElementById("processBtn");
const message = document.getElementById("message");
const resultEmpty = document.getElementById("resultEmpty");
const resultContent = document.getElementById("resultContent");
const resultImage = document.getElementById("resultImage");
const downloadBtn = document.getElementById("downloadBtn");
const resultMeta = document.getElementById("resultMeta");
const apiStatus = document.getElementById("apiStatus");

function showView(name) {
  Object.values(views).forEach(v => v.classList.remove("active"));
  views[name].classList.add("active");
  document.querySelectorAll(".nav-item").forEach(b => b.classList.remove("active"));
  const active = document.querySelector(`[data-view="${name}"]`);
  if (active) active.classList.add("active");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

document.querySelectorAll("[data-view]").forEach(btn => {
  btn.addEventListener("click", () => showView(btn.dataset.view));
});
document.getElementById("heroStart").onclick = () => showView("upscale");
document.getElementById("upscaleCard").onclick = () => showView("upscale");
document.getElementById("backHome").onclick = () => showView("home");

function setFile(file) {
  if (!file) return;
  const allowed = ["image/png", "image/jpeg", "image/webp"];
  if (!allowed.includes(file.type)) {
    message.textContent = "Formato inválido. Use PNG, JPG ou WEBP.";
    return;
  }
  if (file.size > 15 * 1024 * 1024) {
    message.textContent = "A imagem é maior que 15 MB.";
    return;
  }
  const url = URL.createObjectURL(file);
  preview.src = url;
  preview.style.display = "block";
  placeholder.style.display = "none";
  processBtn.disabled = false;
  message.textContent = `${file.name} selecionada.`;
}

fileInput.addEventListener("change", () => setFile(fileInput.files[0]));
dropzone.addEventListener("dragover", e => { e.preventDefault(); });
dropzone.addEventListener("drop", e => {
  e.preventDefault();
  if (e.dataTransfer.files[0]) {
    fileInput.files = e.dataTransfer.files;
    setFile(e.dataTransfer.files[0]);
  }
});

processBtn.addEventListener("click", async () => {
  const file = fileInput.files[0];
  if (!file) return;

  const resolution = document.querySelector('input[name="resolution"]:checked').value;
  const faceEnhance = document.getElementById("faceEnhance").checked;

  const form = new FormData();
  form.append("image", file);
  form.append("resolution", resolution);
  form.append("face_enhance", faceEnhance ? "true" : "false");

  processBtn.disabled = true;
  processBtn.textContent = "⏳ Processando com IA...";
  message.textContent = "Enviando imagem para o backend...";

  try {
    const response = await fetch(`${API_BASE}/upscale/`, {
      method: "POST",
      body: form,
    });

    if (!response.ok) {
      let errorText = "Falha ao processar imagem.";
      try {
        const err = await response.json();
        errorText = err.error || errorText;
      } catch {}
      throw new Error(errorText);
    }

    const blob = await response.blob();
    const objectUrl = URL.createObjectURL(blob);
    const filename = response.headers.get("X-Catnime-Filename") || `catnime-${resolution}.png`;
    const width = response.headers.get("X-Catnime-Width") || "";
    const height = response.headers.get("X-Catnime-Height") || "";

    resultImage.src = objectUrl;
    downloadBtn.href = objectUrl;
    downloadBtn.download = filename;
    resultMeta.textContent = `${width} × ${height} • Real-ESRGAN + Pillow`;
    resultEmpty.style.display = "none";
    resultContent.style.display = "block";
    message.textContent = "Imagem processada com sucesso.";
  } catch (error) {
    console.error(error);
    message.textContent = `Erro: ${error.message}`;
  } finally {
    processBtn.disabled = false;
    processBtn.textContent = "✨ Melhorar com IA";
  }
});

document.getElementById("newImageBtn").onclick = () => {
  fileInput.value = "";
  preview.src = "";
  preview.style.display = "none";
  placeholder.style.display = "block";
  processBtn.disabled = true;
  resultEmpty.style.display = "flex";
  resultContent.style.display = "none";
  message.textContent = "";
};

async function checkAPI() {
  try {
    const res = await fetch(`${API_BASE}/health/`);
    if (!res.ok) throw new Error();
    apiStatus.textContent = "Online";
    apiStatus.parentElement.parentElement.querySelector(".status-dot").style.background = "#3adb76";
  } catch {
    apiStatus.textContent = "Offline / não configurada";
    apiStatus.parentElement.parentElement.querySelector(".status-dot").style.background = "#ff5b00";
  }
}
checkAPI();
