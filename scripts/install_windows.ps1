Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Write-Host "설치 완료. 실행: streamlit run app.py"
