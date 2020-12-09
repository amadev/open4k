# Copyright 2019 Mirantis Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# It's necessary to set this because some environments don't link sh -> bash.
SHELL := /bin/bash
TASK  := build

EXCLUDES := ''
CHARTS := $(filter-out $(EXCLUDES), $(wildcard ./charts/*/))

.PHONY: $(EXCLUDES) $(CHARTS)

ARGS =

ifdef VERSION
ARGS += --version $(VERSION)
endif

ifdef PACKAGE_DIR
ARGS += --destination $(PACKAGE_DIR)
endif

all: $(CHARTS)

$(CHARTS):
	@if [ -d $@ ]; then \
		echo; \
		echo "===== Processing [$@] chart ====="; \
		make $(TASK)-$@; \
	fi

init-%:
	if [ -f $*/Makefile ]; then make -C $*; fi

lint-%: init-%
	if [ -d $* ]; then helm lint $*; fi

build-%: lint-%
	if [ -d $* ]; then helm package $* $(ARGS); fi

clean:
	@echo "Clean all build artifacts"
	rm -f *tgz */charts/*tgz
