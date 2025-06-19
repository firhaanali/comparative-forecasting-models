# comparative-forecasting-models
Repositori ini berisi implementasi komparatif antara empat algoritma ensemble tree-based, yaitu:
- 🌲 Random Forest
- 🚀 XGBoost
- 💡 LightGBM
- 🐱 CatBoost

Setiap algoritma diuji menggunakan dataset yang sama, struktur kode yang konsisten, dan empat metode tuning hyperparameter yang identik, yaitu:
- 🧮 Grid Search
- 🎲 Random Search
- 🧠 Bayesian Optimization
- 🔍 Optuna

🔍 Tujuan Penelitian
Penelitian ini bertujuan untuk:
1. Membandingkan performa keempat algoritma dalam memprediksi penjualan,
2. Mengevaluasi efektivitas masing-masing metode tuning hyperparameter terhadap akurasi prediksi,
3. Mengidentifikasi algoritma dan teknik optimasi terbaik berdasarkan metrik evaluasi seperti MSE, RMSE, MAE, dan R².

Masing-masing model dievaluasi menggunakan:
Train/Validation/Test Split: 80/10/10
Cross-Validation: TimeSeriesSplit / K-Fold
Metrik Evaluasi:
1. Mean Squared Error (MSE)
2. Root Mean Squared Error (RMSE)
3. Mean Absolute Error (MAE)
4. R² Score

📈 Hasil dan Analisis
Analisis mencakup:
1. Visualisasi Learning Curve tiap model
2. Perbandingan performa antar metode tuning
3. Waktu komputasi tiap metode
