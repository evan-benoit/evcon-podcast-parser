.PHONY: package deploy

# Where your lambda source lives
SRC_DIR := ../src/lambda/hello/
BUILD_DIR := ./build
ZIP_FILE := $(CURDIR)/deployment-lambda-hello.zip
LAMBDA_NAME := rmind-hello

deps:
	@echo "Installing dependencies into build dir..."
	rm -rf $(BUILD_DIR)
	mkdir -p $(BUILD_DIR)
	pip install --target $(BUILD_DIR) -r $(SRC_DIR)/requirements.txt

package: deps
	@echo "Zipping Lambda source and dependencies..."
	cp -r $(SRC_DIR)/* $(BUILD_DIR)/
	cd $(BUILD_DIR) && zip -r $(ZIP_FILE) .

deploy: package
	@echo "Updating Lambda $(LAMBDA_NAME)..."
	aws lambda update-function-code \
		--function-name $(LAMBDA_NAME) \
		--zip-file fileb://$(ZIP_FILE) > /dev/null

apply: deploy
	@echo "Applying Terraform configuration..."
	terraform apply

clean:
	rm -rf $(BUILD_DIR) $(ZIP_FILE)