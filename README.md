# comparative-forecasting-models
This repository provides a comparative implementation of four ensemble tree-based algorithms:
- 🌲 Random Forest
- 🚀 XGBoost
- 💡 LightGBM
- 🐱 CatBoost

Each algorithm is tested using the same dataset, consistent code structure, and four identical hyperparameter tuning techniques:
- 🧮 Grid Search
- 🎲 Random Search
- 🧠 Bayesian Optimization
- 🔍 Optuna

🔍 Research Objectives
This study aims to:
1. Compare the performance of the four algorithms in forecasting sales,
2. Evaluate the effectiveness of each hyperparameter tuning method in improving prediction accuracy,
3. Identify the best-performing algorithm and optimization technique based on evaluation metrics including MSE, RMSE, MAE, and R² Score.

Each model is evaluated using:
- Train/Validation/Test Split: 80/10/10
- Cross-Validation: TimeSeriesSplit / K-Fold
- Metrik Evaluasi:
1. Mean Squared Error (MSE)
2. Root Mean Squared Error (RMSE)
3. Mean Absolute Error (MAE)
4. R² Score

📈 Result and Analysis
The analysis includes:
1. Visualisasi Learning Curve tiap model
2. Perbandingan performa antar metode tuning
3. Waktu komputasi tiap metode
