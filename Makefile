# Makefile do projeto1-eda
# Alvos: make data | make analysis | make test | make all | make clean

PYTHON := .venv/bin/python

.PHONY: all venv data analysis test notebook clean

all: data analysis test

# Cria a venv local e instala dependências (só refaz se requirements.txt mudar)
.venv/.ok: requirements.txt
	python3 -m venv .venv
	$(PYTHON) -m pip install --quiet --upgrade pip
	$(PYTHON) -m pip install --quiet -r requirements.txt
	touch .venv/.ok

venv: .venv/.ok

# Gera o dataset sintético de CloudTrail
data: venv
	$(PYTHON) data/generate_data.py

# Roda as 5 análises e salva gráficos + summary.json em reports/
analysis: venv
	$(PYTHON) src/analysis.py --output reports/

# Roda a suíte de testes
test: venv
	$(PYTHON) -m pytest tests/ -v

# Abre o notebook no JupyterLab (precisa do dataset: make data primeiro)
notebook: venv data
	$(PYTHON) -m jupyter lab notebooks/eda_cloudtrail.ipynb

# Remove artefatos gerados
clean:
	rm -rf reports data/cloudtrail_sample.csv .pytest_cache
