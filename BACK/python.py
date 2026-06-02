from flask import Flask, request, jsonify
import cv2
import numpy as np
import tempfile
import os
from google import genai
from flask_cors import CORS
import base64

app = Flask(__name__)
CORS(app)

client = genai.Client(api_key="bota a chave aqui")

def to_base64(imagem):
    _, buffer = cv2.imencode('.jpg', imagem)
    return base64.b64encode(buffer).decode('utf-8')

def gaussiano(imagem):
    img_cinza = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
    mascara_neutra = np.zeros_like(img_cinza) 
    img_preparada = cv2.add(img_cinza, mascara_neutra) 
    imgGaussiana = cv2.GaussianBlur(img_preparada, (3, 3), 0)
    return imgGaussiana

def sobel(imgGaussiana):
    imgSobelX = cv2.Sobel(imgGaussiana, cv2.CV_8U, 1, 0, ksize=3)
    _, imgThreshold = cv2.threshold(imgSobelX, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return imgThreshold

def closing(imgEntrada):
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 5))
    imgClosing = cv2.morphologyEx(imgEntrada, cv2.MORPH_CLOSE, kernel)
    return imgClosing

def encontrarPlaca(imgClosing):
    contornos, _ = cv2.findContours(imgClosing, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contornos = sorted(contornos, key=cv2.contourArea, reverse=True)[:15]
    localizacao = None
    for c in contornos:
        x, y, w, h = cv2.boundingRect(c)
        proporcao = float(w) / h
        if 2.2 < proporcao < 5.0:
            if w > 35 and h > 10:
                localizacao = c
                break
    return localizacao

def recortarPlaca(imagem_original, coordenadas):
    x, y, w, h = cv2.boundingRect(coordenadas)
    padding_h = int(h * 0.15)
    padding_w = int(w * 0.05)
    y_start = max(0, y - padding_h)
    y_end   = min(imagem_original.shape[0], y + h + padding_h)
    x_start = max(0, x - padding_w)
    x_end   = min(imagem_original.shape[1], x + w + padding_w)
    return imagem_original[y_start:y_end, x_start:x_end]

def preparar_para_ocr(img_recorte):
    gray    = cv2.cvtColor(img_recorte, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
    blur    = cv2.medianBlur(resized, 3)
    _, binaria = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if np.mean(binaria) < 127:
        binaria = cv2.bitwise_not(binaria)
    return binaria

def identificar_texto(img_recorte_path):
    uploaded_file = client.files.upload(file=img_recorte_path)
    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=[
            "Identifique exatamente os caracteres da placa nessa imagem. ",
            "Responda APENAS com a placa, sem mais nada. ",
            "A placa brasileira tem o formato: 3 letras maiúsculas, hífen, 4 números (ex: DVR-7813). ",
            "IMPORTANTE: Use apenas letras A-Z e números 0-9. ",
            "Nunca use caracteres especiais, acentos ou letras com diacríticos como Ö, Ü, Ã, etc. ",
            "A fonte é FE Engschrift — distinga bem: O vs D, 0 vs O, 1 vs I, 8 vs B.",
            uploaded_file
        ]
    )
    return response.text.strip()

@app.route("/detectar-placa", methods=["POST"])
def detectar_placa():
    if "imagem" not in request.files:
        return jsonify({"erro": "Nenhuma imagem enviada."}), 400

    file = request.files["imagem"]
    img_bytes = np.frombuffer(file.read(), np.uint8)
    imagem = cv2.imdecode(img_bytes, cv2.IMREAD_COLOR)

    if imagem is None:
        return jsonify({"erro": "Falha ao decodificar imagem."}), 400

    #dicionário
    passos = {}

    imgGaussiana = gaussiano(imagem)
    passos["1 Gaussiano"] = to_base64(imgGaussiana)

    imgBinaria = sobel(imgGaussiana)
    passos["2 Sobel"] = to_base64(imgBinaria)

    imgClosing = closing(imgBinaria)
    passos["3 Closing"] = to_base64(imgClosing)

    imgPlaca_coords = encontrarPlaca(imgClosing)
    if imgPlaca_coords is None:
        return jsonify({"erro": "Placa não localizada", "passos": passos}), 422

    recorte = recortarPlaca(imagem, imgPlaca_coords)
    passos["4 Recorte Original"] = to_base64(recorte)

    recorte_limpo = preparar_para_ocr(recorte)
    passos["5 Recorte Processado"] = to_base64(recorte_limpo)

    placa_texto = ""
    with tempfile.NamedTemporaryFile(suffix=".jpeg", delete=False) as tmp:
        tmp_path = tmp.name
        cv2.imwrite(tmp_path, recorte_limpo)
    
    try:
        placa_texto = identificar_texto(tmp_path)
    except Exception:
        placa_texto = "Erro na identificação"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    return jsonify({
        "placa": placa_texto,
        "passos": passos
    })

if __name__ == "__main__":
    app.run(debug=True, port=5000)