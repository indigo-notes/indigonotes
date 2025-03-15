eval "$(conda shell.bash hook)"

conda activate indigonotes
cd /app/
uvicorn main:app --host 0.0.0.0 --port 80
conda deactivate
