.PHONY: package deploy

# Where your lambda source lives
SRC_DIR := ../src/lambda/hello/
ZIP_FILE := $(CURDIR)/deployment-lambda-hello.zip
LAMBDA_NAME := rmind-hello

package:
	@echo "Zipping Lambda source..."
	cd $(SRC_DIR) && zip $(ZIP_FILE) * 

deploy: package
	@echo "Updating Lambda $(LAMBDA_NAME)..."
	aws lambda update-function-code \
		--function-name $(LAMBDA_NAME) \
		--zip-file fileb://$(ZIP_FILE) > /dev/null

apply: deploy
	@echo "Applying Terraform configuration..."
	terraform apply