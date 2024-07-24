# Assignment on AWS Infrastructure Automation

### Overview: 
Develop a system that automatically manages the lifecycle of a web application hosted on  EC2 instances, monitors its health, and reacts to changes in traffic by scaling resources.Furthermore, administrators receive notifications regarding the infrastructure's health and scaling events. 
#### Detailed Breakdown: 
1. Web Application Deployment: 
   - Use `boto3` to: 
   - Create an S3 bucket to store your web application's static files. 
   - Launch an EC2 instance and configure it as a web server (e.g., Apache, Nginx).  - Deploy the web application onto the EC2 instance. 
2. Load Balancing with ELB: 
   - Deploy an Application Load Balancer (ALB) using `boto3`. 
   - Register the EC2 instance(s) with the ALB. 
3. Auto Scaling Group (ASG) Configuration: 
   - Using `boto3`, create an ASG with the deployed EC2 instance as a template. 
   - Configure scaling policies to scale in/out based on metrics like CPU utilization or network traffic. 
4. SNS Notifications: 
   - Set up different SNS topics for different alerts (e.g., health issues, scaling events, high traffic). 
   - Integrate SNS with Lambda so that administrators receive SMS or email notifications. 
5. Infrastructure Automation: 
   - Create a single script using `boto3` that: 
   - Deploys the entire infrastructure. 
   - Updates any component as required. 
   - Tears down everything when the application is no longer needed. 
6. Optional Enhancement – Dynamic Content Handling: 
   - Store user-generated content or uploads on S3. 
   - When a user uploads content to the web application, it gets temporarily stored on the  EC2 instance. A background process (or another Lambda function) can move this to the S3  bucket and update the application's database to point to the content's new location on S3. 
#### Objectives: 
- Gain a comprehensive understanding of key AWS services and their integration.
- Understand the lifecycle of a dynamic web application and its infrastructure.
 
#### Prerequisites
Prepare the development setup as follows:

   - Python 3.7 or higher installed.
     
   - Boto3 library installed (pip install boto3).
     ```bash
     pip3 install boto3
     ```
   - Configure AWS permissions via CLI command aws configure
     ```bash
      AWS Access Key ID [****************PC6D]: 
      AWS Secret Access Key [****************mBt6]: 
      Default region name [ap-northeast-2]: 
      Default output format [json]: json
     ```

#### Usage
   1. Run the python script <br />
      python3 aws_auto_deployment.py. On running the script ask for below inputs: <br />
      Enter action: create or delete <br />
      **Type: "create" to automatically create aws resources** <br /> 
      **Type: "delete" to automatically delete or tear down the resources created in "create"** <br />
      
      Below logs will be generated from the application during **create** operation <br />
      ```bash
      Enter action: create or delete: create
      AMI ID: ami-01ed8ade75d4eee2f
      Bucket created successfully: http://sonal-bucket.s3.amazonaws.com/
      Bucket sonal-bucket created successfully
      File index.html uploaded to sonal-bucket/index.html
      Primary server instance not found. Creating one..
      sonal-test-server created: i-0cf0c02640a9455c9
      Waiting for the instance to be up and UserData to execute...
      AMI ami-03f76d4b859ed86ce created from instance i-0cf0c02640a9455c9
      Waiting for AMI to become available...
      AMI ami-03f76d4b859ed86ce is now available.
      Target group with desired name is not present, Creating.....
      Target group sonal-target-group created with ARN: arn:aws:elasticloadbalancing:ap-northeast-2:975050024946:targetgroup/sonal-target-group/ff1af753c480f45c
      Instance i-0cf0c02640a9455c9 registered with target group sonal-target-group
      Load balancer 'sonal-load-balancer' not found.
      Load balancing ARN: arn:aws:elasticloadbalancing:ap-northeast-2:975050024946:loadbalancer/app/sonal-load-balancer/cb61755bb53b9742
      Creating launch configuration...
      Created launch configuration
      Auto scaling not found..
      {'ResponseMetadata': {'RequestId': '54e6962b-4d32-4172-a6f6-e7eb5b6240c6', 'HTTPStatusCode': 200, 'HTTPHeaders': {'x-amzn-requestid': '54e6962b-4d32-4172-a6f6-e7eb5b6240c6', 'content-type': 'text/xml', 'content-length': '231', 'date': 'Wed, 24 Jul 2024 15:15:10 GMT'}, 'RetryAttempts': 0}}
      Created auto scaling group
      SNS Topic created: arn:aws:sns:ap-northeast-2:975050024946:SONAL-Trigger-Scaling-Events
      SNS Topic created: arn:aws:sns:ap-northeast-2:975050024946:SONAL-Trigger-Health-Issues
      Error creating Lambda function sonal-notification-handler: An error occurred (InvalidParameterValueException) when calling the CreateFunction operation: The role defined for the function cannot be assumed by Lambda.
      Lambda subscribed to SNS Topic: {'SubscriptionArn': 'arn:aws:sns:ap-northeast-2:975050024946:SONAL-Trigger-Health-Issues:7ce356c5-392a-45f3-8f18-fe9309378319', 'ResponseMetadata': {'RequestId': '072b325a-9f61-513e-82a0-6d4183a330fc', 'HTTPStatusCode': 200, 'HTTPHeaders': {'x-amzn-requestid': '072b325a-9f61-513e-82a0-6d4183a330fc', 'date': 'Wed, 24 Jul 2024 15:15:14 GMT', 'content-type': 'text/xml', 'content-length': '382', 'connection': 'keep-alive'}, 'RetryAttempts': 0}}
      SNS Topic created: arn:aws:sns:ap-northeast-2:975050024946:SONAL-Trigger-Scaling-Events
      Error creating Lambda function sonal-notification-handler: An error occurred (InvalidParameterValueException) when calling the CreateFunction operation: The role defined for the function cannot be assumed by Lambda.
      Lambda subscribed to SNS Topic: {'SubscriptionArn': 'arn:aws:sns:ap-northeast-2:975050024946:SONAL-Trigger-Scaling-Events:04504f8f-b78e-46c8-93fc-a104e1542e8d', 'ResponseMetadata': {'RequestId': '8aeb1fd3-ce59-5605-81d8-40c8d29ac7c7', 'HTTPStatusCode': 200, 'HTTPHeaders': {'x-amzn-requestid': '8aeb1fd3-ce59-5605-81d8-40c8d29ac7c7', 'date': 'Wed, 24 Jul 2024 15:15:15 GMT', 'content-type': 'text/xml', 'content-length': '383', 'connection': 'keep-alive'}, 'RetryAttempts': 0}}
      SNS Topic created: arn:aws:sns:ap-northeast-2:975050024946:SONAL-Trigger-High-Traffic
      Error creating Lambda function sonal-notification-handler: An error occurred (InvalidParameterValueException) when calling the CreateFunction operation: The role defined for the function cannot be assumed by Lambda.
      Lambda subscribed to SNS Topic: {'SubscriptionArn': 'arn:aws:sns:ap-northeast-2:975050024946:SONAL-Trigger-High-Traffic:b1e2966b-1e13-4697-8c09-82d56b6731a4', 'ResponseMetadata': {'RequestId': 'c714c6e4-bb51-5a86-b50d-99ffa7954b44', 'HTTPStatusCode': 200, 'HTTPHeaders': {'x-amzn-requestid': 'c714c6e4-bb51-5a86-b50d-99ffa7954b44', 'date': 'Wed, 24 Jul 2024 15:15:16 GMT', 'content-type': 'text/xml', 'content-length': '381', 'connection': 'keep-alive'}, 'RetryAttempts': 0}}
      ```
      Similarly below logs will be generated during **delete** operation <br />
      ```bash
      Enter action: create or delete: delete
      sonal-test-server Instance Already Present, Instance ID: i-0cf0c02640a9455c9
      Launch configuration 'sonal-launch-configuration' already exists.
      Auto scaling group 'sonal-auto-scale' already exists.
      Deleted index.html from sonal-bucket
      Bucket sonal-bucket deleted successfully
      Terminated EC2 instance with ID: i-0cf0c02640a9455c9
      AMI with name 'sonal-ami-2' already exists.
      Deregistered AMI with ID: ami-03f76d4b859ed86ce
      Deleted load balancer with ARN: arn:aws:elasticloadbalancing:ap-northeast-2:975050024946:loadbalancer/app/sonal-load-balancer/cb61755bb53b9742
      Failed to delete listener arn:aws:elasticloadbalancing:ap-northeast-2:975050024946:listener/app/sonal-load-balancer/cb61755bb53b9742/95df27107131e286: An error occurred (ListenerNotFound) when calling the DeleteListener operation: Listener 'arn:aws:elasticloadbalancing:ap-northeast-2:975050024946:listener/app/sonal-load-balancer/cb61755bb53b9742/95df27107131e286' not found
      Deleted auto scaling group: sonal-auto-scale
      Deleted scaling policy: sonal-policy for Auto Scaling Group: sonal-auto-scale
      Deleted launch configuration: sonal-launch-configuration
      Deleted target group: 'arn:aws:elasticloadbalancing:ap-northeast-2:975050024946:targetgroup/sonal-target-group/ff1af753c480f45c
      Lambda function 'sonal-notification-handler' not found
      ```
      
