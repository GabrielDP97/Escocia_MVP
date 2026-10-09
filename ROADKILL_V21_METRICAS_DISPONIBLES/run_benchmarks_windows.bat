@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Ejecuta setup_windows.bat primero.
  pause
  exit /b 1
)
.venv\Scripts\python.exe -m pytest -q
if errorlevel 1 (
  echo Los tests han fallado.
  pause
  exit /b 1
)
.venv\Scripts\python.exe -m backend.run_benchmarks
if errorlevel 1 (
  echo No se pudo regenerar el benchmark.
  pause
  exit /b 1
)
echo.
echo Benchmark regenerado correctamente en data\benchmark_technology_lab.json
echo Auditoria de calibracion regenerada en data\calibration_audit.json
echo Comparativa CSV en data\calibration_comparison.csv
echo Auditoria temporal estricta en data\strict_temporal_audit.json
echo Resumen validation 2016 en data\strict_validation_2016_summary.csv
echo Resumen test 2017 en data\strict_test_2017_summary.csv
echo Sensibilidad de umbral en data\strict_threshold_sensitivity_2017.csv
pause
