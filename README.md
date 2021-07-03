# Serverless: Lambda + DynamoDB

## API Gateway
https://docs.aws.amazon.com/lambda/latest/dg/services-apigateway.html

## Lambda layer
This code uses external modules (requests). When creating a lambda function in AWS that requires external modules, one of the options is to use a lambda layer that contains all these modules. That way, the lambda is independent of those modules, can be updated by itself, and also you can share that layer between lambdas that use the same modules, thus making it easier to maintain.

### Preparing the layer
First create a new folder for this project:
```
mkdir aws-lambda-layer
cd aws-lambda-layer
```
Next, create a folder structure for the modules that need to be installed.
```
mkdir -p lambda-layer/python/lib/python3.8/site-packages
```
Once the folder is created we can install requests in that folder.
```
pip3 install requests --target lambda-layer/python/lib/python3.8/site-packages
```
That folder structure is important because that is where Python expects to find the modules. Also as you can see, in this example I am using Python 3.8.

Now we can go into the lambda-layer folder and create a zip file for the layer that will be uploaded using the console.
```
cd lambda-layer
zip -r9 lambda-layer.zip .
```

### Creating the layer
Log into the AWS console and go to Services -> Lambda -> Layers

- Create layer
- Name (ex: myRequestsLayer)
- Upload
- Select your zip file from before
- Runtime (Python 3.8)
- Create

### Connecting the layer to lambda
On the lambda screen, in the Designer section, click on the Layers box.

- Add a layer
- Select from list of runtime compatible layers
- Name (chose your layer)
- Version 1
- Add


### IMPORTANT
Increase time for lambda to 30 secs