# Serverless: Lambda + DynamoDB


# How to deploy
## Create Lambda function
1. Open the Functions page on the lambda console 
2. `Creat funciton` -> `Author from scratch`.
3. Choose a name, e.g. `telegramBotTengeEuro`.
4. Runtime: `Python 3.8`.
5. Keep rest at default for now and press `Create fundtion`.

## Create a web API with an HTTP endpoint for the Lambda function
Reference: https://docs.aws.amazon.com/lambda/latest/dg/services-apigateway.html
1. Open the Functions page on the Lambda console. 
2. Choose the function.
3. Under `Functional overview`, choose `Add trigger`.
4. Select `API Gateway`.
5. For API, choose `Create an API`.
6. For API Type, choose `HTTP API`.
7. For Security, choose `Open`. 
8. Choose `Add`.
9. Copy API endpoint for later use.

## Preparing the lambda layer
This code uses external modules: `requests` and `boto3`. `boto3` is already supported by lambda runtime. When creating a lambda function in AWS that requires external modules, one of the options is to use a lambda layer that contains all these modules. That way, the lambda is independent of those modules, can be updated by itself, and also you can share that layer between lambdas that use the same modules, thus making it easier to maintain.

Layer with requests is included as `lambda-layer.zip`. However, in case more external modules are needed, you can follow instruction below.

### Create lambda layer (optional)
Before starting, make sure you're using python3.8 since lambda runtime is python3.8. 
First create a folder structure for the modules that need to be installed.
```
mkdir -p lambda-layer/python/lib/python3.8/site-packages
```
Once the folder is created we can install requests and any other module in that folder.
```
pip3 install requests --target lambda-layer/python/lib/python3.8/site-packages
```
That folder structure is important because that is where Python expects to find the modules.

Now we can go into the lambda-layer folder and create a zip file for the layer that will be uploaded using the console.
```
cd lambda-layer
zip -r9 lambda-layer.zip .
```

### Creating the layer
1. Go to Services -> Lambda -> Layers and choose `Create layer`.
2. Name (ex: telegramBotRequestsLayer).
3. Upload `lambda-layer.zip`.
4. For runtime choose Python 3.8 and choose `Create`.

### Connecting the layer to lambda
1. Go to Services -> Lambda -> Functions and select the lambda function.
2. Under `Layers` choose `Add a layer`.
3. Choose `Custom layers` and select the layer.
4. Press `Add`.

## Create telegram bot
Reference: https://core.telegram.org/bots/api
1. Talk to [BotFather](https://t.me/botfather) to create a new bot and get your bot token.
2. Set webhook by sending following request with your `TELEGRAM_BOT_TOKEN` and `LAMBDA_HTTP_API_ENDPOINT` (you can use browser): https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook?url={LAMBDA_HTTP_API_ENDPOINT}

## Setup lambda function
1. Go to `Lambda` -> `Functions` and choose the lambda function.
2. Copy and paste code from `lambda_function.py` code source box and deploy.
3. In `Configuration` -> `Environment variables` set following values:
- `ADMIN_CHAT_ID`: admin's chat id (you can find this by texting the bot and printing the event)
- `TELEGRAM_BOT_TOKEN`: bot token you got fron BotFather
- `CURRENCY_A`: name of currency A in english (e.g. tenge)
- `CURRENCY_A_RUS`: name of currency A in russian (e.g. тенге)
- `CURRENCY_B`: name of currency B in english (e.g. euro)
- `CURRENCY_B_RUS`: name of currency B in russian (e.g. евро)
4. In `Configuration` -> `General configuration` set memory to 256MB and timeout to 30secs.

## Setup DynamoDB
Go to DynamoDB and create following tables:
1. name: `{CURRENCY_A}2{CURRENCY_B}` (e.g. `tenge2euro`); partition key name: `user_id`, type: number; no sort key
2. name: `{CURRENCY_B}2{CURRENCY_A}` (e.g. `euro2tenge`); partition key name: `user_id`, type: number; no sort key
3. name: `{CURRENCY_A}2{CURRENCY_B}_telegram_hist` (e.g. `tenge2euro_telegram_hist`); partition key name: `user_id`, type: number; sort key name: `date`, type: number
3. name: `{CURRENCY_A}2{CURRENCY_B}_transaction_history` (e.g. `tenge2euro_transaction_history`); partition key name: `date`, type: number; no sort key

## Configure IAM Role for lambda
Lambda need to access DynamoDB.
1. Go to `IAM` -> `Roles`.
2. Choose default role used by the lambda.
3. Choose `Add inline policy`.
4. For service choose `DynamoDB`.
5. Actions: `PutItem`, `DeleteItem`, `GetItem`, `Scan`, `Query`.
6. Resources: `All resources`.
7. Choose `Review policy`.
8. Set name to `DynamoDBReadWrite`.

# How to run tests
Install pipenv
```
python3 -m pip install pipenv
```
Install from Pipfile
```
python3 -m pipenv install
```
Activate environment and run tests
```
python3 -m pipenv shell
python -m unittest test_lambda_function.py
```