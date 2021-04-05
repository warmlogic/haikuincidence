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
