.PHONY: default
default: list;

# From https://stackoverflow.com/questions/4219255/how-do-you-get-the-list-of-targets-in-a-makefile
.PHONY: list
list:
	@$(MAKE) -pRrq -f $(lastword $(MAKEFILE_LIST)) : 2>/dev/null | awk -v RS= -F: '/^# File/,/^# Finished Make data base/ {if ($$1 !~ "^[#.]") {print $$1}}' | sort | egrep -v -e '^[^[:alnum:]]' -e '^$@$$' | xargs

.PHONY: format
format:
	black .

.PHONY: sort
sort:
	isort --profile black .

.PHONY: lint
lint:
	flake8 .

.PHONY: typecheck
typecheck:
	mypy .

.PHONY: fix
fix:
	make format
	make sort
	make lint
	# make typecheck

.PHONY: poetry-install
poetry-install:
	poetry config virtualenvs.create false \
	&& poetry lock \
	&& poetry export --without-hashes -f requirements.txt --dev \
	| pip install -r /dev/stdin \
	&& poetry debug

nltk-resources:
	python -m nltk.downloader cmudict

# build-app-heroku:
# 	poetry export -f requirements.txt -o requirements.txt
# 	docker build -t registry.heroku.com/$(HEROKU_APP_NAME)/$(HEROKU_PROCESS_TYPE) .

# push-app-heroku:
# 	docker push registry.heroku.com/${HEROKU_APP_NAME}/$(HEROKU_PROCESS_TYPE):latest
