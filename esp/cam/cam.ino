
#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>

// --- CONFIGURATION RÉSEAU ---
const char* ssid = "Livebox-E960";
const char* password = "o9gG5ggCgVEPcPjMau";
const char* serverIP = "192.168.1.30"; // L'IP de ton PC
String serverName = "http://192.168.1.30:8000/api/v1/camera/upload"; // ALIGNÉ !
// --------------------------------

// Configuration des broches pour le modèle AI Thinker
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

void setup() {
  Serial.begin(115200);

  // Connexion au Wi-Fi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnecté au Wi-Fi!");

  // Configuration de la caméra
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  
  // Résolution de l'image (VGA = 640x480). Tu peux mettre FRAMESIZE_SVGA, FRAMESIZE_XGA etc.
  config.frame_size = FRAMESIZE_VGA; 
  config.jpeg_quality = 12; // De 0 à 63 (plus petit = meilleure qualité)
  config.fb_count = 1;

  // Initialisation de la caméra
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Erreur d'initialisation de la caméra: 0x%x", err);
    return;
  }
}

void loop() {
  if(WiFi.status() == WL_CONNECTED){
    // Prendre une photo
    camera_fb_t * fb = esp_camera_fb_get();
    if(!fb) {
      Serial.println("Échec de la capture de l'image");
      delay(100); 
      return;
    }

    // Préparer la requête HTTP
    HTTPClient http;
    http.begin(serverName);
    http.addHeader("Content-Type", "image/jpeg");
    http.addHeader("X-Device-ID", "node3_vision_real"); // AJOUTÉ !

    // Envoyer l'image en POST
    int httpResponseCode = http.POST(fb->buf, fb->len);
    
    if (httpResponseCode > 0) {
      Serial.print("Code HTTP: ");
      Serial.println(httpResponseCode);
    } else {
      Serial.print("Code d'erreur HTTP: ");
      Serial.println(httpResponseCode);
    }
    
    http.end(); // Libérer les ressources HTTP
    esp_camera_fb_return(fb); // Libérer la mémoire de la caméra
  }
  
  // Attendre 1 seconde avant la prochaine photo
  delay(1000); 
}
